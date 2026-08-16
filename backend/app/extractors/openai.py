import json
from time import perf_counter

from openai import AsyncOpenAI, OpenAIError

from app.domain.extraction import ExtractionRun, ExtractionUsage, PaperExtraction
from app.domain.paper import Paper
from app.extractors.base import ExtractionProviderError
from app.services.evidence_validator import EvidenceValidationError, validate_extraction_evidence

PROMPT_VERSION = "paper-extraction-v1"
SYSTEM_PROMPT = """You extract evidence-backed research notes from paper metadata.
Use only the supplied title and abstract. Do not add outside knowledge.
Every claim must include one or more short, exact, contiguous quotes from the declared section.
Use an empty limitations list when the metadata states no limitation.
Keep summaries concise and distinguish reported results from proposed contributions."""


class OpenAIPaperExtractor:
    def __init__(
        self,
        client: AsyncOpenAI,
        *,
        model: str = "gpt-5-mini",
        max_output_tokens: int = 2_500,
    ) -> None:
        if max_output_tokens < 256:
            raise ValueError("max_output_tokens must be at least 256")
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens

    async def extract(self, paper: Paper) -> ExtractionRun:
        started_at = perf_counter()
        try:
            response = await self._client.responses.parse(
                model=self._model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _paper_prompt(paper)},
                ],
                text_format=PaperExtraction,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except OpenAIError as error:
            raise ExtractionProviderError("OpenAI extraction request failed") from error

        extraction = response.output_parsed
        if extraction is None:
            raise ExtractionProviderError("OpenAI returned no parsed extraction")
        try:
            validate_extraction_evidence(paper, extraction)
        except EvidenceValidationError as error:
            raise ExtractionProviderError("OpenAI returned unsupported evidence") from error

        usage = response.usage
        return ExtractionRun(
            extraction=extraction,
            model=self._model,
            prompt_version=PROMPT_VERSION,
            provider_response_id=response.id,
            usage=ExtractionUsage(
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            elapsed_ms=round((perf_counter() - started_at) * 1_000, 2),
        )


def _paper_prompt(paper: Paper) -> str:
    payload = {
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": [author.name for author in paper.authors],
        "published_on": paper.published_on.isoformat(),
        "venue": paper.venue,
    }
    return json.dumps(payload, ensure_ascii=False)
