"""Database session and engine setup for DeployEasy."""
import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

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
connect_args = {"check_same_thread": False, "timeout": 15} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="developer")  # "admin", "developer", "demo"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    projects = relationship("Project", back_populates="owner")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    csrf_token = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="sessions")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    repo_name = Column(String(150), nullable=False, unique=True, index=True)
    branch = Column(String(50), default="main")
    service_url = Column(String(255), default="")
    deploy_hook_url = Column(String(255), default="")
    status = Column(String(30), default="operational")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    owner = relationship("User", back_populates="projects")
    deployments = relationship("Deployment", back_populates="project", cascade="all, delete-orphan", order_by="desc(Deployment.created_at)")
    health_checks = relationship("HealthCheck", back_populates="project", cascade="all, delete-orphan", order_by="desc(HealthCheck.checked_at)")
    security_scans = relationship("SecurityScan", back_populates="project", cascade="all, delete-orphan", order_by="desc(SecurityScan.scanned_at)")

    @property
    def has_deploy_hook(self) -> bool:
        return bool(self.deploy_hook_url and self.deploy_hook_url.strip())


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    commit_sha = Column(String(40), nullable=False, index=True)
    commit_message = Column(String(255), default="")
    branch = Column(String(50), default="main")
    trigger_type = Column(String(30), default="git_push")  # git_push, manual, rollback
    status = Column(String(30), default="queued")  # queued, deploying, success, failure, rolled_back
    duration_seconds = Column(Integer, default=0)
    logs_summary = Column(Text, default="")
    workflow_run_id = Column(String(50), nullable=True)
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


def seed_demo_fixtures(db: SessionLocal):
    """Seed comprehensive realistic dummy data for Demo, Sandbox, and Test exploration."""
    from .auth import hash_password

    demo_user = db.query(User).filter(User.username == "demo-developer").first()
    if not demo_user:
        demo_user = User(
            username="demo-developer",
            email="demo@deployeasy.local",
            password_hash=hash_password("demo123456!"),
            role="demo",
            is_active=True,
        )
        db.add(demo_user)
        db.flush()

    # 3 Realistic Projects matching user's reference notes
    projects_def = [
        {
            "name": "Payments API",
            "repo_name": "org/payments-api",
            "branch": "main",
            "service_url": "https://payments.deployeasy.local",
            "status": "operational",
        },
        {
            "name": "Auth Gateway",
            "repo_name": "org/auth-gateway",
            "branch": "main",
            "service_url": "https://auth.deployeasy.local",
            "status": "operational",
        },
        {
            "name": "Analytics Worker",
            "repo_name": "org/analytics-worker",
            "branch": "staging",
            "service_url": "https://analytics.deployeasy.local",
            "status": "operational",
        },
    ]

    created_projects = []
    for p_info in projects_def:
        proj = db.query(Project).filter(Project.repo_name == p_info["repo_name"]).first()
        if not proj:
            proj = Project(
                name=p_info["name"],
                repo_name=p_info["repo_name"],
                branch=p_info["branch"],
                service_url=p_info["service_url"],
                deploy_hook_url="",
                status=p_info["status"],
                owner_id=demo_user.id,
            )
            db.add(proj)
            db.flush()
        created_projects.append(proj)

    primary_project = created_projects[0]

    # 5 Realistic Deployments for Primary Project
    existing_deploys = db.query(Deployment).filter(Deployment.project_id == primary_project.id).count()
    if existing_deploys == 0:
        now = datetime.now(UTC)
        deploys = [
            Deployment(
                project_id=primary_project.id,
                commit_sha="6f8b2c01994e63778a4b8782a17fcd59d18b62aa",
                commit_message="[DEMO] Upgrade container base image to Python 3.12-slim",
                branch="main",
                trigger_type="git_push",
                status="success",
                duration_seconds=42,
                logs_summary="✓ Docker multi-stage build succeeded (142MB)\n✓ Trivy container audit passed (0 critical)\n✓ Smoke tests 200 OK on /health",
                created_at=now - timedelta(minutes=15),
            ),
            Deployment(
                project_id=primary_project.id,
                commit_sha="e3876ac91fd2c97491d904b7264817c9135a907b",
                commit_message="[DEMO] Rollback to verified SHA after staging alert",
                branch="main",
                trigger_type="rollback",
                status="rolled_back",
                duration_seconds=38,
                logs_summary="✓ Rollback dispatch confirmed via GitHub Actions\n✓ Live SHA verified on /version\n✓ Fleet restored to healthy state",
                created_at=now - timedelta(hours=1),
            ),
            Deployment(
                project_id=primary_project.id,
                commit_sha="bad9104037da98231c6e18721c5b45ea108e4381",
                commit_message="[DEMO] Failed smoke probe: HTTP 500 on /health/live",
                branch="main",
                trigger_type="git_push",
                status="failure",
                duration_seconds=24,
                logs_summary="FAILED tests/test_api.py AssertionError: Expected 200 Received 500\nEndpoint /health/live returned Internal Server Error",
                created_at=now - timedelta(hours=3),
            ),
            Deployment(
                project_id=primary_project.id,
                commit_sha="a91b42c8821d743a9183765e902b41cb9127ea63",
                commit_message="[DEMO] Add Redis caching layer and connection pool",
                branch="main",
                trigger_type="git_push",
                status="success",
                duration_seconds=51,
                logs_summary="✓ Build succeeded\n✓ CI lint & unit tests passed (74/74)\n✓ Zero downtime rollout completed",
                created_at=now - timedelta(days=1),
            ),
            Deployment(
                project_id=primary_project.id,
                commit_sha="f1996ee10a9c823199b45e2a901d8362b172a501",
                commit_message="[DEMO] Initial production release with verified container",
                branch="main",
                trigger_type="manual",
                status="success",
                duration_seconds=45,
                logs_summary="✓ Initial repository setup\n✓ Base container deployed to Render\n✓ Verified live version",
                created_at=now - timedelta(days=3),
            ),
        ]
        for d in deploys:
            db.add(d)

    # Health Checks (28ms response time, matching user's handwritten notes)
    for p in created_projects:
        existing_hc = db.query(HealthCheck).filter(HealthCheck.project_id == p.id).first()
        if not existing_hc:
            db.add(HealthCheck(
                project_id=p.id,
                endpoint="/health",
                status_code=200,
                response_time_ms=28.4,
                is_healthy=True,
            ))

    # Security Scans (Critical 0, High 2, Medium 5, Low 8)
    existing_scan = db.query(SecurityScan).filter(SecurityScan.project_id == primary_project.id).first()
    if not existing_scan:
        db.add(SecurityScan(
            project_id=primary_project.id,
            scan_type="trivy",
            target="docker.io/library/deployeasy:latest",
            critical_count=0,
            high_count=2,
            medium_count=5,
            low_count=8,
            passed=True,
            findings_json='[{"id":"CVE-2024-1234","severity":"HIGH","pkg":"openssl","fixed_in":"3.0.13"},{"id":"CVE-2024-5678","severity":"HIGH","pkg":"curl","fixed_in":"8.6.0"}]',
        ))
        db.add(SecurityScan(
            project_id=primary_project.id,
            scan_type="gitleaks",
            target="git-commits",
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            passed=True,
            findings_json="[]",
        ))

    db.commit()


