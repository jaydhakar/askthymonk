"""Zen Wisdom Explorer — FastAPI backend.

A RAG chat interface over a Pinecone index of ~90 Hindi Osho books. Endpoints:
  GET  /health         — liveness probe
  GET  /api/languages  — languages the client is allowed to offer
  POST /api/wisdom     — ask a question, get a grounded answer + cited book
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import (
    FALLBACK_ANSWER,
    DEFAULT_LANGUAGE,
    get_settings,
    is_supported,
    language_label,
    resolve_namespace,
)
from .models import LanguagesResponse, WisdomRequest, WisdomResponse
from .safety import crisis_response, is_crisis
from .services.embeddings import embed_question
from .services.llm import generate_answer
from .services.pinecone_client import query_namespace

logger = logging.getLogger("zen_wisdom")

settings = get_settings()

# Per-IP rate limiting.
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])


class UTF8JSONResponse(JSONResponse):
    """Declare charset explicitly so naive clients (e.g. Windows PowerShell 5.1)
    decode Hindi/Devanagari responses correctly. Mobile clients handle UTF-8
    regardless, but this is correct and harmless for everyone."""

    media_type = "application/json; charset=utf-8"


app = FastAPI(
    title="Zen Wisdom Explorer API",
    version="1.0.0",
    default_response_class=UTF8JSONResponse,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down and try again shortly."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/languages", response_model=LanguagesResponse)
def languages() -> LanguagesResponse:
    """The single source of truth for which languages the app may offer.
    Today this reports only what SUPPORTED_LANGUAGES contains (["hi"] by default),
    so the mobile client never hardcodes the toggle options."""
    return LanguagesResponse(
        languages=[{"code": c, "label": language_label(c)} for c in settings.supported_languages]
    )


@app.post("/api/wisdom", response_model=WisdomResponse)
@limiter.limit(settings.rate_limit)
def wisdom(payload: WisdomRequest, request: Request) -> WisdomResponse:
    # Optional shared-secret gate. When API_SHARED_SECRET is configured, callers
    # must present a matching X-API-Key header. Disabled when unset (local dev).
    if settings.api_shared_secret and request.headers.get("x-api-key") != settings.api_shared_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    language = payload.language or DEFAULT_LANGUAGE
    if not is_supported(language):
        # Unknown/unsupported language: fall back to the default rather than error.
        language = DEFAULT_LANGUAGE

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")

    # Safety first: a distress/crisis question skips RAG and the Osho persona
    # entirely and returns a direct, caring message with resources.
    if is_crisis(question):
        return WisdomResponse(answer=crisis_response(language), book=None, language=language)

    namespace = resolve_namespace(language)

    try:
        # Step 1: embed with the same model the index was built with.
        vector = embed_question(question)
        # Step 2: retrieve top_k from the resolved namespace.
        matches = query_namespace(vector, namespace=namespace, top_k=settings.top_k)
    except RuntimeError as exc:
        # Missing configuration (e.g. an API key not set).
        logger.error("Configuration error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface upstream failures as 502
        logger.exception("Upstream retrieval/embedding failure")
        raise HTTPException(status_code=502, detail="Upstream service error during retrieval.") from exc

    # Graceful fallback for an empty namespace (e.g. "en" today) or no matches.
    if not matches:
        return WisdomResponse(answer=FALLBACK_ANSWER, book=None, language=language)

    try:
        # Step 4: ground an answer in the retrieved passages.
        answer = generate_answer(question, matches, language)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upstream LLM failure")
        raise HTTPException(status_code=502, detail="Upstream service error during generation.") from exc

    # Cite the top match's book, unless the model reported nothing relevant.
    book = matches[0].get("book") or None
    if answer.strip() == FALLBACK_ANSWER:
        book = None

    return WisdomResponse(answer=answer, book=book, language=language)
