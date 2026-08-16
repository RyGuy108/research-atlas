from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class PaperProvider(StrEnum):
    ARXIV = "arxiv"
    OPENALEX = "openalex"


class Author(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=200)
    orcid: str | None = None


class PaperSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: PaperProvider
    identifier: str = Field(min_length=1, max_length=100)


class Paper(BaseModel):
    model_config = ConfigDict(frozen=True)

    sources: tuple[PaperSource, ...] = Field(min_length=1)
    title: str = Field(min_length=1, max_length=500)
    abstract: str = Field(min_length=1)
    authors: tuple[Author, ...] = Field(min_length=1)
    categories: tuple[str, ...] = ()
    doi: str | None = None
    arxiv_id: str | None = None
    citation_count: int = Field(default=0, ge=0)
    published_on: date
    updated_on: date | None = None
    venue: str | None = Field(default=None, max_length=200)
    landing_page_url: HttpUrl
    pdf_url: HttpUrl | None = None

    @model_validator(mode="after")
    def require_unique_providers(self) -> Self:
        providers = [source.provider for source in self.sources]
        if len(providers) != len(set(providers)):
            raise ValueError("a paper can only have one identifier per provider")
        return self
