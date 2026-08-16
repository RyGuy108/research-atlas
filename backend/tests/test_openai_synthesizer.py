from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from app.domain.extraction import (
    EvidenceClaim,
    EvidenceQuote,
    EvidenceSection,
    PaperExtraction,
)
from app.domain.landscape import (
    ClusteredLandscape,
    ClusterNarrative,
    LandscapePaper,
    LandscapeSynthesis,
    OpenResearchQuestion,
    PaperPosition,
    ThemeCluster,
)
from app.synthesizers.base import SynthesisProviderError
from app.synthesizers.openai import PROMPT_VERSION, OpenAILandscapeSynthesizer


class FakeResponses:
    def __init__(self, synthesis: LandscapeSynthesis) -> None:
        self.synthesis = synthesis
        self.arguments: dict[str, Any] = {}

    async def parse(self, **kwargs: Any) -> Any:
        self.arguments = kwargs
        return SimpleNamespace(
            id="resp_landscape_123",
            output_parsed=self.synthesis,
            usage=SimpleNamespace(input_tokens=300, output_tokens=150, total_tokens=450),
        )


class FakeClient:
    def __init__(self, synthesis: LandscapeSynthesis) -> None:
        self.responses = FakeResponses(synthesis)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_openai_synthesizer_requests_validated_structured_landscape() -> None:
    papers, clustered = _inputs()
    client = FakeClient(_synthesis(papers[0].paper_id))
    synthesizer = OpenAILandscapeSynthesizer(cast(Any, client), model="gpt-test")

    run = await synthesizer.synthesize(papers, clustered)

    assert run.model == "gpt-test"
    assert run.prompt_version == PROMPT_VERSION
    assert run.usage.total_tokens == 450
    assert run.synthesis.clusters[0].name == "Adaptive retrieval"
    assert client.responses.arguments["text_format"] is LandscapeSynthesis
    assert client.responses.arguments["store"] is False
    assert str(papers[0].paper_id) in client.responses.arguments["input"][1]["content"]


@pytest.mark.anyio
async def test_openai_synthesizer_rejects_unknown_references() -> None:
    papers, clustered = _inputs()
    client = FakeClient(_synthesis(uuid4()))
    synthesizer = OpenAILandscapeSynthesizer(cast(Any, client))

    with pytest.raises(SynthesisProviderError, match="invalid landscape references"):
        await synthesizer.synthesize(papers, clustered)


def _inputs() -> tuple[list[LandscapePaper], ClusteredLandscape]:
    paper_id = uuid4()
    evidence = EvidenceQuote(quote="Adaptive retrieval", section=EvidenceSection.TITLE)
    claim = EvidenceClaim(summary="A confidence-aware retrieval policy.", evidence=(evidence,))
    paper = LandscapePaper(
        paper_id=paper_id,
        rank=1,
        title="Adaptive retrieval",
        extraction=PaperExtraction(
            problem=claim,
            method=claim,
            results=(claim,),
            contributions=(claim,),
            limitations=(),
            keywords=("retrieval", "routing", "evaluation"),
        ),
    )
    clustered = ClusteredLandscape(
        clusters=(ThemeCluster(cluster_id=0, label="retrieval", paper_ids=(paper_id,)),),
        positions=(
            PaperPosition(paper_id=paper_id, cluster_id=0, membership_score=1, x=0, y=0),
        ),
        similarity_edges=(),
    )
    return [paper], clustered


def _synthesis(paper_id: object) -> LandscapeSynthesis:
    return LandscapeSynthesis.model_validate(
        {
            "overview": "The landscape studies confidence-aware adaptive retrieval policies.",
            "clusters": [
                ClusterNarrative(
                    cluster_id=0,
                    name="Adaptive retrieval",
                    summary="This cluster studies when language models should retrieve evidence.",
                    evidence_paper_ids=(paper_id,),
                ).model_dump()
            ],
            "relationships": [],
            "tensions": [],
            "open_questions": [
                OpenResearchQuestion(
                    question="When should a model avoid an unnecessary retrieval call?",
                    rationale="The policy must balance answer quality against retrieval cost.",
                    evidence_paper_ids=(paper_id,),
                ).model_dump()
            ],
        }
    )
