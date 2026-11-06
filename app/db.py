"""Database session and engine setup for DeployEasy."""
from collections.abc import Generator
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from . import config

# SQLite requires check_same_thread=False for multithreaded FastAPI requests
connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    repo_name = Column(String(150), nullable=False, unique=True, index=True)
    branch = Column(String(50), default="main")
    service_url = Column(String(255), default="")
    deploy_hook_url = Column(String(255), default="")
    status = Column(String(30), default="operational")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    deployments = relationship("Deployment", back_populates="project", cascade="all, delete-orphan", order_by="desc(Deployment.created_at)")
    health_checks = relationship("HealthCheck", back_populates="project", cascade="all, delete-orphan", order_by="desc(HealthCheck.checked_at)")
    security_scans = relationship("SecurityScan", back_populates="project", cascade="all, delete-orphan", order_by="desc(SecurityScan.scanned_at)")


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    commit_sha = Column(String(40), nullable=False, index=True)
    commit_message = Column(String(255), default="")
    branch = Column(String(50), default="main")
    trigger_type = Column(String(30), default="git_push")  # git_push, manual, rollback
    status = Column(String(30), default="success")  # success, failure, building, rolled_back
    duration_seconds = Column(Integer, default=45)
    logs_summary = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)

    project = relationship("Project", back_populates="deployments")


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    endpoint = Column(String(100), default="/health")
    status_code = Column(Integer, default=200)
    response_time_ms = Column(Float, default=12.5)
    is_healthy = Column(Boolean, default=True)
    error_message = Column(String(255), nullable=True)
    checked_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)

    project = relationship("Project", back_populates="health_checks")


class SecurityScan(Base):
    __tablename__ = "security_scans"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    scan_type = Column(String(30), default="trivy")  # trivy, gitleaks
    target = Column(String(100), default="docker-image")
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    passed = Column(Boolean, default=True)
    findings_json = Column(Text, default="[]")
    scanned_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)

    project = relationship("Project", back_populates="security_scans")


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and seed initial data if empty."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if any project exists
        existing = db.query(Project).first()
        if not existing:
            default_project = Project(
                name="DeployEasy Service",
                repo_name=config.GITHUB_REPO or "harshit5afk/deployeasy",
                branch="main",
                service_url=config.SERVICE_URL or "http://localhost:8080",
                deploy_hook_url=config.RENDER_DEPLOY_HOOK_URL or "https://api.render.com/deploy/srv-placeholder",
                status="operational",
            )
            db.add(default_project)
            db.flush()

            # Seed realistic historical deployments
            initial_deployments = [
                Deployment(
                    project_id=default_project.id,
                    commit_sha=config.GIT_SHA if len(config.GIT_SHA) == 40 else "e3876ac91fd2c97491d904b7264817c9135a907b",
                    commit_message="feat(platform): deploy verified container with automated healthcheck & rollback",
                    branch="main",
                    trigger_type="git_push",
                    status="success",
                    duration_seconds=52,
                    logs_summary="✓ Tests passed (Ruff + pytest)\n✓ Image scanned with Trivy (0 vulnerabilities)\n✓ Deployed to Render\n✓ Smoke test verified live SHA",
                ),
                Deployment(
                    project_id=default_project.id,
                    commit_sha="40e54ca854b79b1d38ae859069d273a216c52bb1",
                    commit_message="feat(ui): modern developer platform landing page and interactive telemetry",
                    branch="main",
                    trigger_type="git_push",
                    status="success",
                    duration_seconds=47,
                    logs_summary="✓ Build succeeded\n✓ Published ghcr.io/harshit5afk/deployeasy:40e54ca\n✓ Health verified in 18s",
                ),
                Deployment(
                    project_id=default_project.id,
                    commit_sha="26ea6421398bb290ef4081c748bb7014b2d56a12",
                    commit_message="docs: phase 7a & 8 - architecture diagrams, demo script, and complete README",
                    branch="main",
                    trigger_type="git_push",
                    status="success",
                    duration_seconds=41,
                    logs_summary="✓ Documentation updated\n✓ Pipeline tests passed",
                ),
                Deployment(
                    project_id=default_project.id,
                    commit_sha="ef1482f7c0099ad4bb5e58db5f32cf8e51928014",
                    commit_message="feat(ops): manual rollback by SHA with GHCR verification and incident playbook",
                    branch="main",
                    trigger_type="rollback",
                    status="rolled_back",
                    duration_seconds=38,
                    logs_summary="✓ Rollback requested to SHA ef1482f\n✓ Verified image in GHCR\n✓ Rolled back live deployment in 22s",
                ),
            ]
            for dep in initial_deployments:
                db.add(dep)

            # Seed recent health checks
            initial_checks = [
                HealthCheck(project_id=default_project.id, endpoint="/health", status_code=200, response_time_ms=14.2, is_healthy=True),
                HealthCheck(project_id=default_project.id, endpoint="/version", status_code=200, response_time_ms=11.8, is_healthy=True),
                HealthCheck(project_id=default_project.id, endpoint="/metrics", status_code=200, response_time_ms=9.5, is_healthy=True),
            ]
            for hc in initial_checks:
                db.add(hc)

            # Seed security scans
            trivy_scan = SecurityScan(
                project_id=default_project.id,
                scan_type="trivy",
                target="ghcr.io/harshit5afk/deployeasy:latest",
                critical_count=0,
                high_count=0,
                medium_count=1,
                low_count=3,
                passed=True,
                findings_json='[{"pkg": "urllib3", "severity": "MEDIUM", "cve": "CVE-2024-37891", "fixed_version": "2.2.2"}]',
            )
            gitleaks_scan = SecurityScan(
                project_id=default_project.id,
                scan_type="gitleaks",
                target="git-history (all branches)",
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                passed=True,
                findings_json='[]',
            )
            db.add(trivy_scan)
            db.add(gitleaks_scan)

            db.commit()
    finally:
        db.close()
