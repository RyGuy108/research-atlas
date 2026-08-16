from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.ranking_metrics import RankingMetrics


class RelevanceJudgment(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_id: UUID
    relevance: float = Field(ge=0, le=3)


class RankingEvaluationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    judgments: tuple[RelevanceJudgment, ...] = Field(min_length=1)
    k: int = Field(default=10, ge=1, le=100)

    @field_validator("judgments")
    @classmethod
    def require_unique_papers(
        cls, judgments: tuple[RelevanceJudgment, ...]
    ) -> tuple[RelevanceJudgment, ...]:
        paper_ids = [judgment.paper_id for judgment in judgments]
        if len(paper_ids) != len(set(paper_ids)):
            raise ValueError("each paper can only be judged once")
        return judgments


class RankingEvaluationRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    evaluation_id: UUID = Field(default_factory=uuid4)
    search_id: UUID
    judgments: tuple[RelevanceJudgment, ...]
    metrics: RankingMetrics
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
