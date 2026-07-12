"""Pydantic request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .config import DEFAULT_LANGUAGE


class WisdomRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's question.")
    # Defaults to "hi" when the client omits it.
    language: str = DEFAULT_LANGUAGE


class WisdomResponse(BaseModel):
    answer: str
    book: str | None = None
    language: str


class LanguageInfo(BaseModel):
    code: str
    label: str


class LanguagesResponse(BaseModel):
    languages: list[LanguageInfo]
