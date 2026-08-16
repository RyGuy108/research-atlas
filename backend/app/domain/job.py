from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.extraction import ExtractionBatch
from app.domain.landscape import ResearchLandscape
from app.domain.search import SearchRequest
from app.domain.search_result import SearchOutcome


class PipelineJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PipelineJobStage(StrEnum):
    DISCOVER = "discover"
    RERANK = "rerank"
    EXTRACT = "extract"
    MAP = "map"
    COMPLETE = "complete"


class PipelineJobRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    search: SearchRequest
    extraction_limit: int = Field(default=5, ge=2, le=25)


class PipelineArtifacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    search: SearchOutcome | None = None
    extractions: ExtractionBatch | None = None
    landscape: ResearchLandscape | None = None


class PipelineProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage: PipelineJobStage
    percent: int = Field(ge=0, le=100)
    message: str = Field(min_length=1, max_length=240)
    artifacts: PipelineArtifacts = Field(default_factory=PipelineArtifacts)


class PipelineJobSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: UUID = Field(default_factory=uuid4)
    status: PipelineJobStatus = PipelineJobStatus.QUEUED
    stage: PipelineJobStage = PipelineJobStage.DISCOVER
    percent: int = Field(default=0, ge=0, le=100)
    message: str = "Waiting for a worker"
    artifacts: PipelineArtifacts = Field(default_factory=PipelineArtifacts)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def terminal(self) -> bool:
        return self.status in {PipelineJobStatus.SUCCEEDED, PipelineJobStatus.FAILED}
