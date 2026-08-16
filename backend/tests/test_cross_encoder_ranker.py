from collections.abc import Sequence
from datetime import date

import pytest

from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.domain.search import RankingStrategy
from app.rankers.cross_encoder import CrossEncoderRanker


class FakeScorer:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.received_pairs: Sequence[tuple[str, str]] = ()
        self.batch_size = 0

    def predict(self, pairs: Sequence[tuple[str, str]], *, batch_size: int) -> list[float]:
        self.received_pairs = pairs
        self.batch_size = batch_size
        return self.scores


def test_cross_encoder_ranks_model_scores_and_builds_query_pairs() -> None:
    scorer = FakeScorer([0.1, 2.4, -0.2])
    papers = [_paper("first"), _paper("second"), _paper("third")]

    results = CrossEncoderRanker(scorer, batch_size=8).rank("adaptive retrieval", papers, limit=2)

    assert [result.paper.title for result in results] == ["second", "first"]
    assert [result.score for result in results] == [2.4, 0.1]
    assert all(result.strategy == RankingStrategy.CROSS_ENCODER for result in results)
    assert scorer.received_pairs[0] == (
        "adaptive retrieval",
        "first. Abstract for first",
    )
    assert scorer.batch_size == 8


def test_cross_encoder_rejects_misaligned_model_output() -> None:
    with pytest.raises(ValueError, match="different number"):
        CrossEncoderRanker(FakeScorer([])).rank("adaptive retrieval", [_paper("one")])


def _paper(identifier: str) -> Paper:
    return Paper(
        sources=(PaperSource(provider=PaperProvider.ARXIV, identifier=identifier),),
        title=identifier,
        abstract=f"Abstract for {identifier}",
        authors=(Author(name="Ada Researcher"),),
        published_on=date(2026, 8, 1),
        landing_page_url=f"https://example.org/{identifier}",
    )
