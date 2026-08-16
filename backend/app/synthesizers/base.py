from collections.abc import Sequence
from typing import Protocol

from app.domain.landscape import ClusteredLandscape, LandscapePaper, LandscapeSynthesisRun


class LandscapeSynthesizer(Protocol):
    async def synthesize(
        self,
        papers: Sequence[LandscapePaper],
        clustered: ClusteredLandscape,
    ) -> LandscapeSynthesisRun: ...


class SynthesisProviderError(RuntimeError):
    """Raised when a synthesis provider does not return a usable research landscape."""
