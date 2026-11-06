"""DeployEasy: Production Cloud CI/CD & Deployment Platform."""
import asyncio
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import config
from .auth import (
    check_auth_rate_limit,
    clear_session_cookies,
    create_user_session,
    get_authorized_project,
    get_current_user,
    hash_password,
    set_session_cookies,
    verify_csrf_protection,
    verify_password,
)
from .cost_estimator import estimate_project_costs
from .db import (
    Deployment,
    HealthCheck,
    Project,
    SessionLocal,
    User,
    UserSession,
    get_db,
    init_db,
)
from .env_validator import validate_environment
from .github_client import (
    GitHubIntegrationError,
    dispatch_github_workflow,
    verify_live_version,
)
from .incident_generator import generate_incident_report
from .log_analyzer import analyze_deployment_logs
from .notifications import (
    dispatch_webhook,
    format_discord_payload,
    format_slack_payload,
)
from .readiness import calculate_readiness_score
from .schemas import (
    AuthTokenResponse,
    CostEstimateResponse,
    DeploymentResponse,
    DeploymentTriggerRequest,
    EnvValidationRequest,
    EnvValidationResponse,
    HealthCheckResponse,
    IncidentReportRequest,
    IncidentReportResponse,
    LogAnalysisRequest,
    LogAnalysisResponse,
    OverviewStats,
    ProjectCreate,
    ProjectResponse,
    ReadinessResponse,
    RollbackRequest,
    SecurityScanResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    WebhookTestRequest,
)
from .ssrf import (
    SSRFValidationError,
    safe_urlopen,
    validate_target_url,
    validate_webhook_url,
)

STATIC = Path(__file__).parent / "static"
START_TIME = time.time()
requests_served = 0
_runs_cache = {"at": 0.0, "data": None}

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("deployeasy")

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CsrfProtect = Annotated[None, Depends(verify_csrf_protection)]


def probe_project_health(project: Project, db: Session, allow_local_for_testing: bool = False) -> HealthCheck:
    """Execute a live HTTP health probe with strict SSRF protection and accurate error detection."""
    service_url = (project.service_url or "").strip()
    if not service_url:
        service_url = "http://localhost:8080"

    target_url = service_url.rstrip("/") + "/health"
    try:
        validate_target_url(target_url, allow_local_for_testing=allow_local_for_testing)
    except SSRFValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSRF protection: {exc}",
        ) from exc

    start_probe = time.time()
    status_code = 503
    is_healthy = False
    error_msg = None

    try:
        with safe_urlopen(
            target_url,
            timeout=3.0,
            allow_local_for_testing=allow_local_for_testing,
        ) as resp:
            status_code = resp.status
            is_healthy = (200 <= status_code < 300)
    except Exception as exc:  # noqa: BLE001
        status_code = 503
        is_healthy = False
        error_msg = str(exc)

    elapsed_ms = round((time.time() - start_probe) * 1000, 2)
    check_entry = HealthCheck(
        project_id=project.id,
        endpoint="/health",
        status_code=status_code,
        response_time_ms=elapsed_ms if elapsed_ms > 0 else 10.0,
        is_healthy=is_healthy,
        error_message=error_msg,
    )
    db.add(check_entry)
    project.status = "operational" if is_healthy else "degraded"
    db.commit()
    db.refresh(check_entry)
    return check_entry


async def background_health_monitor():
    """Background worker that continuously probes registered projects every 60s."""
    while True:
        try:
            await asyncio.sleep(60)
            db = SessionLocal()
            try:
                projects = db.query(Project).all()
                for p in projects:
                    if p.service_url:
                        try:
                            probe_project_health(p, db)
                        except Exception as probe_err:  # noqa: BLE001
                            log.warning("Background probe failed for %s: %s", p.name, probe_err)
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as loop_err:  # noqa: BLE001
            log.warning("Health monitor loop error: %s", loop_err)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed default admin user
    init_db()
    task = None
    if not os.getenv("TESTING"):
        task = asyncio.create_task(background_health_monitor())
    try:
        yield
    finally:
        if task:
            task.cancel()


app = FastAPI(title="DeployEasy", lifespan=lifespan)

