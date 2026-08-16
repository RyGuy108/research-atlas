from uuid import uuid4

from app.domain.extraction import (
    EvidenceClaim,
    EvidenceQuote,
    EvidenceSection,
    PaperExtraction,
)
from app.domain.landscape import LandscapePaper
from app.services.landscape_clusterer import LandscapeClusterer


def test_clusterer_separates_topics_and_builds_graph_coordinates() -> None:
    papers = [
        _paper(1, "Adaptive retrieval", "retrieval routing confidence uncertainty"),
        _paper(2, "Query routing", "retrieval routing search confidence"),
        _paper(3, "RAG evaluation", "retrieval evaluation relevance search"),
        _paper(4, "Vision transformers", "vision images patches attention"),
        _paper(5, "Image segmentation", "vision images pixels segmentation"),
        _paper(6, "Visual recognition", "vision images classification patches"),
    ]

    landscape = LandscapeClusterer(similarity_threshold=0.1).cluster(papers)

    cluster_by_paper = {item.paper_id: item.cluster_id for item in landscape.positions}
    assert cluster_by_paper[papers[0].paper_id] == cluster_by_paper[papers[1].paper_id]
    assert cluster_by_paper[papers[3].paper_id] == cluster_by_paper[papers[4].paper_id]
    assert cluster_by_paper[papers[0].paper_id] != cluster_by_paper[papers[3].paper_id]
    assert len(landscape.clusters) == 2
    assert landscape.silhouette_score is not None
    assert all(-1 <= item.x <= 1 and -1 <= item.y <= 1 for item in landscape.positions)
    assert landscape.similarity_edges


def test_clusterer_is_deterministic() -> None:
    papers = [
        _paper(1, "Retrieval one", "retrieval search routing"),
        _paper(2, "Retrieval two", "retrieval query search"),
        _paper(3, "Vision one", "vision image pixels"),
        _paper(4, "Vision two", "vision image patches"),
    ]
    clusterer = LandscapeClusterer()

    assert clusterer.cluster(papers) == clusterer.cluster(papers)


def test_clusterer_handles_a_single_paper() -> None:
    paper = _paper(1, "Only paper", "retrieval routing evaluation")

    landscape = LandscapeClusterer().cluster([paper])

    assert len(landscape.clusters) == 1
    assert landscape.positions[0].x == 0
    assert landscape.positions[0].y == 0
    assert landscape.silhouette_score is None


def _paper(rank: int, title: str, keywords: str) -> LandscapePaper:
    quote = EvidenceQuote(quote=title, section=EvidenceSection.TITLE)
    claim = EvidenceClaim(summary=keywords, evidence=(quote,))
    return LandscapePaper(
        paper_id=uuid4(),
        rank=rank,
        title=title,
        extraction=PaperExtraction(
            problem=claim,
            method=claim,
            results=(claim,),
            contributions=(claim,),
            limitations=(),
            keywords=tuple(keywords.split()[:4]),
        ),
    )
