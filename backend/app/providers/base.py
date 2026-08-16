from typing import Protocol

from app.domain.paper import Paper, PaperProvider
from app.domain.search import SearchRequest


class PaperSearchProvider(Protocol):
    provider: PaperProvider

    async def search(self, request: SearchRequest) -> list[Paper]: ...


class ProviderResponseError(RuntimeError):
    """Raised when a metadata provider returns an unusable response."""


class ProviderConfigurationError(RuntimeError):
    """Raised when a provider is missing required local configuration."""

