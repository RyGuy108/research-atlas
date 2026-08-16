from typing import Protocol

from app.domain.extraction import ExtractionRun
from app.domain.paper import Paper


class PaperExtractor(Protocol):
    async def extract(self, paper: Paper) -> ExtractionRun: ...


class ExtractionProviderError(RuntimeError):
    """Raised when an extraction provider does not return a usable structured result."""