def run_migrations() -> None:
    """Apply Alembic migrations in deployed environments; create tables for tests/dev fallback."""
    alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
    if config.ENVIRONMENT in ("production", "prod") and os.getenv("TESTING") != "1":
        if not os.path.exists(alembic_ini_path):
            raise FileNotFoundError("alembic.ini is required in production deployments")
        from alembic.config import Config

        from alembic import command

        cfg = Config(alembic_ini_path)
        command.upgrade(cfg, "head")
        return
    Base.metadata.create_all(bind=engine)


def init_db():
    """Create all tables or apply migrations, and optionally seed admin user from environment variables.
    
    Zero hardcoded credentials or password hashes exist in production code.
    """
    run_migrations()
    db = SessionLocal()
    try:
        # Only seed admin if explicit password is provided in environment
        if config.DEPLOYEASY_ADMIN_PASSWORD:
            admin_user = db.query(User).filter(User.username == config.DEPLOYEASY_ADMIN_USER).first()
            if not admin_user:
                from .auth import hash_password

                admin_user = User(
                    username=config.DEPLOYEASY_ADMIN_USER,
                    email=config.DEPLOYEASY_ADMIN_EMAIL,
                    password_hash=hash_password(config.DEPLOYEASY_ADMIN_PASSWORD),
                    role="admin",
                    is_active=True,
                )
                db.add(admin_user)
                db.commit()
            else:
                from .auth import hash_password, verify_password

                admin_user.role = "admin"
                if not verify_password(config.DEPLOYEASY_ADMIN_PASSWORD, admin_user.password_hash):
                    admin_user.password_hash = hash_password(config.DEPLOYEASY_ADMIN_PASSWORD)
                db.commit()

        # Only seed demo fixtures if explicitly configured via environment variable
        if config.DEPLOYEASY_DEMO_MODE:
            seed_demo_fixtures(db)
    finally:
        db.close()
