import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from xml.etree import ElementTree

import httpx

from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.domain.search import SearchRequest
from app.providers.base import ProviderResponseError

ATOM = "http://www.w3.org/2005/Atom"
ARXIV = "http://arxiv.org/schemas/atom"
NAMESPACES = {"atom": ATOM, "arxiv": ARXIV}


class ArxivProvider:
    provider = PaperProvider.ARXIV

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        page_size: int = 100,
        page_delay_seconds: float = 3.0,
        max_attempts: int = 3,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if page_size < 1 or page_size > 2_000:
            raise ValueError("page_size must be between 1 and 2000")
        self._client = client
        self._page_size = page_size
        self._page_delay_seconds = page_delay_seconds
        self._max_attempts = max_attempts
        self._sleep = sleep

    async def search(self, request: SearchRequest) -> list[Paper]:
        """Page through arXiv results without exceeding the caller's candidate budget."""
        papers: list[Paper] = []
        while len(papers) < request.filters.max_candidates:
            remaining = request.filters.max_candidates - len(papers)
            batch_size = min(self._page_size, remaining)
            response = await self._request_page(request, start=len(papers), size=batch_size)
            page = parse_arxiv_feed(response.text)
            papers.extend(page)

            if len(page) < batch_size:
                break
            if len(papers) < request.filters.max_candidates:
                await self._sleep(self._page_delay_seconds)

        return papers

    async def _request_page(
        self, request: SearchRequest, *, start: int, size: int
    ) -> httpx.Response:
        params: dict[str, str | int] = {
            "search_query": build_arxiv_query(request),
            "start": start,
            "max_results": size,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        for attempt in range(self._max_attempts):
            try:
                response = await self._client.get("/api/query", params=params)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as error:
                retryable = not isinstance(
                    error, httpx.HTTPStatusError
                ) or error.response.status_code in {429, 500, 502, 503, 504}
                if not retryable or attempt + 1 == self._max_attempts:
                    raise ProviderResponseError("arXiv request failed") from error
                await self._sleep(float(2**attempt))

        raise AssertionError("retry loop exited without returning or raising")


def build_arxiv_query(request: SearchRequest) -> str:
    terms = re.findall(r"[\w-]+", request.topic, flags=re.UNICODE)
    if not terms:
        raise ValueError("topic must contain at least one searchable term")

    parts = [f'all:"{term}"' for term in terms]
    if request.filters.year_from or request.filters.year_to:
        year_from = request.filters.year_from or 1950
        year_to = request.filters.year_to or 2100
        parts.append(f"submittedDate:[{year_from}01010000 TO {year_to}12312359]")
    return " AND ".join(parts)


def parse_arxiv_feed(content: str) -> list[Paper]:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ProviderResponseError("arXiv returned invalid Atom XML") from error

    return [_parse_entry(entry) for entry in root.findall("atom:entry", NAMESPACES)]


def _parse_entry(entry: ElementTree.Element) -> Paper:
    entry_id = _required_text(entry, "atom:id")
    provider_id = re.sub(r"v\d+$", "", entry_id.rsplit("/", 1)[-1])
    links = entry.findall("atom:link", NAMESPACES)
    landing_url = next(
        (link.get("href") for link in links if link.get("rel") == "alternate"), entry_id
    )
    pdf_url = next(
        (
            link.get("href")
            for link in links
            if link.get("title") == "pdf" or link.get("type") == "application/pdf"
        ),
        None,
    )
    authors = tuple(
        Author(name=_required_text(author, "atom:name"))
        for author in entry.findall("atom:author", NAMESPACES)
    )
    categories = tuple(
        category.get("term", "")
        for category in entry.findall("atom:category", NAMESPACES)
        if category.get("term")
    )

    return Paper(
        sources=(PaperSource(provider=PaperProvider.ARXIV, identifier=provider_id),),
        title=_normalize_space(_required_text(entry, "atom:title")),
        abstract=_normalize_space(_required_text(entry, "atom:summary")),
        authors=authors,
        categories=categories,
        doi=_optional_text(entry, "arxiv:doi"),
        arxiv_id=provider_id,
        published_on=_parse_date(_required_text(entry, "atom:published")),
        updated_on=_parse_date(_required_text(entry, "atom:updated")),
        venue=_optional_text(entry, "arxiv:journal_ref"),
        landing_page_url=landing_url,
        pdf_url=pdf_url,
    )


def _required_text(element: ElementTree.Element, path: str) -> str:
    value = element.findtext(path, namespaces=NAMESPACES)
    if value is None or not value.strip():
        raise ProviderResponseError(f"arXiv entry is missing {path}")
    return value.strip()


def _optional_text(element: ElementTree.Element, path: str) -> str | None:
    value = element.findtext(path, namespaces=NAMESPACES)
    return value.strip() if value and value.strip() else None


def _parse_date(value: str) -> date:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError as error:
        raise ProviderResponseError(f"arXiv returned an invalid date: {value}") from error


def _normalize_space(value: str) -> str:
    return " ".join(value.split())
