"""Create persisted research landscapes.

Revision ID: 20260816_03
Revises: 20260816_02
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260816_03"
down_revision: str | None = "20260816_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_landscapes",
        sa.Column("search_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clustered", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthesis", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("provider_response_id", sa.String(length=255), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("elapsed_ms", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["search_id"],
            ["searches.id"],
            name=op.f("fk_research_landscapes_search_id_searches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("search_id", name=op.f("pk_research_landscapes")),
    )


def downgrade() -> None:
    op.drop_table("research_landscapes")
