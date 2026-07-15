"""Configuration and small pure helpers.

Everything that varies between environments comes from env vars (loaded from
a local .env via python-dotenv). No secrets or model names are hardcoded.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

# The English decline message. Also the default for unknown languages.
FALLBACK_ANSWER = "I have not spoken on this specific matter in the indexed literature."

# When the model cannot ground an answer it emits this fixed, language-independent
# sentinel — NOT the fallback sentence itself, which it would otherwise translate
# into the answer's language and defeat exact-match detection.
NO_ANSWER_SENTINEL = "NO_ANSWER"

# Localized decline messages, shown when retrieval finds nothing usable or the
# model emits the sentinel. Add a language's entry when it ships.
FALLBACK_MESSAGES: dict[str, str] = {
    "en": FALLBACK_ANSWER,
    "hi": "मैंने अनुक्रमित साहित्य में इस विशेष विषय पर कुछ नहीं कहा है।",
}

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

        # --- Hindi retrieval (original Pinecone account) ---
        # Default namespace of PINECONE_INDEX; questions embedded with
        # EMBEDDING_MODEL (text-embedding-3-large, 3072-dim).
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
        self.pinecone_index = os.getenv("PINECONE_INDEX", "")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

        # --- English retrieval (SEPARATE Pinecone account/index) ---
        # English lives in its own Pinecone account (second free tier), so it has
        # its own API key + index and its own, different embedding model
        # (text-embedding-3-small, 1536-dim). The model MUST match how that index
        # was ingested or the query fails with a dimension mismatch.
        self.pinecone_api_key_en = os.getenv("PINECONE_API_KEY_EN", "")
        self.pinecone_index_en = os.getenv("PINECONE_INDEX_EN", "")
        self.embedding_model_en = os.getenv("EMBEDDING_MODEL_EN", "text-embedding-3-small")

        self.chat_model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.supported_languages = _parse_languages(os.getenv("SUPPORTED_LANGUAGES"))
        self.cors_origins = _parse_origins(os.getenv("CORS_ORIGINS", "*"))
        self.rate_limit = os.getenv("RATE_LIMIT", "20/minute")
        # Chunks retrieved per query, per language. English uses a higher default
        # because text-embedding-3-small returns lower-scoring, more diffuse
        # passages — at top_k=3 the grounded answer is often present but too
        # diluted for the model to ground on; 6 reliably gives enough signal.
        self.top_k = int(os.getenv("TOP_K", "3"))
        self.top_k_en = int(os.getenv("TOP_K_EN", "6"))
        # Optional shared secret. When set, /api/wisdom requires a matching
        # X-API-Key header. Empty (default) disables the check for local dev.
        self.api_shared_secret = os.getenv("API_SHARED_SECRET", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def is_supported(language: str) -> bool:
    return language in get_settings().supported_languages


@dataclass(frozen=True)
class RetrievalTarget:
    """A matched embedding-model + Pinecone-account/index pair for one language.

    Hindi and English are embedded with DIFFERENT models (different dimensions)
    and stored in DIFFERENT Pinecone accounts. Bundling them here means a query
    can only ever use a model and index that belong together — mixing them (e.g.
    a 1536-dim English embedding against the 3072-dim Hindi index) is the exact
    failure that produces a dimension-mismatch error.
    """

    language: str
    embedding_model: str
    pinecone_api_key: str
    pinecone_index: str
    top_k: int


def retrieval_target(language: str) -> RetrievalTarget:
    """Resolve the correct (embedding model, Pinecone account, index, top_k) for
    a language. Anything other than "en" uses the Hindi/default target."""
    settings = get_settings()
    if language == "en":
        return RetrievalTarget(
            language="en",
            embedding_model=settings.embedding_model_en,
            pinecone_api_key=settings.pinecone_api_key_en,
            pinecone_index=settings.pinecone_index_en,
            top_k=settings.top_k_en,
        )
    return RetrievalTarget(
        language=DEFAULT_LANGUAGE,
        embedding_model=settings.embedding_model,
        pinecone_api_key=settings.pinecone_api_key,
        pinecone_index=settings.pinecone_index,
        top_k=settings.top_k,
    )


def language_label(code: str) -> str:
    return LANGUAGE_LABELS.get(code, code)


def fallback_message(language: str) -> str:
    """The decline message in the given language (English if unknown)."""
    return FALLBACK_MESSAGES.get(language, FALLBACK_ANSWER)


def is_no_answer(text: str) -> bool:
    """True if the model's answer is the decline sentinel (robust to case,
    punctuation, and spacing, e.g. "NO_ANSWER", "no answer.", "No-Answer")."""
    return "NOANSWER" in re.sub(r"[^A-Za-z]", "", text).upper()
