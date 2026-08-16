import pytest

from app.services.ranking_metrics import evaluate_ranking


def test_evaluate_ranking_computes_recall_mrr_and_graded_ndcg() -> None:
    metrics = evaluate_ranking(
        ["irrelevant", "most-relevant", "relevant", "missed"],
        {"most-relevant": 3.0, "relevant": 1.0, "missed": 2.0},
        k=3,
    )

    assert metrics.recall == pytest.approx(2 / 3)
    assert metrics.reciprocal_rank == pytest.approx(0.5)
    assert metrics.ndcg == pytest.approx(0.5234343)


def test_evaluate_ranking_returns_zero_without_positive_labels() -> None:
    metrics = evaluate_ranking(["one"], {"one": 0.0}, k=5)

    assert metrics.recall == 0.0
    assert metrics.reciprocal_rank == 0.0
    assert metrics.ndcg == 0.0


def test_evaluate_ranking_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="positive"):
        evaluate_ranking([], {}, k=0)
    with pytest.raises(ValueError, match="negative"):
        evaluate_ranking(["one"], {"one": -1.0}, k=1)
