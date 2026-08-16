import re
import unicodedata
from collections.abc import Iterable

from app.domain.paper import Author, Paper, PaperProvider, PaperSource


def normalize_and_deduplicate(papers: Iterable[Paper]) -> list[Paper]:
    """Collapse provider records by durable identifiers, then conservative title matching."""
    canonical: list[Paper | None] = []
    key_to_index: dict[str, int] = {}

    for raw_paper in papers:
        paper = normalize_paper(raw_paper)
        matching_indexes = {
            key_to_index[key] for key in _identity_keys(paper) if key in key_to_index
        }
        if not matching_indexes:
            index = len(canonical)
            canonical.append(paper)
        else:
            index = min(matching_indexes)
            merged = paper
            for matching_index in matching_indexes:
                existing = canonical[matching_index]
                if existing is not None:
                    merged = _merge_papers(existing, merged)
                if matching_index != index:
                    canonical[matching_index] = None
            canonical[index] = merged
            for key, matching_index in tuple(key_to_index.items()):
                if matching_index in matching_indexes:
                    key_to_index[key] = index

        resolved = canonical[index]
        if resolved is None:
            raise AssertionError("canonical paper unexpectedly missing")
        for key in _identity_keys(resolved):
            key_to_index[key] = index

    return [paper for paper in canonical if paper is not None]


def normalize_paper(paper: Paper) -> Paper:
    authors: list[Author] = []
    seen_authors: set[tuple[str, str | None]] = set()
    for author in paper.authors:
        normalized = Author(
            name=_normalize_space(author.name),
            orcid=_normalize_orcid(author.orcid),
        )
        key = (normalized.name.casefold(), normalized.orcid)
        if key not in seen_authors:
            authors.append(normalized)
            seen_authors.add(key)

    sources = tuple(
        sorted(
            {
                PaperSource(
                    provider=source.provider,
                    identifier=_normalize_source_id(source.provider, source.identifier),
                )
                for source in paper.sources
            },
            key=lambda source: source.provider.value,
        )
    )
    categories = tuple(dict.fromkeys(_normalize_space(value) for value in paper.categories))
    return Paper(
        sources=sources,
        title=_normalize_space(paper.title),
        abstract=_normalize_space(paper.abstract),
        authors=tuple(authors),
        categories=categories,
        doi=_normalize_doi(paper.doi),
        arxiv_id=_normalize_arxiv_id(paper.arxiv_id),
        citation_count=paper.citation_count,
        published_on=paper.published_on,
        updated_on=paper.updated_on,
        venue=_normalize_space(paper.venue) if paper.venue else None,
        landing_page_url=paper.landing_page_url,
        pdf_url=paper.pdf_url,
    )


def canonical_paper_key(paper: Paper) -> str:
    keys = _identity_keys(normalize_paper(paper))
    return keys[0]


def _identity_keys(paper: Paper) -> tuple[str, ...]:
    keys: list[str] = []
    if paper.doi:
        keys.append(f"doi:{paper.doi}")
    if paper.arxiv_id:
        keys.append(f"arxiv:{paper.arxiv_id}")
    title = _title_key(paper.title)
    keys.append(f"title:{title}:{paper.published_on.year}")
    return tuple(keys)


def _merge_papers(left: Paper, right: Paper) -> Paper:
    preferred, alternate = (
        (left, right) if _paper_quality(left) >= _paper_quality(right) else (right, left)
    )
    sources = {source.provider: source for source in alternate.sources}
    sources.update({source.provider: source for source in preferred.sources})
    categories = tuple(dict.fromkeys((*preferred.categories, *alternate.categories)))

    return Paper(
        sources=tuple(sorted(sources.values(), key=lambda source: source.provider.value)),
        title=preferred.title,
        abstract=max((left.abstract, right.abstract), key=len),
        authors=max((left.authors, right.authors), key=len),
        categories=categories,
        doi=preferred.doi or alternate.doi,
        arxiv_id=preferred.arxiv_id or alternate.arxiv_id,
        citation_count=max(left.citation_count, right.citation_count),
        published_on=min(left.published_on, right.published_on),
        updated_on=max(
            (value for value in (left.updated_on, right.updated_on) if value),
            default=None,
        ),
        venue=preferred.venue or alternate.venue,
        landing_page_url=preferred.landing_page_url,
        pdf_url=preferred.pdf_url or alternate.pdf_url,
    )


def _paper_quality(paper: Paper) -> tuple[int, int, int, int]:
    identifiers = int(bool(paper.doi)) + int(bool(paper.arxiv_id))
    links = int(paper.pdf_url is not None) + int(paper.venue is not None)
    return identifiers, links, len(paper.abstract), len(paper.authors)


def _normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi.strip(), flags=re.IGNORECASE).lower()


def _normalize_arxiv_id(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    return re.sub(r"v\d+$", "", arxiv_id.strip().rsplit("/", 1)[-1])


def _normalize_orcid(orcid: str | None) -> str | None:
    return orcid.strip().rsplit("/", 1)[-1] if orcid else None


def _normalize_source_id(provider: PaperProvider, identifier: str) -> str:
    value = identifier.strip().rsplit("/", 1)[-1]
    return re.sub(r"v\d+$", "", value) if provider == PaperProvider.ARXIV else value


def _title_key(title: str) -> str:
    decomposed = unicodedata.normalize("NFKD", title).casefold()
    return re.sub(r"[^a-z0-9]+", "", decomposed)


def _normalize_space(value: str) -> str:
    return " ".join(value.split())
