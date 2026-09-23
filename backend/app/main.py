"""Ask Thy Monk — FastAPI backend.

A RAG chat interface over a Pinecone index of ~90 Hindi Osho books. Endpoints:
  GET  /health         — liveness probe
  GET  /api/languages  — languages the client is allowed to offer
  POST /api/wisdom     — ask a question, get a grounded answer + cited book
"""

from __future__ import annotations

import ipaddress
import logging
import os
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import (
    DEFAULT_LANGUAGE,
    fallback_message,
    get_settings,
    is_no_answer,
    is_supported,
    language_label,
    retrieval_target,
)
from .guardrail import blocklist_size, is_blocked
from .metrics import record_turn
from .models import MAX_HISTORY_TURNS, LanguagesResponse, WisdomRequest, WisdomResponse
from .safety import crisis_response, is_crisis
from .services.embeddings import embed_question
from .services.llm import generate_answer, is_class_judgment, is_followup, reformulate_query
from .services.pinecone_client import query_index

logger = logging.getLogger("askthymonk")
# Dedicated diagnostics logger so per-request retrieval/grounding lines are easy
# to filter in Render's log stream (search for "askthymonk.diag").
diag = logging.getLogger("askthymonk.diag")


def _configure_app_logging() -> None:
    """Guarantee our INFO diagnostics reach stdout (hence Render's logs),
    independent of how uvicorn configured root logging. Scoped to the
    'askthymonk' logger tree so uvicorn's own loggers are untouched. Level is
    overridable via LOG_LEVEL (default INFO). Idempotent — safe on reload."""
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    app_logger = logging.getLogger("askthymonk")
    app_logger.setLevel(level)
    if not any(getattr(h, "_atm_handler", False) for h in app_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler._atm_handler = True  # marker so we never attach a duplicate
        app_logger.addHandler(handler)
        # We emit through our own handler; don't also bubble to the root logger.
        app_logger.propagate = False


_configure_app_logging()

settings = get_settings()

# Surface the Layer-1 guardrail state once at import so it's visible in the log
# stream. 0 means the blocklist is missing/empty and only Layer-2 (the prompt)
# is protecting answers.
_blocklist_n = blocklist_size()
(logger.info if _blocklist_n else logger.warning)(
    "guardrail blocklist active terms=%d", _blocklist_n
)

# Per-IP rate limiting.
#
# THE CONTRACT: the website's Cloudflare proxy MUST send the real visitor IP in
# the header below. On the live path (browser -> Cloudflare -> Render) the direct
# socket IP is a single shared infrastructure address, so keying on it collapses
# the limit into one global bucket. We instead key on the forwarded real IP.
#
# ⚠️ HEADER NAME THE WEBSITE PROXY MUST SEND: "X-Real-Client-IP"  (single IP)
CLIENT_IP_HEADER = "X-Real-Client-IP"


def _client_ip_key(request: Request) -> str:
    """Rate-limit bucket key = the real client IP.

    Prefer the IP our trusted Cloudflare proxy forwards in CLIENT_IP_HEADER; fall
    back to the direct socket IP (get_remote_address) when that header is absent
    or malformed — so a missing header degrades to per-socket-IP limiting, NEVER
    to a single shared bucket, and never errors.

    Security note: onrender.com is publicly reachable, so this header CAN be
    spoofed by a direct caller. That is acceptable here: keyless requests are
    rejected (401) before any OpenAI cost, so the residual risk is only cheap
    401-flooding, not cost abuse. The shared-secret gate is unchanged.
    """
    forwarded = request.headers.get(CLIENT_IP_HEADER, "")
    if forwarded:
        # Accept a bare IP, or the first entry of a comma list, and validate it
        # (v4 or v6). Anything malformed falls through to the socket IP.
        candidate = forwarded.split(",")[0].strip()
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip_key, default_limits=[settings.rate_limit])


