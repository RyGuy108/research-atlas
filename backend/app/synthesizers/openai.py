import json
from collections.abc import Sequence
from time import perf_counter

from openai import AsyncOpenAI, OpenAIError

from app.domain.landscape import (
    ClusteredLandscape,
    LandscapePaper,
    LandscapeSynthesis,
    LandscapeSynthesisRun,
    SynthesisUsage,
)
from app.services.landscape_validator import (
    LandscapeValidationError,
    validate_landscape_synthesis,
)
from app.synthesizers.base import SynthesisProviderError

PROMPT_VERSION = "landscape-synthesis-v1"
SYSTEM_PROMPT = """You synthesize a research landscape from structured paper notes.
Use only the supplied records. Copy paper UUIDs and numeric cluster IDs exactly.
Name and explain every computed cluster. Identify only relationships and tensions supported by
the notes. Propose concrete open questions grounded in the cited papers, without claiming those
questions came directly from an author. Do not use outside knowledge."""


class OpenAILandscapeSynthesizer:
    def __init__(
        self,
        client: AsyncOpenAI,
        *,
        model: str = "gpt-5-mini",
        max_output_tokens: int = 4_000,
    ) -> None:
        if max_output_tokens < 512:
            raise ValueError("max_output_tokens must be at least 512")
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens

    async def synthesize(
        self,
        papers: Sequence[LandscapePaper],
        clustered: ClusteredLandscape,
    ) -> LandscapeSynthesisRun:
        started_at = perf_counter()
        try:
            response = await self._client.responses.parse(
                model=self._model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _landscape_prompt(papers, clustered)},
                ],
                text_format=LandscapeSynthesis,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except OpenAIError as error:
            raise SynthesisProviderError("OpenAI landscape synthesis request failed") from error

        synthesis = response.output_parsed
        if synthesis is None:
            raise SynthesisProviderError("OpenAI returned no parsed landscape synthesis")
        try:
            validate_landscape_synthesis(clustered, synthesis)
        except LandscapeValidationError as error:
            raise SynthesisProviderError("OpenAI returned invalid landscape references") from error

        usage = response.usage
        return LandscapeSynthesisRun(
            synthesis=synthesis,
            model=self._model,
            prompt_version=PROMPT_VERSION,
            provider_response_id=response.id,
            usage=SynthesisUsage(
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            elapsed_ms=round((perf_counter() - started_at) * 1_000, 2),
        )


def _landscape_prompt(
    papers: Sequence[LandscapePaper],
    clustered: ClusteredLandscape,
) -> str:
    payload = {
        "computed_landscape": clustered.model_dump(mode="json"),
        "papers": [paper.model_dump(mode="json") for paper in papers],
    }
    return json.dumps(payload, ensure_ascii=False)
