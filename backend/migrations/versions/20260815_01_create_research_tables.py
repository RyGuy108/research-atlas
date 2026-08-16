"""Create research discovery tables.

Revision ID: 20260815_01
Revises:
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260815_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=240), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strategies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_searches")),
    )
    op.create_table(
        "papers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_key", sa.String(length=600), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("authors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("arxiv_id", sa.String(length=100), nullable=True),
        sa.Column("citation_count", sa.Integer(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("updated_on", sa.Date(), nullable=True),
        sa.Column("venue", sa.String(length=200), nullable=True),
        sa.Column("landing_page_url", sa.Text(), nullable=False),
        sa.Column("pdf_url", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_papers")),
    )
    op.create_index(op.f("ix_papers_arxiv_id"), "papers", ["arxiv_id"], unique=True)
    op.create_index(op.f("ix_papers_canonical_key"), "papers", ["canonical_key"], unique=True)
    op.create_index(op.f("ix_papers_doi"), "papers", ["doi"], unique=True)
    op.create_table(
        "paper_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["paper_id"],
            ["papers.id"],
            name=op.f("fk_paper_sources_paper_id_papers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_sources")),
        sa.UniqueConstraint("paper_id", "provider", name="uq_paper_sources_paper_provider"),
        sa.UniqueConstraint(
            "provider", "external_id", name="uq_paper_sources_provider_external_id"
        ),
    )
    op.create_table(
        "search_results",
        sa.Column("search_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["paper_id"],
            ["papers.id"],
            name=op.f("fk_search_results_paper_id_papers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["search_id"],
            ["searches.id"],
            name=op.f("fk_search_results_search_id_searches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("search_id", "paper_id", name=op.f("pk_search_results")),
    )


def downgrade() -> None:
    op.drop_table("search_results")
    op.drop_table("paper_sources")
    op.drop_index(op.f("ix_papers_doi"), table_name="papers")
    op.drop_index(op.f("ix_papers_canonical_key"), table_name="papers")
    op.drop_index(op.f("ix_papers_arxiv_id"), table_name="papers")
    op.drop_table("papers")
    op.drop_table("searches")
