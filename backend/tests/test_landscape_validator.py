from uuid import uuid4

import pytest

from app.domain.landscape import (
    ClusteredLandscape,
    ClusterNarrative,
    LandscapeSynthesis,
    OpenResearchQuestion,
    PaperPosition,
    RelationshipKind,
    ResearchRelationship,
    ThemeCluster,
)
from app.services.landscape_validator import (
    LandscapeValidationError,
    validate_landscape_synthesis,
)


def test_validator_accepts_known_cluster_and_paper_references() -> None:
    clustered, paper_ids = _clustered()

    validate_landscape_synthesis(clustered, _synthesis(paper_ids))


def test_validator_rejects_unknown_paper_reference() -> None:
    clustered, paper_ids = _clustered()
    synthesis = _synthesis(paper_ids).model_copy(
        update={
            "open_questions": (
                OpenResearchQuestion(
                    question="How should retrieval policies be evaluated?",
                    rationale="Current papers use different evaluation assumptions.",
                    evidence_paper_ids=(uuid4(),),
                ),
            )
        }
    )

    with pytest.raises(LandscapeValidationError, match="unknown paper"):
        validate_landscape_synthesis(clustered, synthesis)


def test_validator_rejects_cluster_citation_from_another_cluster() -> None:
    clustered, paper_ids = _clustered()
    synthesis = _synthesis(paper_ids).model_copy(
        update={
            "clusters": (
                ClusterNarrative(
                    cluster_id=0,
                    name="Retrieval policies",
                    summary="Methods decide when and how a system should retrieve evidence.",
                    evidence_paper_ids=(paper_ids[1],),
                ),
                _synthesis(paper_ids).clusters[1],
            )
        }
    )

    with pytest.raises(LandscapeValidationError, match="outside its cluster"):
        validate_landscape_synthesis(clustered, synthesis)


def _clustered() -> tuple[ClusteredLandscape, tuple[object, object]]:
    first, second = uuid4(), uuid4()
    clustered = ClusteredLandscape(
        clusters=(
            ThemeCluster(cluster_id=0, label="retrieval", paper_ids=(first,)),
            ThemeCluster(cluster_id=1, label="evaluation", paper_ids=(second,)),
        ),
        positions=(
            PaperPosition(paper_id=first, cluster_id=0, membership_score=1, x=-1, y=0),
            PaperPosition(paper_id=second, cluster_id=1, membership_score=1, x=1, y=0),
        ),
        similarity_edges=(),
        silhouette_score=0.5,
    )
    return clustered, (first, second)


def _synthesis(paper_ids: tuple[object, object]) -> LandscapeSynthesis:
    first, second = paper_ids
    return LandscapeSynthesis.model_validate(
        {
            "overview": "The field studies retrieval policies and their evaluation tradeoffs.",
            "clusters": [
                {
                    "cluster_id": 0,
                    "name": "Retrieval policies",
                    "summary": "Methods decide when and how a system should retrieve evidence.",
                    "evidence_paper_ids": [first],
                },
                {
                    "cluster_id": 1,
                    "name": "Evaluation methods",
                    "summary": "Evaluation work measures retrieval quality and efficiency.",
                    "evidence_paper_ids": [second],
                },
            ],
            "relationships": [
                ResearchRelationship(
                    source_paper_id=first,
                    target_paper_id=second,
                    kind=RelationshipKind.EXTENDS,
                    summary="The evaluation paper measures the retrieval policy's behavior.",
                )
            ],
            "tensions": [],
            "open_questions": [
                {
                    "question": "How should retrieval policies be evaluated consistently?",
                    "rationale": "The papers motivate both policy design and evaluation criteria.",
                    "evidence_paper_ids": [first, second],
                }
            ],
        }
    )
