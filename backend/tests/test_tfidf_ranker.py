from datetime import date

import pytest

from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.domain.search import RankingStrategy
from app.rankers.tfidf import TfidfRanker


def test_tfidf_ranker_prioritizes_query_overlap() -> None:
    papers = [
        _paper("Vision transformers", "Image classification with attention.", "vision"),
        _paper(
            "Adaptive retrieval for language models",
            "A confidence policy decides when a language model should retrieve.",
            "retrieval",
        ),
        _paper("Database indexes", "Improving relational query plans.", "database"),
    ]

    results = TfidfRanker().rank("adaptive retrieval language models", papers, limit=2)

    assert [result.paper.sources[0].identifier for result in results] == [
        "retrieval",
        "vision",
    ]
    assert [result.rank for result in results] == [1, 2]
    assert results[0].score > results[1].score
    assert all(result.strategy == RankingStrategy.KEYWORD for result in results)


def test_tfidf_ranker_keeps_input_order_when_every_score_is_zero() -> None:
    papers = [
        _paper("Computer vision", "Pixels and patches.", "one"),
        _paper("Database systems", "Transactions and storage.", "two"),
    ]

    results = TfidfRanker().rank("adaptive retrieval", papers)

    assert [result.paper.sources[0].identifier for result in results] == ["one", "two"]
    assert [result.score for result in results] == [0.0, 0.0]


def test_tfidf_ranker_validates_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        TfidfRanker().rank("retrieval", [], limit=0)


def _paper(title: str, abstract: str, identifier: str) -> Paper:
    return Paper(
        sources=(PaperSource(provider=PaperProvider.ARXIV, identifier=identifier),),
        title=title,
        abstract=abstract,
        authors=(Author(name="Ada Researcher"),),
        published_on=date(2026, 8, 1),
        landing_page_url=f"https://example.org/{identifier}",
    )