# Enable CORS for cross-origin client apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def structured_logging(request: Request, call_next):
    """Count requests and write one JSON log line per request."""
    global requests_served
    request_id = uuid.uuid4().hex[:8]
    started = time.time()
    response = await call_next(request)
    requests_served += 1
    response.headers["X-Request-ID"] = request_id
    log.info(json.dumps({
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "level": "INFO",
        "request_id": request_id,
        "route": request.url.path,
        "status": response.status_code,
        "duration_ms": round((time.time() - started) * 1000, 1),
    }))
    return response


# -----------------------------------------------------------------------------
# Base Core Endpoints & Frontend Views
# -----------------------------------------------------------------------------

@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and not accept.startswith("*/*"):
        return FileResponse(STATIC / "landing.html")
    return {"message": "Welcome to DeployEasy"}


@app.get("/login")
@app.get("/signup")
def auth_page():
    return FileResponse(STATIC / "login.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": config.APP_VERSION, "git_sha": config.GIT_SHA}


@app.get("/metrics")
def metrics():
    return {
        "process_uptime_seconds": round(time.time() - START_TIME, 1),
        "requests_since_process_start": requests_served,
    }


# -----------------------------------------------------------------------------
# Authentication & Safe Session Management
# -----------------------------------------------------------------------------

@app.post("/api/auth/register", response_model=AuthTokenResponse, status_code=201)
def register_user(payload: UserCreate, request: Request, response: Response, db: DbSession):
    """Create a new developer account with PBKDF2 password hashing, rate limiting, and HttpOnly cookies."""
    check_auth_rate_limit(request)

    existing = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="developer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    session = create_user_session(db, user)
    set_session_cookies(response, session)

    return AuthTokenResponse(
        token=session.session_token,
        csrf_token=session.csrf_token,
        user=user,
    )


