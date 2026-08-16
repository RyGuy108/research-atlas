from datetime import date

from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.services.paper_normalizer import canonical_paper_key, normalize_and_deduplicate


def make_paper(
    provider: PaperProvider,
    identifier: str,
    *,
    title: str = "Adaptive Retrieval for Small Language Models",
    abstract: str = "A short abstract.",
    doi: str | None = None,
    arxiv_id: str | None = None,
    year: int = 2026,
    citation_count: int = 0,
) -> Paper:
    return Paper(
        sources=(PaperSource(provider=provider, identifier=identifier),),
        title=title,
        abstract=abstract,
        authors=(Author(name="Ada Researcher"),),
        doi=doi,
        arxiv_id=arxiv_id,
        citation_count=citation_count,
        published_on=date(year, 8, 1),
        landing_page_url="https://example.org/paper",
    )


def test_deduplicate_merges_doi_matches_and_preserves_sources() -> None:
    arxiv = make_paper(
        PaperProvider.ARXIV,
        "2608.00001v2",
        doi="https://doi.org/10.1000/Example.1",
        arxiv_id="2608.00001v2",
    )
    openalex = make_paper(
        PaperProvider.OPENALEX,
        "https://openalex.org/W123",
        abstract="A much longer abstract with experiment and result details.",
        doi="10.1000/example.1",
        arxiv_id="https://arxiv.org/abs/2608.00001",
        citation_count=14,
    )

    result = normalize_and_deduplicate([arxiv, openalex])

    assert len(result) == 1
    assert result[0].doi == "10.1000/example.1"
    assert result[0].arxiv_id == "2608.00001"
    assert result[0].citation_count == 14
    assert result[0].abstract == openalex.abstract
    assert {(source.provider, source.identifier) for source in result[0].sources} == {
        (PaperProvider.ARXIV, "2608.00001"),
        (PaperProvider.OPENALEX, "W123"),
    }


def test_deduplicate_uses_title_and_year_when_ids_are_missing() -> None:
    first = make_paper(PaperProvider.ARXIV, "one", title="RAG: A Practical Study")
    second = make_paper(PaperProvider.OPENALEX, "two", title="rag — a practical study")

    assert len(normalize_and_deduplicate([first, second])) == 1


def test_deduplicate_keeps_same_title_from_different_years() -> None:
    first = make_paper(PaperProvider.ARXIV, "one", title="Shared Title", year=2025)
    second = make_paper(PaperProvider.OPENALEX, "two", title="Shared Title", year=2026)

    assert len(normalize_and_deduplicate([first, second])) == 2


def test_deduplicate_bridge_record_joins_existing_identifier_groups() -> None:
    doi_record = make_paper(
        PaperProvider.OPENALEX,
        "W123",
        title="Provider title",
        doi="10.1000/example.1",
    )
    arxiv_record = make_paper(
        PaperProvider.ARXIV,
        "2608.00001",
        title="Preprint title",
        arxiv_id="2608.00001",
    )
    bridge = make_paper(
        PaperProvider.OPENALEX,
        "W456",
        title="A corrected title",
        doi="10.1000/example.1",
        arxiv_id="2608.00001",
    )

    result = normalize_and_deduplicate([doi_record, arxiv_record, bridge])

    assert len(result) == 1
    assert result[0].doi == "10.1000/example.1"
    assert result[0].arxiv_id == "2608.00001"


def test_canonical_key_prefers_doi() -> None:
    paper = make_paper(
        PaperProvider.ARXIV,
        "2608.00001",
        doi="HTTPS://DOI.ORG/10.1000/Example.1",
        arxiv_id="2608.00001",
    )

    assert canonical_paper_key(paper) == "doi:10.1000/example.1"
