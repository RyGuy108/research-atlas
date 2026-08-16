from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.ranking import RankedPaper
from app.domain.search import RankingStrategy


class SearchDiagnostics(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_candidates: dict[str, int]
    candidate_count: int = Field(ge=0)
    deduplicated_count: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    elapsed_ms: float = Field(ge=0)
    warnings: tuple[str, ...] = ()


class SearchOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    search_id: UUID
    topic: str
    ranking_strategy: RankingStrategy
    results: tuple[RankedPaper, ...]
    diagnostics: SearchDiagnostics
