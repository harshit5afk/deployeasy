import os

os.environ["TESTING"] = "1"
import socket
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import reset_auth_rate_limits
from app.db import (
    Deployment,
    SecurityScan,
    SessionLocal,
    init_db,
)
from app.main import app
from app.readiness import calculate_readiness_score

init_db()
client = TestClient(app)

MOCK_PUBLIC_ADDRINFO = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


@pytest.fixture(autouse=True)
def clean_rate_limits():
    """Ensure clean rate limit window before each test."""
    reset_auth_rate_limits()
    yield
    reset_auth_rate_limits()


@pytest.fixture(autouse=True)
def mock_external_dns():
    """Mock external DNS resolution so tests don't require internet and run deterministically."""
    orig_getaddrinfo = socket.getaddrinfo

    def side_effect(host, port, *args, **kwargs):
        if host in ("127.0.0.1", "localhost", "169.254.169.254", "10.0.0.1", "192.168.1.1", "::1", "fe80::1"):
            return orig_getaddrinfo(host, port, *args, **kwargs)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 443))]

    with patch("socket.getaddrinfo", side_effect=side_effect):
        yield


@pytest.fixture
def auth_client():
    """Fixture providing an authenticated admin client with active session and CSRF header."""
    reset_auth_rate_limits()
    admin_client = TestClient(app)
    r = admin_client.post("/api/auth/login", json={"username": "admin", "password": "admin123456!"})
    csrf = r.json().get("csrf_token") or admin_client.cookies.get("deployeasy_csrf")
    admin_client.headers["X-CSRF-Token"] = csrf
    return admin_client


@pytest.fixture
def sample_project(auth_client):
    """Creates a sample project with an initial deployment and security scan for testing."""
    repo = f"test-org/sample-{uuid.uuid4().hex[:6]}"
    res = auth_client.post("/api/projects", json={
        "name": "Sample Microservice",
        "repo_name": repo,
        "branch": "main",
        "service_url": "https://sample.onrender.com",
        "deploy_hook_url": "https://api.render.com/deploy/srv-mock-secret",
    })
    proj = res.json()
    proj_id = proj["id"]

    db = SessionLocal()
    try:
        dep = Deployment(
            project_id=proj_id,
            commit_sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            commit_message="Initial deploy commit",
            branch="main",
            status="success",
            duration_seconds=42,
            logs_summary="CI/CD Build Successful\n✓ Tests passed",
        )
        scan = SecurityScan(
            project_id=proj_id,
            scan_type="trivy",
            target="sample:latest",
            critical_count=0,
            high_count=0,
            passed=True,
        )
        db.add_all([dep, scan])
        db.commit()
    finally:
        db.close()
    return proj_id


def test_health_returns_200():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version_has_version_and_sha():
    body = client.get("/version").json()
    assert "version" in body and "git_sha" in body


def test_metrics_are_numbers():
    body = client.get("/metrics").json()
    assert isinstance(body["process_uptime_seconds"], (int, float))
    assert isinstance(body["requests_since_process_start"], int)


def test_root_message():
    assert "DeployEasy" in client.get("/").json()["message"]


def test_runs_endpoint_never_crashes_without_config():
    r = client.get("/api/runs")
    assert r.status_code == 200 and "runs" in r.json()


def test_dashboard_page_served():
    r = client.get("/dashboard")
    assert r.status_code == 200 and "DeployEasy" in r.text


def test_list_projects_never_leaks_deploy_hook_url(auth_client, sample_project):
    r = auth_client.get("/api/projects")
    assert r.status_code == 200
    projects = r.json()
    assert isinstance(projects, list)
    assert len(projects) >= 1
    # Security Gate: deploy_hook_url must NEVER be exposed in public API responses
    for p in projects:
        assert "deploy_hook_url" not in p
        assert "has_deploy_hook" in p


