"""Pinecone retrieval.

Read-only from this app's perspective: we only ever query. We never upsert,
delete, or re-run ingestion.

Hindi and English live in SEPARATE Pinecone accounts (different API keys,
different indexes), so we keep one cached client/index per (api_key, index_name)
pair and query the DEFAULT namespace of each — there is no namespace switching
anymore. The caller passes the account/index from the language's RetrievalTarget.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from pinecone import Pinecone

logger = logging.getLogger("askthymonk.pinecone")


@lru_cache(maxsize=8)
def _index_for(api_key: str, index_name: str):
    if not api_key:
        raise RuntimeError(f"Pinecone API key is not set (index='{index_name or '?'}')")
    if not index_name:
        raise RuntimeError("Pinecone index name is not set")
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    # Validate connectivity ONCE per (api_key, index_name) per instance. This
    # both (a) surfaces a bad init immediately in the logs — including the actual
    # dimension and vector count this instance sees, which is the smoking gun if
    # a cold start ever comes up pointed at an empty/wrong index — and (b) because
    # lru_cache never memoizes a call that raises, a failed validation is NOT
    # cached: the next request re-initializes fresh instead of a degraded client
    # persisting for the whole instance lifetime. No retrieval behavior changes;
    # a genuinely unreachable index now fails loudly at init rather than silently.
    try:
        stats = index.describe_index_stats()
        dimension = stats.get("dimension") if hasattr(stats, "get") else getattr(stats, "dimension", None)
        total = (
            stats.get("total_vector_count") if hasattr(stats, "get") else getattr(stats, "total_vector_count", None)
        )
        logger.info(
            "pinecone init OK index=%s dimension=%s total_vectors=%s", index_name, dimension, total
        )
    except Exception as exc:  # noqa: BLE001 — surface + refuse to cache a broken client
        logger.error("pinecone init FAILED index=%s error=%r", index_name, exc)
        raise RuntimeError(f"Pinecone index '{index_name}' failed connectivity validation: {exc}") from exc

    return index


def query_index(api_key: str, index_name: str, vector: list[float], top_k: int) -> list[dict[str, Any]]:
    """Query the default namespace of one account's index and return matches as
    plain dicts: [{"score": float, "book": str, "text": str}, ...] by relevance.
    Returns [] when there are no matches.
    """
    response = _index_for(api_key, index_name).query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
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
                "source": (metadata or {}).get("source", "") or "",
                "text": (metadata or {}).get("text", "") or "",
            }
        )
    return matches
