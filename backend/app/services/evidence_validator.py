import re

from app.domain.extraction import EvidenceClaim, EvidenceSection, PaperExtraction
from app.domain.paper import Paper


class EvidenceValidationError(ValueError):
    """Raised when an extracted quote cannot be traced to the supplied paper metadata."""


def validate_extraction_evidence(paper: Paper, extraction: PaperExtraction) -> None:
    sources = {
        EvidenceSection.TITLE: _comparable_text(paper.title),
        EvidenceSection.ABSTRACT: _comparable_text(paper.abstract),
    }
    for claim in _claims(extraction):
        for evidence in claim.evidence:
            quote = _comparable_text(evidence.quote)
            if quote not in sources[evidence.section]:
                raise EvidenceValidationError(
                    f"evidence quote is not present in paper {evidence.section.value}"
                )


def _claims(extraction: PaperExtraction) -> tuple[EvidenceClaim, ...]:
    return (
        extraction.problem,
        extraction.method,
        *extraction.results,
        *extraction.contributions,
        *extraction.limitations,
    )


def _comparable_text(value: str) -> str:
    # Whitespace normalization tolerates PDF/metadata line wrapping without weakening attribution.
    return re.sub(r"\s+", " ", value).strip().casefold()
