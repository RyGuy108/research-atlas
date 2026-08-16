from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SearchModel(Base):
    __tablename__ = "searches"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(String(240))
    filters: Mapped[dict[str, Any]] = mapped_column(JSON)
    strategies: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    results: Mapped[list[SearchResultModel]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )


class PaperModel(Base):
    __tablename__ = "papers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    canonical_key: Mapped[str] = mapped_column(String(600), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    abstract: Mapped[str] = mapped_column(Text)
    authors: Mapped[list[dict[str, str | None]]] = mapped_column(JSON)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    doi: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    published_on: Mapped[date] = mapped_column(Date)
    updated_on: Mapped[date | None] = mapped_column(Date)
    venue: Mapped[str | None] = mapped_column(String(200))
    landing_page_url: Mapped[str] = mapped_column(Text)
    pdf_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sources: Mapped[list[PaperSourceModel]] = relationship(
        back_populates="paper", cascade="all, delete-orphan", lazy="selectin"
    )
    search_results: Mapped[list[SearchResultModel]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )


class PaperSourceModel(Base):
    __tablename__ = "paper_sources"
    __table_args__ = (
        UniqueConstraint("provider", "external_id"),
        UniqueConstraint("paper_id", "provider"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    paper_id: Mapped[UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(40))
    external_id: Mapped[str] = mapped_column(String(100))

    paper: Mapped[PaperModel] = relationship(back_populates="sources")


class SearchResultModel(Base):
    __tablename__ = "search_results"

    search_id: Mapped[UUID] = mapped_column(
        ForeignKey("searches.id", ondelete="CASCADE"), primary_key=True
    )
    paper_id: Mapped[UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    rank: Mapped[int] = mapped_column(Integer)
    relevance_score: Mapped[float | None] = mapped_column(Float)

    search: Mapped[SearchModel] = relationship(back_populates="results")
    paper: Mapped[PaperModel] = relationship(back_populates="search_results")


class PaperExtractionModel(Base):
    __tablename__ = "paper_extractions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["search_id", "paper_id"],
            ["search_results.search_id", "search_results.paper_id"],
            ondelete="CASCADE",
        ),
    )

    search_id: Mapped[UUID] = mapped_column(primary_key=True)
    paper_id: Mapped[UUID] = mapped_column(primary_key=True)
    extraction: Mapped[dict[str, Any]] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(100))
    provider_response_id: Mapped[str] = mapped_column(String(255))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    total_tokens: Mapped[int] = mapped_column(Integer)
    elapsed_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