def test_create_project_and_get(auth_client):
    unique_repo = f"test-org/service-{uuid.uuid4().hex[:6]}"
    payload = {
        "name": "Microservice Worker",
        "repo_name": unique_repo,
        "branch": "main",
        "service_url": "https://worker.onrender.com",
        "deploy_hook_url": "https://api.render.com/deploy/srv-secret-token",
    }
    r = auth_client.post("/api/projects", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Microservice Worker"
    assert data["has_deploy_hook"] is True
    # Ensure hook is not leaked in response
    assert "deploy_hook_url" not in data

    project_id = data["id"]
    r_get = auth_client.get(f"/api/projects/{project_id}")
    assert r_get.status_code == 200
    assert r_get.json()["repo_name"] == unique_repo
    assert "deploy_hook_url" not in r_get.json()


def test_get_project_deployments(auth_client, sample_project):
    r_deps = auth_client.get(f"/api/projects/{sample_project}/deployments")
    assert r_deps.status_code == 200
    deps = r_deps.json()
    assert isinstance(deps, list)
    assert len(deps) >= 1
    assert "commit_sha" in deps[0]


@patch("app.main.dispatch_github_workflow")
@patch("app.main.verify_live_version", return_value=True)
def test_trigger_deployment_and_rollback(mock_verify, mock_dispatch, auth_client, sample_project):
    with patch("app.main.config.GITHUB_TOKEN", "mock_gh_token"):
        # Trigger deployment (force=True to bypass readiness gates for test)
        trigger_payload = {
            "project_id": sample_project,
            "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "commit_message": "test: trigger smoke test release",
            "branch": "main",
            "force": True,
        }
        r_trig = auth_client.post("/api/deployments/trigger", json=trigger_payload)
        assert r_trig.status_code == 201
        assert r_trig.json()["status"] in ("success", "deploying")

        # Trigger rollback
        rollback_payload = {
            "project_id": sample_project,
            "target_sha": "ef1482f7c0099ad4bb5e58db5f32cf8e51928014",
            "reason": "Test rollback from automated suite",
        }
        r_roll = auth_client.post("/api/deployments/rollback", json=rollback_payload)
        assert r_roll.status_code == 200
        data = r_roll.json()
        assert data["status"] in ("rolled_back", "deploying")
        assert "ef1482f" in data["commit_sha"]


@patch("app.main.safe_urlopen")
def test_health_check_probe_and_history(mock_safe_urlopen, auth_client, sample_project):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_safe_urlopen.return_value.__enter__.return_value = mock_resp

    # Run on-demand check
    r_check = auth_client.post(f"/api/projects/{sample_project}/check-health")
    assert r_check.status_code == 200
    assert r_check.json()["endpoint"] == "/health"

    # Get history
    r_hist = auth_client.get(f"/api/projects/{sample_project}/health-history")
    assert r_hist.status_code == 200
    hist = r_hist.json()
    assert isinstance(hist, list)
    assert len(hist) >= 1


@patch("app.main.safe_urlopen", side_effect=Exception("Connection refused"))
def test_health_probe_reports_unreachable_endpoint(mock_safe_urlopen, auth_client):
    """Verify that an unreachable endpoint reports is_healthy=False and 503."""
    unique_repo = f"test-org/dead-service-{uuid.uuid4().hex[:6]}"
    p_res = auth_client.post("/api/projects", json={
        "name": "Dead Port Service",
        "repo_name": unique_repo,
        "service_url": "https://unreachable.example.com",
    })
    assert p_res.status_code == 201
    p_id = p_res.json()["id"]

    r_check = auth_client.post(f"/api/projects/{p_id}/check-health")
    assert r_check.status_code == 200
    data = r_check.json()
    assert data["is_healthy"] is False
    assert data["status_code"] == 503
    assert data["error_message"] is not None


def test_health_probe_ssrf_protection(auth_client):
    """Verify that creating/probing a cloud metadata IP 169.254.169.254 is blocked by SSRF gate."""
    unique_repo = f"test-org/ssrf-service-{uuid.uuid4().hex[:6]}"
    p_res = auth_client.post("/api/projects", json={
        "name": "SSRF Target Service",
        "repo_name": unique_repo,
        "service_url": "http://169.254.169.254/latest/meta-data",
    })
    # Blocked at project creation time
    assert p_res.status_code == 400
    assert "cloud metadata" in p_res.json()["detail"].lower() or "ssrf" in p_res.json()["detail"].lower()


def test_security_scans(auth_client, sample_project):
    r_sec = auth_client.get(f"/api/projects/{sample_project}/security")
    assert r_sec.status_code == 200
    scans = r_sec.json()
    assert isinstance(scans, list)
    assert len(scans) >= 1


def test_system_overview_never_leaks_secrets(auth_client, sample_project):
    r = auth_client.get("/api/overview")
    assert r.status_code == 200
    data = r.json()
    assert "fleet_health" in data
    assert "recent_deployments" in data
    # Check that projects in overview stats do not expose deploy_hook_url
    for p in data["projects"]:
        assert "deploy_hook_url" not in p


def test_analyze_logs_endpoint():
    # Test 1: Test failure
    log_sample = """
    ============================= test session starts =============================
    FAILED tests/test_core.py::test_calculation - AssertionError: 42 != 43
    """
    r = client.post("/api/analyze-logs", json={"logs": log_sample})
    assert r.status_code == 200
    res = r.json()
    assert res["error_category"] == "test_failure"
    assert res["severity"] == "HIGH"
    assert "pytest" in res["suggested_fix"].lower()

    # Test 2: Trivy vulnerability gate
    trivy_sample = "2026-11-05T12:00:00Z FATAL Trivy scan detected CRITICAL CVE-2024-37891 exit code: 1"
    r2 = client.post("/api/analyze-logs", json={"logs": trivy_sample})
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["error_category"] == "security_vulnerability"
    assert res2["severity"] == "CRITICAL"


def test_deployment_log_analysis_record(auth_client, sample_project):
    r_deps = auth_client.get(f"/api/projects/{sample_project}/deployments")
    dep_id = r_deps.json()[0]["id"]

    r_analysis = auth_client.get(f"/api/deployments/{dep_id}/analysis")
    assert r_analysis.status_code == 200
    assert "error_category" in r_analysis.json()


def test_validate_env_endpoint_masks_passwords():
    # Payload containing database password and secret tokens
    secret_pass = "supersecretpassword987654321"
    env_with_secrets = {
        "PORT": "8080",
        "DATABASE_URL": f"postgresql://appuser:{secret_pass}@pg.prod.cluster:5432/maindb",
        "SECRET_KEY": "supersecretkey12345678",
        "API_TOKEN": "tok_live_1234567890abcdef",
    }
    r = client.post("/api/validate-env", json={"env_vars": env_with_secrets})
    assert r.status_code == 200
    res = r.json()
    assert res["is_valid"] is True
    # Confirm that raw password is NOT in sanitized database URL
    assert secret_pass not in res["sanitized_variables"]["DATABASE_URL"]
    assert "***" in res["sanitized_variables"]["DATABASE_URL"]
    assert "..." in res["sanitized_variables"]["SECRET_KEY"]

    # Verify that warnings do not leak the raw password
    for warning in res["warnings"]:
        assert secret_pass not in warning


def test_readiness_score_hard_safety_gates():
    # 1. Broken tests must trip hard blocker even with 75/75 elsewhere
    res_failed_tests = calculate_readiness_score(
        tests_passed=False,
        critical_vulns=0,
        high_vulns=0,
        secrets_detected=False,
        health_status="operational",
        rollback_available=True,
    )
    assert res_failed_tests["deployment_blocked"] is True
    assert res_failed_tests["confidence_tier"] == "Deployment Blocked"
    assert res_failed_tests["badge_class"] == "badge-danger"
    assert any("test suite failed" in b.lower() for b in res_failed_tests["blocking_reasons"])
    assert res_failed_tests["readiness_score"] <= 35

    # 2. Critical CVE must trip hard blocker
    res_cve = calculate_readiness_score(tests_passed=True, critical_vulns=1)
    assert res_cve["deployment_blocked"] is True
    assert res_cve["confidence_tier"] == "Deployment Blocked"

    # 3. Secret leak must trip hard blocker
    res_secrets = calculate_readiness_score(tests_passed=True, secrets_detected=True)
    assert res_secrets["deployment_blocked"] is True

    # 4. All passing gets 100/100 and Ready for Production
    res_all_pass = calculate_readiness_score(tests_passed=True, critical_vulns=0, secrets_detected=False)
    assert res_all_pass["deployment_blocked"] is False
    assert res_all_pass["readiness_score"] >= 85
    assert res_all_pass["confidence_tier"] == "Ready for Production"


def test_landing_page_served():
    r = client.get("/", headers={"accept": "text/html"})
    assert r.status_code == 200
    assert "DeployEasy" in r.text
    assert "Confidence" in r.text


def test_auth_pages_served():
    r_login = client.get("/login")
    assert r_login.status_code == 200
    assert "Sign In" in r_login.text or "Welcome" in r_login.text

    r_signup = client.get("/signup")
    assert r_signup.status_code == 200
    assert "DeployEasy" in r_signup.text


def test_unauthenticated_me_returns_401():
    """Unauthenticated calls to /api/auth/me MUST return 401 Unauthorized."""
    unauth = TestClient(app)
    r_me = unauth.get("/api/auth/me")
    assert r_me.status_code == 401
    assert "Authentication required" in r_me.json()["detail"]


def test_user_registration_login_and_me():
    """Test full cryptographic registration, login, and cookie session authorization."""
    reset_auth_rate_limits()
    uid = uuid.uuid4().hex[:6]
    username = f"dev_{uid}"
    email = f"dev_{uid}@example.com"
    password = "Secur3Password!"

    c = TestClient(app)
    # 1. Register
    r_reg = c.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    assert r_reg.status_code == 201
    reg_data = r_reg.json()
    assert reg_data["user"]["username"] == username
    assert "deployeasy_session" in c.cookies

    # 2. Get /me with Session Cookie
    r_me = c.get("/api/auth/me")
    assert r_me.status_code == 200
    assert r_me.json()["username"] == username
    assert r_me.json()["role"] == "developer"

    # 3. Login
    c2 = TestClient(app)
    reset_auth_rate_limits()
    r_login = c2.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    assert r_login.status_code == 200
    assert "deployeasy_session" in c2.cookies


def test_demo_account_cannot_mutate_projects(auth_client, sample_project):
    """Demo accounts must be strictly read-only and cannot trigger rollbacks or deploys."""
    reset_auth_rate_limits()
    demo_client = TestClient(app)
    r_demo = demo_client.post("/api/auth/demo-login")
    assert r_demo.status_code == 200

    csrf = demo_client.cookies.get("deployeasy_csrf")
    headers = {"X-CSRF-Token": csrf}

    # Demo user attempting to trigger deploy
    r_trig = demo_client.post(
        "/api/deployments/trigger",
        json={
            "project_id": sample_project,
            "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "commit_message": "Unauthorized demo deploy",
        },
        headers=headers,
    )
    assert r_trig.status_code == 403
    assert "read-only access" in r_trig.json()["detail"]

    # Demo user attempting rollback
    r_roll = demo_client.post(
        "/api/deployments/rollback",
        json={
            "project_id": sample_project,
            "target_sha": "ef1482f7c0099ad4bb5e58db5f32cf8e51928014",
            "reason": "Unauthorized demo rollback",
        },
        headers=headers,
    )
    assert r_roll.status_code == 403
    assert "read-only access" in r_roll.json()["detail"]


def test_deployment_diff_endpoint(auth_client, sample_project):
    r_deps = auth_client.get(f"/api/projects/{sample_project}/deployments")
    dep_id = r_deps.json()[0]["id"]

    r_diff = auth_client.get(f"/api/deployments/{dep_id}/diff")
    assert r_diff.status_code == 200
    data = r_diff.json()
    assert "current_sha" in data
    assert "previous_sha" in data
    assert "diff_summary" in data


def test_project_costs_endpoint(auth_client, sample_project):
    r_costs = auth_client.get(f"/api/projects/{sample_project}/costs")
    assert r_costs.status_code == 200
    data = r_costs.json()
    assert "projected_monthly_cost_usd" in data
    assert "breakdown" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) >= 1


