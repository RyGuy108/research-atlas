import math
from collections.abc import Hashable, Mapping, Sequence, Set

from pydantic import BaseModel, ConfigDict, Field


class RankingMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    k: int = Field(ge=1)
    recall: float = Field(ge=0, le=1)
    reciprocal_rank: float = Field(ge=0, le=1)
    ndcg: float = Field(ge=0, le=1)


def evaluate_ranking[ItemT: Hashable](
    ranked_items: Sequence[ItemT],
    relevance: Mapping[ItemT, float],
    *,
    k: int,
) -> RankingMetrics:
    """Compute common information-retrieval metrics from graded relevance labels."""
    if k < 1:
        raise ValueError("k must be positive")
    if any(score < 0 for score in relevance.values()):
        raise ValueError("relevance scores cannot be negative")

    relevant = {item for item, score in relevance.items() if score > 0}
    return RankingMetrics(
        k=k,
        recall=_recall_at_k(ranked_items, relevant, k),
        reciprocal_rank=_reciprocal_rank_at_k(ranked_items, relevant, k),
        ndcg=_ndcg_at_k(ranked_items, relevance, k),
    )


def _recall_at_k[ItemT](ranked: Sequence[ItemT], relevant: Set[ItemT], k: int) -> float:
    if not relevant:
        return 0.0
    retrieved = set(ranked[:k])
    return len(retrieved & relevant) / len(relevant)


def _reciprocal_rank_at_k[ItemT](
    ranked: Sequence[ItemT], relevant: Set[ItemT], k: int
) -> float:
    for index, item in enumerate(ranked[:k], start=1):
        if item in relevant:
            return 1 / index
    return 0.0


def _ndcg_at_k[ItemT: Hashable](
    ranked: Sequence[ItemT], relevance: Mapping[ItemT, float], k: int
) -> float:
    gains = [relevance.get(item, 0.0) for item in ranked[:k]]
    ideal = sorted(relevance.values(), reverse=True)[:k]
    ideal_dcg = _discounted_cumulative_gain(ideal)
    return _discounted_cumulative_gain(gains) / ideal_dcg if ideal_dcg else 0.0


def _discounted_cumulative_gain(gains: Sequence[float]) -> float:
    return sum((2**gain - 1) / math.log2(index + 1) for index, gain in enumerate(gains, start=1))