class UTF8JSONResponse(JSONResponse):
    """Declare charset explicitly so naive clients (e.g. Windows PowerShell 5.1)
    decode Hindi/Devanagari responses correctly. Mobile clients handle UTF-8
    regardless, but this is correct and harmless for everyone."""

    media_type = "application/json; charset=utf-8"


app = FastAPI(
    title="Ask Thy Monk API",
    # 1.3.2: English-only retrieval-relevance floor (EN_SCORE_FLOOR, default 0.45)
    # applied before generation — declines off-topic questions the LLM's NO_ANSWER
    # gate would otherwise confabulate on. Hindi unchanged. (1.3.1: real-client-IP
    # rate limiting. 1.3.0: name/content guardrail.) /health deploy marker.
    version="1.3.2",
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
    return {"status": "ok", "version": app.version}


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

    # Cap conversation history server-side (never trust the client's own limit).
    history = [{"question": h.question, "answer": h.answer} for h in payload.conversation_history]
    history = history[-MAX_HISTORY_TURNS:]

    # Engagement metric (counts only, no text): this request's turn number.
    record_turn(len(history) + 1)

    # Safety first: a distress/crisis question skips RAG and the Osho persona
    # entirely and returns a direct, caring message with resources. Scan the
    # ACCUMULATED conversation (prior user turns + this message), so distress
    # built up gradually across several messages is still caught.
    crisis_scan_text = " ".join([h["question"] for h in history] + [question])
    if is_crisis(crisis_scan_text):
        diag.info("outcome=crisis lang=%s turn=%d", language, len(history) + 1)
        return WisdomResponse(answer=crisis_response(language), book=None, source=None, language=language)

    # Select the embedding model AND the Pinecone account/index as one matched
    # pair for this language — embedding must use the same model the target index
    # was built with, or the query fails with a dimension mismatch.
    target = retrieval_target(language)

    # Follow-up handling (turn 2+ only), in TWO stages:
    #   1) classify whether this turn is a genuine follow-up (continues the prior
    #      topic) or a NEW question (subject change);
    #   2) ONLY if it's a follow-up, rewrite it into a standalone query so e.g.
    #      "what does that mean?" retrieves on its actual topic.
    # A new/unrelated question — and any uncertainty — is used verbatim, so a topic
    # switch never gets the prior topic grafted on. First messages skip this
    # entirely. Only the RETRIEVAL query changes; answer generation still gets the
    # original question + history below. Degrade to the original on any failure.
    retrieval_query = question
    # "skipped" = first turn / no history (inert); "new_question" = classified as a
    # subject change (used as-is); "changed"/"unchanged" = follow-up rewritten;
    # "failed" = the extra calls errored. Logged below, not assumed.
    reformulation = "skipped"
    if history:
        try:
            if is_followup(question, history):
                retrieval_query = reformulate_query(question, history)
                reformulation = "changed" if retrieval_query != question else "unchanged"
            else:
                reformulation = "new_question"
        except Exception:  # noqa: BLE001 — never let the extra calls break the request
            logger.warning("Follow-up classification/reformulation failed; using the original question.")
            retrieval_query = question
            reformulation = "failed"

    # Guardrail (pre-generation): decline questions that ask the app to judge or
    # generalize about a group/class/profession/community OF PEOPLE as a whole
    # (e.g. "what does Osho say about politicians?"). The retrieved passages for
    # such queries are inherently critical of the group, so we never generate
    # from them — we return the ordinary localized decline instead
    # (indistinguishable from a normal "not spoken on this" reply). Checked on the
    # resolved standalone query so a follow-up like "and are they corrupt?" is
    # caught too. Deliberately narrow (biased to answer); degrade to answering on
    # any classifier failure so a transient error never blocks a normal question.
    try:
        if is_class_judgment(retrieval_query):
            diag.info("outcome=decline_class_judgment lang=%s turn=%d", language, len(history) + 1)
            return WisdomResponse(answer=fallback_message(language), book=None, source=None, language=language)
    except Exception:  # noqa: BLE001 — never let the guardrail classifier break a request
        logger.warning("Class-judgment classifier failed; proceeding to answer normally.")

    try:
        # Step 1: embed the (reformulated) retrieval query with the language's model.
        vector = embed_question(retrieval_query, target.embedding_model)
        # Step 2: query that same language's Pinecone account/index (default ns),
        # with that language's top_k.
        matches = query_index(target.pinecone_api_key, target.pinecone_index, vector, target.top_k)
    except RuntimeError as exc:
        # Missing configuration (e.g. an API key or index not set).
        logger.error("Configuration error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface upstream failures as 502
        logger.exception("Upstream retrieval/embedding failure")
        raise HTTPException(status_code=502, detail="Upstream service error during retrieval.") from exc

    # Diagnostics: the config ACTUALLY used this request (top_k/index/model read
    # from the resolved target, not assumed), plus match count and raw scores and
    # reformulation status. No question/answer text is logged (matches metrics.py).
    scores = [round(m.get("score"), 4) for m in matches if m.get("score") is not None]
    diag.info(
        "retrieval lang=%s index=%s top_k=%d embed=%s turn=%d reformulation=%s matches=%d scores=%s",
        language,
        target.pinecone_index,
        target.top_k,
        target.embedding_model,
        len(history) + 1,
        reformulation,
        len(matches),
        scores,
    )

    # Graceful decline when nothing relevant is retrieved (localized, no book).
    if not matches:
        diag.info("outcome=decline_no_matches lang=%s top_k=%d", language, target.top_k)
        return WisdomResponse(answer=fallback_message(language), book=None, source=None, language=language)

    top = matches[0]
    top_score = round(top["score"], 4) if top.get("score") is not None else None

    # Retrieval-relevance floor (English only; target.score_floor is 0.0 for Hindi,
    # making this a no-op there). Applied BEFORE generation: calibration showed the
    # LLM's own NO_ANSWER gate is unreliable in English (it grounded off-topic
    # questions at scores as low as ~0.20), while the top retrieval score cleanly
    # separates legit (>=0.532) from noise/adjacent-leak (<=0.385). Below the floor
    # we decline directly — identical localized decline, book/source nulled — which
    # also skips a wasted LLM call. Hindi (floor 0.0) is untouched by this branch.
    if target.score_floor and (top_score is None or top_score < target.score_floor):
        diag.info(
            "outcome=floor_declined lang=%s top_score=%s floor=%s",
            language, top_score, target.score_floor,
        )
        return WisdomResponse(answer=fallback_message(language), book=None, source=None, language=language)

    try:
        # Step 4: ground an answer in the retrieved passages (with prior turns
        # as conversational context; retrieval above still used only `question`).
        answer = generate_answer(question, matches, language, history=history)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upstream LLM failure")
        raise HTTPException(status_code=502, detail="Upstream service error during generation.") from exc

    # A sentinel answer means the model declined: return the localized decline
    # message and never cite a book (the sentinel is language-independent, so
    # this detection works regardless of the answer language).
    if is_no_answer(answer):
        diag.info(
            "outcome=decline_no_answer lang=%s matches=%d top_score=%s",
            language, len(matches), top_score,
        )
        return WisdomResponse(answer=fallback_message(language), book=None, source=None, language=language)

    # Layer-1 name/content guardrail: if the generated answer contains any
    # blocklisted term, FULLY SUPPRESS it and return the ordinary localized
    # decline — indistinguishable from a normal "not spoken on this" reply. The
    # matched term is intentionally NOT logged (matches our no-text-retention
    # policy); we log only that suppression occurred.
    if is_blocked(answer):
        diag.info("outcome=suppressed_blocklist lang=%s matches=%d", language, len(matches))
        return WisdomResponse(answer=fallback_message(language), book=None, source=None, language=language)

    diag.info(
        "outcome=grounded lang=%s book=%s matches=%d top_score=%s",
        language, top.get("book") or None, len(matches), top_score,
    )
    return WisdomResponse(
        answer=answer,
        book=top.get("book") or None,
        source=top.get("source") or None,
        language=language,
    )
