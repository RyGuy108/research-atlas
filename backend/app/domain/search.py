from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RankingStrategy(StrEnum):
    KEYWORD = "keyword"
    EMBEDDING = "embedding"
    CROSS_ENCODER = "cross_encoder"
    CITATION_EXPANSION = "citation_expansion"


class SearchFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    venues: frozenset[str] = Field(default_factory=frozenset)
    year_from: int | None = Field(default=None, ge=1950, le=2100)
    year_to: int | None = Field(default=None, ge=1950, le=2100)
    max_candidates: int = Field(default=100, ge=10, le=500)
    citation_depth: int = Field(default=0, ge=0, le=2)

    @model_validator(mode="after")
    def validate_year_range(self) -> Self:
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError("year_from must be less than or equal to year_to")
        return self


class SearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic: str = Field(min_length=3, max_length=240)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    strategies: tuple[RankingStrategy, ...] = (RankingStrategy.CROSS_ENCODER,)

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, topic: str) -> str:
        return " ".join(topic.split())

    @field_validator("strategies")
    @classmethod
    def require_unique_strategies(
        cls, strategies: tuple[RankingStrategy, ...]
    ) -> tuple[RankingStrategy, ...]:
        if not strategies:
            raise ValueError("at least one ranking strategy is required")
        if len(strategies) != len(set(strategies)):
            raise ValueError("ranking strategies must be unique")
        return strategies
