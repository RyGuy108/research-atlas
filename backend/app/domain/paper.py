from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PaperProvider(StrEnum):
    ARXIV = "arxiv"
    OPENALEX = "openalex"


class Author(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=200)
    orcid: str | None = None


class Paper(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: PaperProvider
    provider_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    abstract: str = Field(min_length=1)
    authors: tuple[Author, ...] = Field(min_length=1)
    categories: tuple[str, ...] = ()
    doi: str | None = None
    published_on: date
    updated_on: date | None = None
    venue: str | None = Field(default=None, max_length=200)
    landing_page_url: HttpUrl
    pdf_url: HttpUrl | None = None
