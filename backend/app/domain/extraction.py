from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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
