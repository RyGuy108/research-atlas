import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import date

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.paper import Author, Paper, PaperProvider
from app.domain.search import SearchRequest
from app.providers.base import ProviderConfigurationError, ProviderResponseError


class _AuthorDetails(BaseModel):
    display_name: str
    orcid: str | None = None


class _Authorship(BaseModel):
    author: _AuthorDetails


class _Source(BaseModel):
    id: str
    display_name: str


class _Location(BaseModel):
    landing_page_url: str | None = None
    pdf_url: str | None = None
    source: _Source | None = None


class _Topic(BaseModel):
    display_name: str


class _ExternalIds(BaseModel):
    arxiv: str | None = None


class _Work(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    doi: str | None = None
    title: str
    publication_date: date
    abstract_inverted_index: dict[str, list[int]] | None = None
    authorships: list[_Authorship]
    primary_location: _Location | None = None
    topics: list[_Topic] = Field(default_factory=list)
    ids: _ExternalIds = Field(default_factory=_ExternalIds)
    cited_by_count: int = 0


class _PageMeta(BaseModel):
    next_cursor: str | None = None


class _WorkPage(BaseModel):
    results: list[_Work]
    meta: _PageMeta


class _SourcePage(BaseModel):
    results: list[_Source]


class OpenAlexProvider:
    provider = PaperProvider.OPENALEX

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str | None,
        page_size: int = 100,
        max_attempts: int = 3,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not api_key:
            raise ProviderConfigurationError(
                "OpenAlex requires OPENALEX_API_KEY; create a free key at openalex.org/settings/api"
            )
        if page_size < 1 or page_size > 200:
            raise ValueError("page_size must be between 1 and 200")
        self._client = client
        self._api_key = api_key
        self._page_size = page_size
        self._max_attempts = max_attempts
        self._sleep = sleep

    async def search(self, request: SearchRequest) -> list[Paper]:
        source_ids = await self._resolve_source_ids(request.filters.venues)
        if request.filters.venues and not source_ids:
            return []

        filters = ["has_abstract:true"]
        if request.filters.year_from:
            filters.append(f"from_publication_date:{request.filters.year_from}-01-01")
        if request.filters.year_to:
            filters.append(f"to_publication_date:{request.filters.year_to}-12-31")
        if source_ids:
            filters.append(f"primary_location.source.id:{'|'.join(source_ids)}")

        papers: list[Paper] = []
        cursor: str | None = "*"
        while len(papers) < request.filters.max_candidates and cursor:
            size = min(self._page_size, request.filters.max_candidates - len(papers))
            payload = await self._get_json(
                "/works",
                params={
                    "search": request.topic,
                    "filter": ",".join(filters),
                    "per-page": size,
                    "cursor": cursor,
                },
            )
            page = _validate_payload(_WorkPage, payload, "works")
            papers.extend(_to_paper(work) for work in page.results)
            cursor = page.meta.next_cursor
            if len(page.results) < size:
                break

        return papers

    async def _resolve_source_ids(self, venues: frozenset[str]) -> tuple[str, ...]:
        source_ids: list[str] = []
        for venue in sorted(venues):
            payload = await self._get_json(
                "/sources", params={"search": venue, "per-page": 5}
            )
            page = _validate_payload(_SourcePage, payload, "sources")
            target = _normalized_name(venue)
            match = next(
                (
                    source
                    for source in page.results
                    if _normalized_name(source.display_name) == target
                ),
                page.results[0] if page.results else None,
            )
            if match:
                source_ids.append(match.id.rsplit("/", 1)[-1])
        return tuple(source_ids)

    async def _get_json(
        self, path: str, *, params: dict[str, str | int]
    ) -> object:
        request_params = {**params, "api_key": self._api_key}
        for attempt in range(self._max_attempts):
            try:
                response = await self._client.get(path, params=request_params)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as error:
                retryable = (
                    not isinstance(error, httpx.HTTPStatusError)
                    or error.response.status_code in {429, 500, 502, 503, 504}
                )
                if not retryable or attempt + 1 == self._max_attempts:
                    raise ProviderResponseError("OpenAlex request failed") from error
                await self._sleep(float(2**attempt))
            except ValueError as error:
                raise ProviderResponseError("OpenAlex returned invalid JSON") from error

        raise AssertionError("retry loop exited without returning or raising")


def _to_paper(work: _Work) -> Paper:
    location = work.primary_location or _Location()
    abstract = _restore_abstract(work.abstract_inverted_index)
    if not abstract:
        raise ProviderResponseError(f"OpenAlex work {work.id} has no abstract")
    if not work.authorships:
        raise ProviderResponseError(f"OpenAlex work {work.id} has no authors")

    return Paper(
        provider=PaperProvider.OPENALEX,
        provider_id=work.id.rsplit("/", 1)[-1],
        title=" ".join(work.title.split()),
        abstract=abstract,
        authors=tuple(
            Author(name=item.author.display_name, orcid=_normalize_orcid(item.author.orcid))
            for item in work.authorships
        ),
        categories=tuple(topic.display_name for topic in work.topics),
        doi=_normalize_doi(work.doi),
        arxiv_id=_normalize_arxiv_id(work.ids.arxiv),
        citation_count=work.cited_by_count,
        published_on=work.publication_date,
        venue=location.source.display_name if location.source else None,
        landing_page_url=location.landing_page_url or work.id,
        pdf_url=location.pdf_url,
    )


def _restore_abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    final_position = max(position for positions in index.values() for position in positions)
    words = [""] * (final_position + 1)
    for word, positions in index.items():
        for position in positions:
            words[position] = word
    return " ".join(word for word in words if word)


def _normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE).lower()


def _normalize_arxiv_id(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    return re.sub(r"v\d+$", "", arxiv_id.rsplit("/", 1)[-1])


def _normalize_orcid(orcid: str | None) -> str | None:
    return orcid.rsplit("/", 1)[-1] if orcid else None


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _validate_payload[ModelT: BaseModel](
    model: type[ModelT], payload: object, resource: str
) -> ModelT:
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        raise ProviderResponseError(f"OpenAlex returned invalid {resource} data") from error
