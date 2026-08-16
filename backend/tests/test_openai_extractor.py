from datetime import date
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.domain.extraction import (
    EvidenceClaim,
    EvidenceQuote,
    EvidenceSection,
    PaperExtraction,
)
from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.extractors.base import ExtractionProviderError
from app.extractors.openai import PROMPT_VERSION, OpenAIPaperExtractor


class FakeResponses:
    def __init__(self, extraction: PaperExtraction | None) -> None:
        self.extraction = extraction
        self.arguments: dict[str, Any] = {}

    async def parse(self, **kwargs: Any) -> Any:
        self.arguments = kwargs
        return SimpleNamespace(
            id="resp_test_123",
            output_parsed=self.extraction,
            usage=SimpleNamespace(input_tokens=120, output_tokens=80, total_tokens=200),
        )


class FakeClient:
    def __init__(self, extraction: PaperExtraction | None) -> None:
        self.responses = FakeResponses(extraction)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_openai_extractor_requests_structured_output_and_tracks_usage() -> None:
    client = FakeClient(_extraction("We introduce a confidence-aware retrieval policy."))
    extractor = OpenAIPaperExtractor(cast(Any, client), model="gpt-test", max_output_tokens=800)

    result = await extractor.extract(_paper())

    assert result.model == "gpt-test"
    assert result.prompt_version == PROMPT_VERSION
    assert result.provider_response_id == "resp_test_123"
    assert result.usage.total_tokens == 200
    assert result.extraction.keywords == ("retrieval", "routing", "evaluation")
    assert client.responses.arguments["text_format"] is PaperExtraction
    assert client.responses.arguments["store"] is False
    assert '"title": "Adaptive Retrieval"' in client.responses.arguments["input"][1]["content"]


@pytest.mark.anyio
async def test_openai_extractor_rejects_untraceable_quotes() -> None:
    client = FakeClient(_extraction("Accuracy improves by twenty percent."))
    extractor = OpenAIPaperExtractor(cast(Any, client))

    with pytest.raises(ExtractionProviderError, match="unsupported evidence"):
        await extractor.extract(_paper())


@pytest.mark.anyio
async def test_openai_extractor_rejects_missing_parsed_output() -> None:
    extractor = OpenAIPaperExtractor(cast(Any, FakeClient(None)))

    with pytest.raises(ExtractionProviderError, match="no parsed extraction"):
        await extractor.extract(_paper())


def _extraction(quote: str) -> PaperExtraction:
    evidence = EvidenceQuote(quote=quote, section=EvidenceSection.ABSTRACT)
    claim = EvidenceClaim(summary="A supported claim.", evidence=(evidence,))
    return PaperExtraction(
        problem=claim,
        method=claim,
        results=(claim,),
        contributions=(claim,),
        limitations=(),
        keywords=("retrieval", "routing", "evaluation"),
    )


def _paper() -> Paper:
    return Paper(
        sources=(PaperSource(provider=PaperProvider.ARXIV, identifier="2608.00001"),),
        title="Adaptive Retrieval",
        abstract=(
            "We introduce a confidence-aware retrieval policy. "
            "It reduces unnecessary searches while preserving answer quality."
        ),
        authors=(Author(name="Ada Researcher"),),
        published_on=date(2026, 8, 1),
        landing_page_url="https://arxiv.org/abs/2608.00001",
    )
