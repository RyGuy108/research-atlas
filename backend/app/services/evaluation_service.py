from typing import Protocol
from uuid import UUID

from app.domain.evaluation import RankingEvaluationRequest, RankingEvaluationRun
from app.services.ranking_metrics import evaluate_ranking


class EvaluationStore(Protocol):
    async def list_ranked_paper_ids(self, search_id: UUID) -> list[UUID]: ...

    async def save_evaluation(self, evaluation: RankingEvaluationRun) -> None: ...


class SearchNotEvaluableError(LookupError):
    """Raised when a search or one of its labeled papers cannot be evaluated."""


class EvaluationService:
    def __init__(self, store: EvaluationStore) -> None:
        self._store = store

    async def evaluate(
        self,
        search_id: UUID,
        request: RankingEvaluationRequest,
    ) -> RankingEvaluationRun:
        ranked_ids = await self._store.list_ranked_paper_ids(search_id)
        if not ranked_ids:
            raise SearchNotEvaluableError("search has no ranked papers to evaluate")

        known_ids = set(ranked_ids)
        unknown_ids = {
            judgment.paper_id
            for judgment in request.judgments
            if judgment.paper_id not in known_ids
        }
        if unknown_ids:
            raise SearchNotEvaluableError("judgments include papers outside this search")

        relevance = {judgment.paper_id: judgment.relevance for judgment in request.judgments}
        evaluation = RankingEvaluationRun(
            search_id=search_id,
            judgments=request.judgments,
            metrics=evaluate_ranking(ranked_ids, relevance, k=request.k),
        )
        await self._store.save_evaluation(evaluation)
        return evaluation
