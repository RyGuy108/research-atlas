"""Create persisted ranking evaluations.

Revision ID: 20260816_04
Revises: 20260816_03
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260816_04"
down_revision: str | None = "20260816_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ranking_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judgments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("k", sa.Integer(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("reciprocal_rank", sa.Float(), nullable=False),
        sa.Column("ndcg", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["search_id"],
            ["searches.id"],
            name=op.f("fk_ranking_evaluations_search_id_searches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ranking_evaluations")),
    )
    op.create_index(
        op.f("ix_ranking_evaluations_search_id"),
        "ranking_evaluations",
        ["search_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ranking_evaluations_search_id"), table_name="ranking_evaluations")
    op.drop_table("ranking_evaluations")
