"""Phase 2A reaction source attribution projection.

Revision ID: 20260829_05
Revises: 20260828_04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260829_05"
down_revision: str | None = "20260828_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_source_attribution",
        sa.Column("source_ref", sa.String(240), primary_key=True),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("catalog_source_attribution")
