"""Record the Render service created for each connected project."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_render_service_id"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("render_service_id", sa.String(length=80), nullable=True))
    op.create_index("ix_projects_render_service_id", "projects", ["render_service_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_projects_render_service_id", table_name="projects")
    op.drop_column("projects", "render_service_id")