def test_incident_generator_endpoint(auth_client, sample_project):
    payload = {
        "failed_sha": "badcommit1234567890abcdef1234567890abcd",
        "rollback_sha": "ef1482f7c0099ad4bb5e58db5f32cf8e51928014",
        "symptoms": "Smoke test timed out waiting for SHA on /version",
        "log_excerpt": "Timed out waiting for badcom to go live",
    }
    r_inc = auth_client.post(f"/api/projects/{sample_project}/incidents/generate", json=payload)
    assert r_inc.status_code == 200
    inc = r_inc.json()
    assert "title" in inc
    assert "markdown_report" in inc
    assert "Incident Post-Mortem" in inc["markdown_report"]
    assert inc["failed_sha"] == "badcomm"


@patch("app.main.dispatch_webhook", return_value=(True, {"message": "ok"}))
def test_webhook_test_endpoint(mock_dispatch, auth_client, sample_project):
    payload = {
        "webhook_url": "https://discord.com/api/webhooks/test/dummy",
        "platform": "discord",
    }
    r_wh = auth_client.post(f"/api/projects/{sample_project}/webhook-test", json=payload)
    assert r_wh.status_code == 200
    data = r_wh.json()
    assert data["platform"] == "discord"
    assert "sample_payload" in data
    assert "embeds" in data["sample_payload"]
