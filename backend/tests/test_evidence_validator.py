from datetime import date

import pytest

from app.domain.extraction import (
    EvidenceClaim,
    EvidenceQuote,
    EvidenceSection,
    PaperExtraction,
)
from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.services.evidence_validator import EvidenceValidationError, validate_extraction_evidence


def test_validator_accepts_exact_quotes_with_normalized_whitespace_and_case() -> None:
    paper = _paper()
    extraction = _extraction(
        EvidenceQuote(
            quote="WE INTRODUCE a confidence-aware retrieval policy.",
            section=EvidenceSection.ABSTRACT,
        )
    )

    validate_extraction_evidence(paper, extraction)


def test_validator_rejects_unsupported_evidence() -> None:
    extraction = _extraction(
        EvidenceQuote(
            quote="The approach improves accuracy by twenty percent.",
            section=EvidenceSection.ABSTRACT,
        )
    )

    with pytest.raises(EvidenceValidationError, match="not present"):
        validate_extraction_evidence(_paper(), extraction)


def test_validator_checks_the_declared_section() -> None:
    extraction = _extraction(
        EvidenceQuote(
            quote="Adaptive Retrieval",
            section=EvidenceSection.ABSTRACT,
        )
    )

    with pytest.raises(EvidenceValidationError, match="abstract"):
        validate_extraction_evidence(_paper(), extraction)


def _extraction(evidence: EvidenceQuote) -> PaperExtraction:
    claim = EvidenceClaim(summary="A grounded statement.", evidence=(evidence,))
    return PaperExtraction(
        problem=claim,
        method=claim,
        results=(claim,),
        contributions=(claim,),
        limitations=(),
        keywords=("retrieval", "language models", "evaluation"),
    )


def _paper() -> Paper:
    return Paper(
        sources=(PaperSource(provider=PaperProvider.ARXIV, identifier="2608.00001"),),
        title="Adaptive Retrieval",
        abstract=(
            "We introduce a confidence-aware retrieval policy. "
            "It reduces unnecessary searches while preserving answer quality."
        ),
        authors=(Author(name="Ada Researcher"),),
        published_on=date(2026, 8, 1),
        landing_page_url="https://arxiv.org/abs/2608.00001",
    )
