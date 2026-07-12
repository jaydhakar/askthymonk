"""Question embedding via OpenAI.

The embedding model MUST match the one used to build the Pinecone index
(text-embedding-3-large, 3072 dims) or similarity search breaks. The model name
is read from EMBEDDING_MODEL so it stays in lockstep with the index config.
"""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from ..config import get_settings


@lru_cache
def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=settings.openai_api_key)


def embed_question(text: str) -> list[float]:
    settings = get_settings()
    response = _client().embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding
