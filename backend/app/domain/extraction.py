from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.paper import Paper


class EvidenceSection(StrEnum):
    TITLE = "title"
    ABSTRACT = "abstract"


class EvidenceQuote(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    quote: str = Field(min_length=3, max_length=600)
    section: EvidenceSection


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str = Field(min_length=3, max_length=1_000)
    evidence: tuple[EvidenceQuote, ...] = Field(min_length=1, max_length=3)


class PaperExtraction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    problem: EvidenceClaim
    method: EvidenceClaim
    results: tuple[EvidenceClaim, ...] = Field(min_length=1, max_length=5)
    contributions: tuple[EvidenceClaim, ...] = Field(min_length=1, max_length=5)
    limitations: tuple[EvidenceClaim, ...] = Field(max_length=5)
    keywords: tuple[str, ...] = Field(min_length=3, max_length=10)


class ExtractionUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class ExtractionRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    extraction: PaperExtraction
    model: str
    prompt_version: str
    provider_response_id: str
    usage: ExtractionUsage
    elapsed_ms: float = Field(ge=0)


class ExtractionTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_id: UUID
    rank: int = Field(ge=1)
    paper: Paper


class CompletedExtraction(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_id: UUID
    rank: int = Field(ge=1)
    title: str
    run: ExtractionRun


class ExtractionFailure(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_id: UUID
    rank: int = Field(ge=1)
    title: str
    error: str


class ExtractionBatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    search_id: UUID
    requested_count: int = Field(ge=0)
    completed: tuple[CompletedExtraction, ...]
    failures: tuple[ExtractionFailure, ...]
    usage: ExtractionUsage