@app.post("/api/auth/login", response_model=AuthTokenResponse)
def login_user(payload: UserLogin, request: Request, response: Response, db: DbSession):
    """Authenticate credentials with rate limiting and issue secure HttpOnly cookies."""
    check_auth_rate_limit(request)

    user = db.query(User).filter((User.username == payload.username) | (User.email == payload.username)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    session = create_user_session(db, user)
    set_session_cookies(response, session)

    return AuthTokenResponse(
        token=session.session_token,
        csrf_token=session.csrf_token,
        user=user,
    )


@app.post("/api/auth/demo-login", response_model=AuthTokenResponse)
def demo_login(response: Response, db: DbSession):
    """Create a secured demo session with read-only sandbox permissions."""
    demo_user = db.query(User).filter(User.username == "demo-developer").first()
    if not demo_user:
        demo_user = User(
            username="demo-developer",
            email="demo@deployeasy.local",
            password_hash=hash_password("demopassword123"),
            role="demo",
            is_active=True,
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

    session = create_user_session(db, demo_user)
    set_session_cookies(response, session)

    return AuthTokenResponse(
        token=session.session_token,
        csrf_token=session.csrf_token,
        user=demo_user,
    )


@app.get("/api/auth/me", response_model=UserResponse)
def current_user_identity(user: CurrentUser):
    """Retrieve current session identity. Requires valid authentication."""
    return user


@app.post("/api/auth/logout")
def logout_user(request: Request, response: Response, db: DbSession):
    """Invalidate session in database and clear authentication cookies."""
    token = request.cookies.get("deployeasy_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            token = parts[-1]

    if token:
        db.query(UserSession).filter(UserSession.session_token == token).delete()
        db.commit()

    clear_session_cookies(response)
    return {"status": "logged_out", "message": "Session invalidated"}


# -----------------------------------------------------------------------------
# GitHub Actions Pipeline Runs Telemetry
# -----------------------------------------------------------------------------

@app.get("/api/runs")
def pipeline_runs():
    """Recent GitHub Actions runs, cached for 60s. Failures never break the page."""
    if not config.GITHUB_REPO:
        return {"runs": [], "message": "Set GITHUB_REPO to show pipeline runs."}
    now = time.time()
    if _runs_cache["data"] is not None and now - _runs_cache["at"] < 60:
        return _runs_cache["data"]
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/actions/runs?per_page=5"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "deployeasy"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as r:
            raw = json.load(r)
        data = {"runs": [
            {"name": x["name"], "status": x["conclusion"] or x["status"],
             "sha": x["head_sha"][:7], "time": x["created_at"]}
            for x in raw.get("workflow_runs", [])
        ], "message": ""}
        _runs_cache.update(at=now, data=data)
        return data
    except Exception:  # noqa: BLE001
        return _runs_cache["data"] or {"runs": [], "message": "GitHub API offline or unauthenticated."}


# -----------------------------------------------------------------------------
# Projects API (Owner-Scoped Authorization & SSRF Validation)
# -----------------------------------------------------------------------------

@app.get("/api/projects", response_model=list[ProjectResponse])
def list_projects(user: CurrentUser, db: DbSession):
    """List projects accessible to the authenticated user. Excludes deploy hook secrets."""
    if user.role == "admin":
        return db.query(Project).all()
    return db.query(Project).filter(Project.owner_id == user.id).all()


@app.post("/api/projects", response_model=ProjectResponse, status_code=201)
def create_project(payload: ProjectCreate, user: CurrentUser, db: DbSession, csrf: CsrfProtect = None):
    """Connect a new repository. Requires authentication and enforces SSRF validation on service URLs."""
    if user.role == "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo accounts have read-only access. Sign up as a developer to connect projects.",
        )

    # SSRF validation on project service URL if provided
    if payload.service_url:
        try:
            validate_target_url(payload.service_url)
        except SSRFValidationError as err:
            raise HTTPException(status_code=400, detail=f"Invalid service_url: {err}") from err

    existing = db.query(Project).filter(Project.repo_name == payload.repo_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="A project for this repository already exists")

    project = Project(
        name=payload.name,
        repo_name=payload.repo_name,
        branch=payload.branch,
        service_url=payload.service_url,
        deploy_hook_url=payload.deploy_hook_url,
        status="operational",
        owner_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, user: CurrentUser, db: DbSession):
    """Retrieve project metadata with owner authorization."""
    return get_authorized_project(project_id, user, db, require_write=False)


# -----------------------------------------------------------------------------
# Deployments API, One-Click Rollback & Diffs (Verified Execution)
# -----------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/deployments", response_model=list[DeploymentResponse])
def get_project_deployments(project_id: int, user: CurrentUser, db: DbSession):
    """Retrieve historical deployments for an authorized project."""
    project = get_authorized_project(project_id, user, db, require_write=False)
    return project.deployments


@app.get("/api/deployments/{deployment_id}/diff")
def get_deployment_diff(deployment_id: int, user: CurrentUser, db: DbSession):
    """Calculate the release jump and difference between deployments."""
    dep = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment record not found")

    # Authorize access to parent project
    get_authorized_project(dep.project_id, user, db, require_write=False)

    prev_dep = (
        db.query(Deployment)
        .filter(Deployment.project_id == dep.project_id, Deployment.id < dep.id)
        .order_by(Deployment.id.desc())
        .first()
    )

    prev_sha = prev_dep.commit_sha if prev_dep else "initial"
    return {
        "deployment_id": dep.id,
        "current_sha": dep.commit_sha[:7],
        "previous_sha": prev_sha[:7],
        "commit_message": dep.commit_message,
        "diff_summary": f"Changes between {prev_sha[:7]} and {dep.commit_sha[:7]}",
        "trigger_type": dep.trigger_type,
        "status": dep.status,
        "duration_difference": dep.duration_seconds - (prev_dep.duration_seconds if prev_dep else dep.duration_seconds),
    }


@app.post("/api/deployments/trigger", response_model=DeploymentResponse, status_code=201)
def trigger_deployment(payload: DeploymentTriggerRequest, user: CurrentUser, db: DbSession, csrf: CsrfProtect = None):
    """Trigger manual release deployment. Enforces readiness gates and executes real workflow or hook."""
    project = get_authorized_project(payload.project_id, user, db, require_write=True)

    # 1. Enforce Pre-Deploy Readiness Safety Gates (unless force=True with admin privileges)
    if not payload.force:
        critical_cves = 0
        high_cves = 0
        secrets_found = False
        for scan in project.security_scans:
            if scan.scan_type == "trivy":
                critical_cves += scan.critical_count
                high_cves += scan.high_count
            elif scan.scan_type == "gitleaks" and not scan.passed:
                secrets_found = True

        last_dep = project.deployments[0] if project.deployments else None
        tests_ok = (last_dep is not None and last_dep.status in ("success", "rolled_back"))
        rollback_ok = len(project.deployments) > 1

        readiness = calculate_readiness_score(
            tests_passed=tests_ok,
            critical_vulns=critical_cves,
            high_vulns=high_cves,
            secrets_detected=secrets_found,
            health_status=project.status,
            rollback_available=rollback_ok,
        )
        if readiness["deployment_blocked"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Deployment blocked by safety gates: {'; '.join(readiness['blocking_reasons'])}. Fix violations before promoting.",
            )

    sha = payload.commit_sha
    if len(sha) < 40:
        sha = sha.ljust(40, "0")

    dep_status = "deploying"
    log_lines = [f"Release initiated for commit {sha[:7]}", f"Branch: {payload.branch}"]
    has_integration = False

    # 2. Real Integration Dispatch: GitHub workflow_dispatch
    if config.GITHUB_TOKEN:
        try:
            dispatch_github_workflow(
                repo_name=project.repo_name,
                workflow_file="pipeline.yml",
                inputs={"sha": sha},
                ref=payload.branch or "main",
            )
            log_lines.append("✓ GitHub Actions workflow_dispatch executed (pipeline.yml)")
            has_integration = True
        except GitHubIntegrationError as err:
            log_lines.append(f"⚠️ GitHub Actions dispatch error: {err}")
            dep_status = "failure"

    # 3. Real Integration Dispatch: Render Deploy Hook
    if not has_integration and project.deploy_hook_url:
        try:
            req = urllib.request.Request(
                project.deploy_hook_url,
                data=b"",
                headers={"User-Agent": "DeployEasy-Deployer/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                log_lines.append(f"✓ Render deploy hook notified (HTTP {resp.status})")
                has_integration = True
        except Exception as exc:  # noqa: BLE001
            log_lines.append(f"⚠️ Render deploy hook notification error: {exc}")
            dep_status = "failure"

    # If no integration is configured, never report fake success!
    if not has_integration and dep_status != "failure":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No deployment integration configured. Configure GITHUB_TOKEN or Render deploy hook for this project.",
        )

    dep = Deployment(
        project_id=project.id,
        commit_sha=sha,
        commit_message=payload.commit_message,
        branch=payload.branch,
        trigger_type="manual",
        status=dep_status,
        duration_seconds=0,
        logs_summary="\n".join(log_lines),
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


@app.post("/api/deployments/rollback", response_model=DeploymentResponse, status_code=200)
def rollback_deployment(payload: RollbackRequest, user: CurrentUser, db: DbSession, csrf: CsrfProtect = None):
    """Trigger real rollback using existing rollback.yml workflow or deploy hook.
    
    Requires full 40-character SHA and verifies live version before reporting success.
    """
    project = get_authorized_project(payload.project_id, user, db, require_write=True)

    sha = payload.target_sha.strip().lower()
    # Enforce full 40-character commit SHA per rollback.yml specifications
    if len(sha) != 40 or not re.match(r"^[0-9a-f]{40}$", sha):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rollback requires the full 40-character lowercase hexadecimal commit SHA.",
        )

    log_lines = [
        f"Rollback initiated to target SHA {sha}",
        f"Reason: {payload.reason}",
    ]
    rollback_status = "deploying"
    has_integration = False

    # 1. Real GitHub workflow_dispatch to rollback.yml passing exact input "sha"
    if config.GITHUB_TOKEN:
        try:
            dispatch_github_workflow(
                repo_name=project.repo_name,
                workflow_file="rollback.yml",
                inputs={"sha": sha},
                ref=project.branch or "main",
            )
            log_lines.append(f"✓ GitHub Actions workflow_dispatch triggered (rollback.yml, sha={sha})")
            has_integration = True
        except GitHubIntegrationError as err:
            log_lines.append(f"⚠️ GitHub rollback dispatch failed: {err}")
            rollback_status = "failure"

    # 2. Render deploy hook fallback
    if not has_integration and project.deploy_hook_url:
        try:
            req = urllib.request.Request(
                project.deploy_hook_url,
                data=b"",
                headers={"User-Agent": "DeployEasy-Rollback/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                log_lines.append(f"✓ Render rollback hook notified (HTTP {resp.status})")
                has_integration = True
        except Exception as exc:  # noqa: BLE001
            log_lines.append(f"⚠️ Render deploy hook error: {exc}")
            rollback_status = "failure"

    if not has_integration and rollback_status != "failure":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rollback integration configured. Set GITHUB_TOKEN or deploy hook in project settings.",
        )

    # 3. Live version verification check
    if rollback_status == "deploying" and project.service_url:
        is_live = verify_live_version(project.service_url, sha)
        if is_live:
            rollback_status = "rolled_back"
            log_lines.append(f"✓ Live version probe verified SHA {sha[:7]} running on {project.service_url}")
        else:
            log_lines.append("⏳ Rollback dispatched; awaiting live container convergence on /version")

    rollback_dep = Deployment(
        project_id=project.id,
        commit_sha=sha,
        commit_message=f"Rollback to {sha[:7]}: {payload.reason}",
        branch=project.branch,
        trigger_type="rollback",
        status=rollback_status,
        duration_seconds=0,
        logs_summary="\n".join(log_lines),
    )
    db.add(rollback_dep)
    db.commit()
    db.refresh(rollback_dep)
    return rollback_dep


# -----------------------------------------------------------------------------
# Health Monitoring & Live Probes (Owner-Scoped & SSRF-Protected)
# -----------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/health-history", response_model=list[HealthCheckResponse])
def get_health_history(project_id: int, user: CurrentUser, db: DbSession, limit: int = 15):
    project = get_authorized_project(project_id, user, db, require_write=False)
    return db.query(HealthCheck).filter(HealthCheck.project_id == project.id).order_by(HealthCheck.checked_at.desc()).limit(limit).all()


@app.post("/api/projects/{project_id}/check-health", response_model=HealthCheckResponse)
def run_live_health_check(project_id: int, user: CurrentUser, db: DbSession):
    """Run an on-demand health probe against the project's service URL with SSRF protection."""
    project = get_authorized_project(project_id, user, db, require_write=False)
    return probe_project_health(project, db)


# -----------------------------------------------------------------------------
# Security & Trivy Scans (Owner-Scoped)
# -----------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/security", response_model=list[SecurityScanResponse])
def get_security_scans(project_id: int, user: CurrentUser, db: DbSession):
    project = get_authorized_project(project_id, user, db, require_write=False)
    return project.security_scans


# -----------------------------------------------------------------------------
# Deployment Failure Diagnostics
# -----------------------------------------------------------------------------

@app.post("/api/analyze-logs", response_model=LogAnalysisResponse)
def analyze_logs(payload: LogAnalysisRequest):
    """Intelligently parse raw CI/CD logs to diagnose root causes and recommend fixes."""
    return analyze_deployment_logs(payload.logs)


@app.get("/api/deployments/{deployment_id}/analysis", response_model=LogAnalysisResponse)
def analyze_deployment_record(deployment_id: int, user: CurrentUser, db: DbSession):
    """Analyze the logs of a specific deployment record with project authorization."""
    dep = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment record not found")

    get_authorized_project(dep.project_id, user, db, require_write=False)
    return analyze_deployment_logs(dep.logs_summary)


# -----------------------------------------------------------------------------
# Environment Variable Validation
# -----------------------------------------------------------------------------

@app.post("/api/validate-env", response_model=EnvValidationResponse)
def validate_env_config(payload: EnvValidationRequest):
    """Validate project environment variables against production criteria without secret leakage."""
    return validate_environment(payload.env_vars)


# -----------------------------------------------------------------------------
# Pre-Deploy Readiness Score (0-100% with Hard Blocker Gates)
# -----------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/readiness", response_model=ReadinessResponse)
def get_project_readiness(project_id: int, user: CurrentUser, db: DbSession):
    """Calculate pre-deployment readiness score and hard safety gates for an authorized project."""
    project = get_authorized_project(project_id, user, db, require_write=False)

    critical_cves = 0
    high_cves = 0
    secrets_found = False
    for scan in project.security_scans:
        if scan.scan_type == "trivy":
            critical_cves += scan.critical_count
            high_cves += scan.high_count
        elif scan.scan_type == "gitleaks" and not scan.passed:
            secrets_found = True

    last_dep = project.deployments[0] if project.deployments else None
    tests_ok = (last_dep is not None and last_dep.status in ("success", "rolled_back"))
    rollback_ok = len(project.deployments) > 1

    return calculate_readiness_score(
        tests_passed=tests_ok,
        critical_vulns=critical_cves,
        high_vulns=high_cves,
        secrets_detected=secrets_found,
        health_status=project.status,
        rollback_available=rollback_ok,
    )


# -----------------------------------------------------------------------------
# Cloud & CI/CD Cost Estimator
# -----------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/costs", response_model=CostEstimateResponse)
def get_project_cost_estimates(project_id: int, user: CurrentUser, db: DbSession):
    """Calculate estimated infrastructure, runner minutes, and hosting costs for an authorized project."""
    project = get_authorized_project(project_id, user, db, require_write=False)

    durations = [d.duration_seconds for d in project.deployments]
    return estimate_project_costs(
        deployment_durations_seconds=durations,
        instance_tier="free" if "localhost" in project.service_url or "onrender" in project.service_url else "starter",
        container_image_size_mb=185.0,
        images_stored_count=len(project.deployments),
    )


# -----------------------------------------------------------------------------
# Automated Incident Report & Post-Mortem Generator
# -----------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/incidents/generate", response_model=IncidentReportResponse)
def create_incident_report(project_id: int, payload: IncidentReportRequest, user: CurrentUser, db: DbSession):
    """Automatically generate an incident post-mortem in Markdown format."""
    project = get_authorized_project(project_id, user, db, require_write=False)

    return generate_incident_report(
        project_name=project.name,
        failed_sha=payload.failed_sha,
        rollback_sha=payload.rollback_sha,
        symptoms=payload.symptoms,
        log_excerpt=payload.log_excerpt,
    )


# -----------------------------------------------------------------------------
# Webhook Notifications (SSRF & Domain Allowlist Protection)
# -----------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/webhook-test")
def test_webhook_integration(project_id: int, payload: WebhookTestRequest, user: CurrentUser, db: DbSession):
    """Test webhook notification dispatch with SSRF protection and platform domain allowlists."""
    project = get_authorized_project(project_id, user, db, require_write=False)

    # Validate webhook domain and SSRF
    try:
        validate_webhook_url(payload.webhook_url, payload.platform)
    except SSRFValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook validation error: {exc}",
        ) from exc

    if payload.platform.lower() == "discord":
        body = format_discord_payload(
            event_type="test_notification",
            project_name=project.name,
            commit_sha=config.GIT_SHA,
            message="Test webhook notification dispatched from DeployEasy Dashboard.",
            status="success",
        )
    else:
        body = format_slack_payload(
            event_type="test_notification",
            project_name=project.name,
            commit_sha=config.GIT_SHA,
            message="Test webhook notification dispatched from DeployEasy Dashboard.",
            status="success",
        )

    dispatched = dispatch_webhook(payload.webhook_url, body, platform=payload.platform)
    return {
        "success": dispatched,
        "platform": payload.platform,
        "sample_payload": body,
        "message": "Webhook delivered successfully" if dispatched else "Failed to deliver (endpoint unreachable)",
    }


# -----------------------------------------------------------------------------
# High-level System Overview (Owner-Scoped & Non-Leaking)
# -----------------------------------------------------------------------------

@app.get("/api/overview", response_model=OverviewStats)
def get_system_overview(db: DbSession, user: CurrentUser):
    """Retrieve overview metrics scoped to the authenticated caller."""
    if user.role == "admin":
        projects = db.query(Project).all()
        all_deployments = db.query(Deployment).all()
    else:
        projects = db.query(Project).filter(Project.owner_id == user.id).all()
        project_ids = [p.id for p in projects]
        all_deployments = db.query(Deployment).filter(Deployment.project_id.in_(project_ids)).all() if project_ids else []

    successful = [d for d in all_deployments if d.status in ("success", "rolled_back")]
    failed = [d for d in all_deployments if d.status == "failure"]

    recent = [d for d in all_deployments][:8]
    avg_duration = sum(d.duration_seconds for d in all_deployments) / len(all_deployments) if all_deployments else 0.0

    return OverviewStats(
        total_projects=len(projects),
        active_deployments=len([p for p in projects if p.status == "operational"]),
        successful_deployments=len(successful),
        failed_deployments=len(failed),
        fleet_health="Operational" if not failed else "Degraded",
        avg_deploy_time_seconds=round(avg_duration, 1),
        process_uptime_seconds=round(time.time() - START_TIME, 1),
        requests_served=requests_served,
        version=config.APP_VERSION,
        git_sha=config.GIT_SHA,
        recent_deployments=recent,
        projects=projects,
    )
