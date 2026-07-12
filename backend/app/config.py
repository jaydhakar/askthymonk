"""Configuration and small pure helpers.

Everything that varies between environments comes from env vars (loaded from
a local .env via python-dotenv). No secrets or model names are hardcoded.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

# The exact sentence the LLM (or the no-match path) must return when nothing
# relevant was retrieved. Kept as a constant so retrieval, the prompt, and the
# book-citation logic all agree on the same string.
FALLBACK_ANSWER = "I have not spoken on this specific matter in the indexed literature."

# language code -> Pinecone namespace.
#   "hi" -> "" (the index's default namespace, holding the ~90 Hindi books)
#   "en" -> "en" (reserved for future English books; empty today)
NAMESPACE_MAP: dict[str, str] = {"hi": "", "en": "en"}

# language code -> human label the mobile app can render in the toggle.
LANGUAGE_LABELS: dict[str, str] = {"hi": "Hindi", "en": "English"}

DEFAULT_LANGUAGE = "hi"


def _parse_languages(raw: str | None) -> list[str]:
    """Parse SUPPORTED_LANGUAGES. Accepts a JSON array (e.g. ["hi","en"]) or a
    plain comma-separated list (e.g. hi,en). Defaults to ["hi"]."""
    if not raw or not raw.strip():
        return [DEFAULT_LANGUAGE]
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            codes = [str(x).strip() for x in parsed if str(x).strip()]
            return codes or [DEFAULT_LANGUAGE]
    except json.JSONDecodeError:
        pass
    codes = [p.strip() for p in raw.split(",") if p.strip()]
    return codes or [DEFAULT_LANGUAGE]


def _parse_origins(raw: str | None) -> list[str]:
    """CORS origins as a comma-separated list. '*' (default) allows all."""
    if not raw or not raw.strip():
        return ["*"]
    return [p.strip() for p in raw.split(",") if p.strip()]


class Settings:
    def __init__(self) -> None:
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
        self.pinecone_index = os.getenv("PINECONE_INDEX", "")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.chat_model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.supported_languages = _parse_languages(os.getenv("SUPPORTED_LANGUAGES"))
        self.cors_origins = _parse_origins(os.getenv("CORS_ORIGINS", "*"))
        self.rate_limit = os.getenv("RATE_LIMIT", "20/minute")
        self.top_k = int(os.getenv("TOP_K", "3"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def is_supported(language: str) -> bool:
    return language in get_settings().supported_languages


def resolve_namespace(language: str) -> str:
    """Map a language code to its Pinecone namespace, defaulting to the Hindi
    (default) namespace for anything unrecognized."""
    return NAMESPACE_MAP.get(language, NAMESPACE_MAP[DEFAULT_LANGUAGE])


def language_label(code: str) -> str:
    return LANGUAGE_LABELS.get(code, code)
