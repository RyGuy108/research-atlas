from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.domain.pipeline import (
    PIPELINE_STAGES,
    PipelineStage,
    PipelineState,
    PipelineStatus,
    advance_pipeline,
    fail_pipeline,
)
from app.domain.search import RankingStrategy, SearchFilters, SearchRequest


def test_search_request_normalizes_topic() -> None:
    request = SearchRequest(topic="  adaptive   retrieval  ")

    assert request.topic == "adaptive retrieval"
    assert request.strategies == (RankingStrategy.CROSS_ENCODER,)


def test_search_filters_reject_reversed_years() -> None:
    with pytest.raises(ValidationError, match="year_from"):
        SearchFilters(year_from=2026, year_to=2024)


def test_search_request_rejects_duplicate_strategies() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        SearchRequest(
            topic="retrieval evaluation",
            strategies=(RankingStrategy.EMBEDDING, RankingStrategy.EMBEDDING),
        )


def test_paper_requires_at_least_one_author() -> None:
    with pytest.raises(ValidationError):
        Paper(
            sources=(PaperSource(provider=PaperProvider.ARXIV, identifier="2608.00001"),),
            title="A useful paper",
            abstract="A useful abstract.",
            authors=(),
            published_on=date(2026, 8, 1),
            landing_page_url="https://arxiv.org/abs/2608.00001",
        )


def test_paper_is_immutable() -> None:
    paper = Paper(
        sources=(PaperSource(provider=PaperProvider.ARXIV, identifier="2608.00001"),),
        title="A useful paper",
        abstract="A useful abstract.",
        authors=(Author(name="Ada Researcher"),),
        published_on=date(2026, 8, 1),
        landing_page_url="https://arxiv.org/abs/2608.00001",
    )

    with pytest.raises(ValidationError):
        paper.title = "A different title"


def test_pipeline_advances_in_order_until_complete() -> None:
    state = PipelineState()

    for expected_stage in PIPELINE_STAGES[1:]:
        state = advance_pipeline(state)
        assert state.current_stage == expected_stage

    state = advance_pipeline(state)

    assert state.status == PipelineStatus.COMPLETED
    assert state.current_stage is None
    assert state.completed_stages == PIPELINE_STAGES
    assert state.progress_percent == 100


def test_pipeline_failure_preserves_completed_work() -> None:
    state = advance_pipeline(PipelineState())
    failed = fail_pipeline(state, "provider timed out")

    assert failed.status == PipelineStatus.FAILED
    assert failed.current_stage is None
    assert failed.completed_stages == (PipelineStage.DISCOVERY,)
    assert failed.error == "provider timed out"
