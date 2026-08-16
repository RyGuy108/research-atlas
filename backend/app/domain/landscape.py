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
