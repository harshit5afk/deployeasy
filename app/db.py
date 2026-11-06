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
    """Explicitly isolated demo fixture seeder. Only active in demo mode."""
    demo_user = db.query(User).filter(User.username == "demo-developer").first()
    if not demo_user:
        from .auth import hash_password

        demo_user = User(
            username="demo-developer",
            email="demo@deployeasy.local",
            password_hash=hash_password("demo123456!"),
            role="demo",
            is_active=True,
        )
        db.add(demo_user)
        db.flush()

    existing_demo_project = db.query(Project).filter(Project.repo_name == "demo/sample-service").first()
    if not existing_demo_project:
        demo_project = Project(
            name="Demo Sample Service",
            repo_name="demo/sample-service",
            branch="main",
            service_url="https://demo.deployeasy.local",
            deploy_hook_url="",
            status="operational",
            owner_id=demo_user.id,
        )
        db.add(demo_project)
        db.flush()

        # Add demo deployments clearly flagged as demo data
        db.add(Deployment(
            project_id=demo_project.id,
            commit_sha="e3876ac91fd2c97491d904b7264817c9135a907b",
            commit_message="[DEMO] Initial verified container build",
            branch="main",
            trigger_type="manual",
            status="success",
            duration_seconds=45,
            logs_summary="✓ Demo pipeline test passed",
        ))
        db.commit()


def init_db():
    """Create all tables and seed default admin user. Real production data remains clean."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            from .auth import hash_password

            admin_user = User(
                username="admin",
                email="admin@deployeasy.local",
                password_hash=hash_password("admin123456!"),
                role="admin",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()

        # Only seed demo fixtures if explicitly configured via environment variable
        if config.DEPLOYEASY_DEMO_MODE:
            seed_demo_fixtures(db)
    finally:
        db.close()
