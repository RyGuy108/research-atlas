from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PipelineStage(StrEnum):
    DISCOVERY = "discovery"
    NORMALIZATION = "normalization"
    RANKING = "ranking"
    CITATION_EXPANSION = "citation_expansion"
    EXTRACTION = "extraction"
    CLUSTERING = "clustering"
    SYNTHESIS = "synthesis"


class PipelineStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


PIPELINE_STAGES = tuple(PipelineStage)


class PipelineState(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: UUID = Field(default_factory=uuid4)
    status: PipelineStatus = PipelineStatus.RUNNING
    current_stage: PipelineStage | None = PipelineStage.DISCOVERY
    completed_stages: tuple[PipelineStage, ...] = ()
    error: str | None = None

    @property
    def progress_percent(self) -> int:
        return round(len(self.completed_stages) / len(PIPELINE_STAGES) * 100)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.status == PipelineStatus.RUNNING and self.current_stage is None:
            raise ValueError("a running pipeline requires a current stage")
        if self.status == PipelineStatus.COMPLETED and self.completed_stages != PIPELINE_STAGES:
            raise ValueError("a completed pipeline requires every stage")
        if self.status == PipelineStatus.FAILED and not self.error:
            raise ValueError("a failed pipeline requires an error message")
        return self


def advance_pipeline(state: PipelineState) -> PipelineState:
    """Finish the active stage and return the next valid immutable pipeline state."""
    if state.status != PipelineStatus.RUNNING or state.current_stage is None:
        raise ValueError("only a running pipeline can advance")

    expected_stage = PIPELINE_STAGES[len(state.completed_stages)]
    if state.current_stage != expected_stage:
        raise ValueError(f"expected {expected_stage.value}, found {state.current_stage.value}")

    completed = (*state.completed_stages, state.current_stage)
    if len(completed) == len(PIPELINE_STAGES):
        return state.model_copy(
            update={
                "status": PipelineStatus.COMPLETED,
                "current_stage": None,
                "completed_stages": completed,
            }
        )

    return state.model_copy(
        update={
            "current_stage": PIPELINE_STAGES[len(completed)],
            "completed_stages": completed,
        }
    )


def fail_pipeline(state: PipelineState, error: str) -> PipelineState:
    if state.status != PipelineStatus.RUNNING:
        raise ValueError("only a running pipeline can fail")
    if not error.strip():
        raise ValueError("an error message is required")
    return state.model_copy(
        update={
            "status": PipelineStatus.FAILED,
            "current_stage": None,
            "error": error.strip(),
        }
    )
