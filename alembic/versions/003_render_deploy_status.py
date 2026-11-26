"""Store the latest Render deployment status for each connected service."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_render_deploy_status"
down_revision: str | None = "002_render_service_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("render_deploy_status", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "render_deploy_status")
