"""Pinecone retrieval.

Read-only from this app's perspective: we only ever query. We never upsert,
delete, or re-run ingestion.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pinecone import Pinecone

from ..config import get_settings


@lru_cache
def _index():
    settings = get_settings()
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is not set")
    if not settings.pinecone_index:
        raise RuntimeError("PINECONE_INDEX is not set")
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index)


def query_namespace(vector: list[float], namespace: str, top_k: int) -> list[dict[str, Any]]:
    """Query one namespace and return matches as plain dicts:
    [{"score": float, "book": str, "text": str}, ...] sorted by relevance.
    Returns [] when the namespace has no matches (e.g. the empty "en" namespace).
    """
    response = _index().query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
    )
    # The Pinecone response supports both dict-style and attribute access
    # depending on SDK version; normalize defensively.
    raw_matches = response.get("matches", []) if hasattr(response, "get") else getattr(response, "matches", [])
    matches: list[dict[str, Any]] = []
    for m in raw_matches or []:
        metadata = m.get("metadata", {}) if hasattr(m, "get") else getattr(m, "metadata", {}) or {}
        score = m.get("score") if hasattr(m, "get") else getattr(m, "score", None)
        matches.append(
            {
                "score": score,
                "book": (metadata or {}).get("book", "") or "",
                "text": (metadata or {}).get("text", "") or "",
            }
        )
    return matches
