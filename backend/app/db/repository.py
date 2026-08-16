from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    PaperExtractionModel,
    PaperModel,
    PaperSourceModel,
    SearchModel,
    SearchResultModel,
)
from app.domain.extraction import ExtractionRun, ExtractionTarget
from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.domain.search import SearchRequest
from app.services.paper_normalizer import canonical_paper_key, normalize_paper


class ResearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_search(self, request: SearchRequest) -> UUID:
        search = SearchModel(
            topic=request.topic,
            filters=request.filters.model_dump(mode="json"),
            strategies=[strategy.value for strategy in request.strategies],
        )
        self._session.add(search)
        await self._session.flush()
        return search.id

    async def upsert_paper(self, raw_paper: Paper) -> PaperModel:
        paper = normalize_paper(raw_paper)
        stored = await self._find_paper(paper)
        if stored is None:
            stored = PaperModel(canonical_key=canonical_paper_key(paper))
            self._session.add(stored)

        _copy_paper_fields(stored, paper)
        existing_sources = {source.provider: source for source in stored.sources}
        for source in paper.sources:
            provider = source.provider.value
            if provider in existing_sources:
                existing_sources[provider].external_id = source.identifier
            else:
                stored.sources.append(
                    PaperSourceModel(provider=provider, external_id=source.identifier)
                )
        await self._session.flush()
        return stored

    async def attach_results(
        self,
        search_id: UUID,
        papers: Sequence[Paper],
        scores: Sequence[float | None] | None = None,
    ) -> None:
        if scores is not None and len(scores) != len(papers):
            raise ValueError("scores must align with papers")

        for index, paper in enumerate(papers):
            stored = await self.upsert_paper(paper)
            score = scores[index] if scores is not None else None
            result = await self._session.get(SearchResultModel, (search_id, stored.id))
            if result is None:
                result = SearchResultModel(search_id=search_id, paper_id=stored.id)
                self._session.add(result)
            result.rank = index + 1
            result.relevance_score = score

        await self._session.flush()

    async def list_search_papers(self, search_id: UUID) -> list[Paper]:
        statement = (
            select(PaperModel)
            .join(SearchResultModel)
            .where(SearchResultModel.search_id == search_id)
            .options(selectinload(PaperModel.sources))
            .order_by(SearchResultModel.rank)
        )
        result = await self._session.scalars(statement)
        return [_to_domain_paper(model) for model in result]

    async def list_extraction_targets(
        self,
        search_id: UUID,
        *,
        limit: int,
    ) -> list[ExtractionTarget]:
        statement = (
            select(PaperModel, SearchResultModel.rank)
            .join(SearchResultModel)
            .where(SearchResultModel.search_id == search_id)
            .options(selectinload(PaperModel.sources))
            .order_by(SearchResultModel.rank)
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            ExtractionTarget(paper_id=paper.id, rank=rank, paper=_to_domain_paper(paper))
            for paper, rank in rows
        ]

    async def save_extraction(
        self,
        search_id: UUID,
        paper_id: UUID,
        run: ExtractionRun,
    ) -> None:
        stored = await self._session.get(PaperExtractionModel, (search_id, paper_id))
        if stored is None:
            stored = PaperExtractionModel(search_id=search_id, paper_id=paper_id)
            self._session.add(stored)

        stored.extraction = run.extraction.model_dump(mode="json")
        stored.model = run.model
        stored.prompt_version = run.prompt_version
        stored.provider_response_id = run.provider_response_id
        stored.input_tokens = run.usage.input_tokens
        stored.output_tokens = run.usage.output_tokens
        stored.total_tokens = run.usage.total_tokens
        stored.elapsed_ms = run.elapsed_ms
        await self._session.flush()

    async def _find_paper(self, paper: Paper) -> PaperModel | None:
        conditions = [PaperModel.canonical_key == canonical_paper_key(paper)]
        if paper.doi:
            conditions.append(PaperModel.doi == paper.doi)
        if paper.arxiv_id:
            conditions.append(PaperModel.arxiv_id == paper.arxiv_id)

        source_pairs = [(source.provider.value, source.identifier) for source in paper.sources]
        source_match: Select[tuple[UUID]] = select(PaperSourceModel.paper_id).where(
            or_(
                *(
                    (PaperSourceModel.provider == provider)
                    & (PaperSourceModel.external_id == identifier)
                    for provider, identifier in source_pairs
                )
            )
        )
        conditions.append(PaperModel.id.in_(source_match))
        statement = (
            select(PaperModel).where(or_(*conditions)).options(selectinload(PaperModel.sources))
        )
        result = await self._session.scalars(statement)
        return result.one_or_none()


def _copy_paper_fields(model: PaperModel, paper: Paper) -> None:
    model.canonical_key = canonical_paper_key(paper)
    model.title = paper.title
    model.abstract = paper.abstract
    model.authors = [author.model_dump(mode="json") for author in paper.authors]
    model.categories = list(paper.categories)
    model.doi = paper.doi
    model.arxiv_id = paper.arxiv_id
    model.citation_count = paper.citation_count
    model.published_on = paper.published_on
    model.updated_on = paper.updated_on
    model.venue = paper.venue
    model.landing_page_url = str(paper.landing_page_url)
    model.pdf_url = str(paper.pdf_url) if paper.pdf_url else None


def _to_domain_paper(model: PaperModel) -> Paper:
    return Paper(
        sources=tuple(
            PaperSource(provider=PaperProvider(source.provider), identifier=source.external_id)
            for source in model.sources
        ),
        title=model.title,
        abstract=model.abstract,
        authors=tuple(Author.model_validate(author) for author in model.authors),
        categories=tuple(model.categories),
        doi=model.doi,
        arxiv_id=model.arxiv_id,
        citation_count=model.citation_count,
        published_on=model.published_on,
        updated_on=model.updated_on,
        venue=model.venue,
        landing_page_url=model.landing_page_url,
        pdf_url=model.pdf_url,
    )
