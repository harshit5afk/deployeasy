"""Initial schema for DeployEasy: users, user_sessions, projects, deployments, health_checks, security_scans

Revision ID: 001_initial
Revises: 
Create Date: 2026-11-06 20:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="developer", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # User Sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(length=64), nullable=False),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_sessions_id"), "user_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_user_sessions_session_token"), "user_sessions", ["session_token"], unique=True)
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)

    # Projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("repo_name", sa.String(length=150), nullable=False),
        sa.Column("branch", sa.String(length=50), server_default="main", nullable=False),
        sa.Column("service_url", sa.String(length=255), server_default="", nullable=False),
        sa.Column("deploy_hook_url", sa.String(length=255), server_default="", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="operational", nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(op.f("ix_projects_repo_name"), "projects", ["repo_name"], unique=True)
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)

    # Deployments table
    op.create_table(
        "deployments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("commit_message", sa.String(length=255), server_default="", nullable=False),
        sa.Column("branch", sa.String(length=50), server_default="main", nullable=False),
        sa.Column("trigger_type", sa.String(length=30), server_default="git_push", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="queued", nullable=False),
        sa.Column("duration_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("logs_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("workflow_run_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deployments_id"), "deployments", ["id"], unique=False)
    op.create_index(op.f("ix_deployments_project_id"), "deployments", ["project_id"], unique=False)
    op.create_index(op.f("ix_deployments_commit_sha"), "deployments", ["commit_sha"], unique=False)

    # Health Checks table
    op.create_table(
        "health_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=100), server_default="/health", nullable=False),
        sa.Column("status_code", sa.Integer(), server_default="200", nullable=False),
        sa.Column("response_time_ms", sa.Float(), server_default="12.5", nullable=False),
        sa.Column("is_healthy", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_health_checks_id"), "health_checks", ["id"], unique=False)
    op.create_index(op.f("ix_health_checks_project_id"), "health_checks", ["project_id"], unique=False)

    # Security Scans table
    op.create_table(
        "security_scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("scan_type", sa.String(length=30), server_default="trivy", nullable=False),
        sa.Column("target", sa.String(length=100), server_default="docker-image", nullable=False),
        sa.Column("critical_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("high_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("medium_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("low_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("passed", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("findings_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("scanned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_security_scans_id"), "security_scans", ["id"], unique=False)
    op.create_index(op.f("ix_security_scans_project_id"), "security_scans", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_table("security_scans")
    op.drop_table("health_checks")
    op.drop_table("deployments")
    op.drop_table("projects")
    op.drop_table("user_sessions")
    op.drop_table("users")
