from uuid import UUID, uuid4

import pytest

from app.domain.evaluation import RankingEvaluationRequest, RankingEvaluationRun, RelevanceJudgment
from app.services.evaluation_service import EvaluationService, SearchNotEvaluableError


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeStore:
    def __init__(self, ranked_ids: list[UUID]) -> None:
        self.ranked_ids = ranked_ids
        self.saved: RankingEvaluationRun | None = None

    async def list_ranked_paper_ids(self, search_id: UUID) -> list[UUID]:
        return self.ranked_ids

    async def save_evaluation(self, evaluation: RankingEvaluationRun) -> None:
        self.saved = evaluation


@pytest.mark.anyio
async def test_evaluation_service_computes_and_persists_ir_metrics() -> None:
    first, second, third = uuid4(), uuid4(), uuid4()
    store = FakeStore([first, second, third])
    request = RankingEvaluationRequest(
        judgments=(
            RelevanceJudgment(paper_id=first, relevance=3),
            RelevanceJudgment(paper_id=third, relevance=1),
        ),
        k=2,
    )

    result = await EvaluationService(store).evaluate(uuid4(), request)

    assert result.metrics.recall == 0.5
    assert result.metrics.reciprocal_rank == 1
    assert result.metrics.ndcg > 0
    assert store.saved == result


@pytest.mark.anyio
async def test_evaluation_service_rejects_unknown_paper_labels() -> None:
    store = FakeStore([uuid4()])
    request = RankingEvaluationRequest(
        judgments=(RelevanceJudgment(paper_id=uuid4(), relevance=1),)
    )

    with pytest.raises(SearchNotEvaluableError, match="outside this search"):
        await EvaluationService(store).evaluate(uuid4(), request)
