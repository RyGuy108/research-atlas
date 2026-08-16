from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.extraction import PaperExtraction


class LandscapePaper(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_id: UUID
    rank: int = Field(ge=1)
    title: str
    extraction: PaperExtraction


class PaperPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_id: UUID
    cluster_id: int = Field(ge=0)
    membership_score: float = Field(ge=0, le=1)
    x: float = Field(ge=-1, le=1)
    y: float = Field(ge=-1, le=1)


class ThemeCluster(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: int = Field(ge=0)
    label: str
    paper_ids: tuple[UUID, ...] = Field(min_length=1)


class SimilarityEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_paper_id: UUID
    target_paper_id: UUID
    similarity: float = Field(ge=0, le=1)


class ClusteredLandscape(BaseModel):
    model_config = ConfigDict(frozen=True)

    clusters: tuple[ThemeCluster, ...] = Field(min_length=1)
    positions: tuple[PaperPosition, ...] = Field(min_length=1)
    similarity_edges: tuple[SimilarityEdge, ...]
    silhouette_score: float | None = Field(default=None, ge=-1, le=1)


class RelationshipKind(StrEnum):
    SUPPORTS = "supports"
    EXTENDS = "extends"
    CONTRASTS = "contrasts"
    SHARES_METHOD = "shares_method"


class ClusterNarrative(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cluster_id: int = Field(ge=0)
    name: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=10, max_length=1_500)
    evidence_paper_ids: tuple[UUID, ...] = Field(min_length=1)


class ResearchRelationship(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_paper_id: UUID
    target_paper_id: UUID
    kind: RelationshipKind
    summary: str = Field(min_length=10, max_length=1_000)


class ResearchTension(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str = Field(min_length=10, max_length=1_000)
    evidence_paper_ids: tuple[UUID, ...] = Field(min_length=2)


class OpenResearchQuestion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question: str = Field(min_length=10, max_length=500)
    rationale: str = Field(min_length=10, max_length=1_000)
    evidence_paper_ids: tuple[UUID, ...] = Field(min_length=1)


class LandscapeSynthesis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    overview: str = Field(min_length=20, max_length=2_000)
    clusters: tuple[ClusterNarrative, ...] = Field(min_length=1)
    relationships: tuple[ResearchRelationship, ...]
    tensions: tuple[ResearchTension, ...]
    open_questions: tuple[OpenResearchQuestion, ...] = Field(min_length=1, max_length=10)


class SynthesisUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class LandscapeSynthesisRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    synthesis: LandscapeSynthesis
    model: str
    prompt_version: str
    provider_response_id: str
    usage: SynthesisUsage
    elapsed_ms: float = Field(ge=0)
