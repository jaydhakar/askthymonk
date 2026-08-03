"""Endpoint tests that run fully offline.

The crisis path and the shared-secret gate both short-circuit before any
embedding or Pinecone/OpenAI call, so these tests need no API keys.
"""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import fallback_message

client = TestClient(main.app)

CRISIS_QUESTION = "मैं अपनी ज़िंदगी खत्म करना चाहता हूँ"


def _stub_retrieval(monkeypatch):
    """Bypass real embedding/Pinecone so the decline-handling tests stay offline."""
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    monkeypatch.setattr(main, "embed_question", lambda text, model: [0.0, 0.1])
    monkeypatch.setattr(
        main,
        "query_index",
        lambda api_key, index, vec, k: [{"score": 0.5, "book": "Some Book", "source": "Osho", "text": "..."}],
    )


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["version"] == main.app.version


def test_languages_lists_hindi() -> None:
    res = client.get("/api/languages")
    assert res.status_code == 200
    codes = [lang["code"] for lang in res.json()["languages"]]
    assert "hi" in codes


def test_crisis_question_short_circuits(monkeypatch) -> None:
    # No shared secret configured (local-dev default).
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    res = client.post("/api/wisdom", json={"question": CRISIS_QUESTION, "language": "hi"})
    assert res.status_code == 200
    body = res.json()
    assert body["book"] is None
    assert body["source"] is None
    assert "1800-599-0019" in body["answer"]  # KIRAN helpline present


def test_empty_question_rejected(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    res = client.post("/api/wisdom", json={"question": "   ", "language": "hi"})
    assert res.status_code == 422


def test_crisis_detected_across_conversation_history(monkeypatch) -> None:
    # The newest message is benign; distress appears in an earlier turn. The
    # crisis check must scan the accumulated history + new message together.
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    body = {
        "question": "and how should I spend my evenings?",
        "language": "en",
        "conversation_history": [
            {"question": "lately everything feels heavy", "answer": "I hear you."},
            {"question": "honestly I want to end my life", "answer": "..."},
        ],
    }
    res = client.post("/api/wisdom", json=body)
    assert res.status_code == 200
    body_out = res.json()
    assert body_out["book"] is None
    assert "1800-599-0019" in body_out["answer"]  # routed to crisis resources


def test_followup_is_reformulated_for_retrieval(monkeypatch) -> None:
    # Classified as a follow-up -> retrieval embeds the rewritten standalone query.
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    captured = {}

    def fake_embed(text, model):
        captured["embed_text"] = text
        return [0.0, 0.1]

    monkeypatch.setattr(main, "embed_question", fake_embed)
    monkeypatch.setattr(main, "query_index", lambda *a, **k: [{"score": 0.5, "book": "B", "source": "Osho", "text": "t"}])
    monkeypatch.setattr(main, "is_followup", lambda q, h: True)
    monkeypatch.setattr(main, "reformulate_query", lambda q, h: "STANDALONE REWRITE")
    monkeypatch.setattr(main, "generate_answer", lambda *a, **k: "an answer")

    res = client.post(
        "/api/wisdom",
        json={
            "question": "what does that mean?",
            "language": "en",
            "conversation_history": [{"question": "what is meditation?", "answer": "It is stillness."}],
        },
    )
    assert res.status_code == 200
    assert captured["embed_text"] == "STANDALONE REWRITE"


def test_new_question_with_history_is_not_reformulated(monkeypatch) -> None:
    # Classified as NEW despite prior history -> retrieval uses the ORIGINAL
    # question verbatim; reformulation is never called (no prior topic grafted on).
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    captured = {"reformulated": False}

    def fake_embed(text, model):
        captured["embed_text"] = text
        return [0.0, 0.1]

    def spy_reformulate(q, h):
        captured["reformulated"] = True
        return "SHOULD NOT BE USED"

    monkeypatch.setattr(main, "embed_question", fake_embed)
    monkeypatch.setattr(main, "query_index", lambda *a, **k: [{"score": 0.5, "book": "B", "source": "Osho", "text": "t"}])
    monkeypatch.setattr(main, "is_followup", lambda q, h: False)
    monkeypatch.setattr(main, "reformulate_query", spy_reformulate)
    monkeypatch.setattr(main, "generate_answer", lambda *a, **k: "an answer")

    res = client.post(
        "/api/wisdom",
        json={
            "question": "what is meditation?",
            "language": "en",
            "conversation_history": [{"question": "what does osho say about money?", "answer": "..."}],
        },
    )
    assert res.status_code == 200
    assert captured["reformulated"] is False
    assert captured["embed_text"] == "what is meditation?"


def test_no_reformulation_on_first_message(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    captured = {"reformulated": False}

    def fake_embed(text, model):
        captured["embed_text"] = text
        return [0.0, 0.1]

    def spy_reformulate(q, h):
        captured["reformulated"] = True
        return "SHOULD NOT BE USED"

    monkeypatch.setattr(main, "embed_question", fake_embed)
    monkeypatch.setattr(main, "query_index", lambda *a, **k: [{"score": 0.5, "book": "B", "text": "t"}])
    monkeypatch.setattr(main, "reformulate_query", spy_reformulate)
    monkeypatch.setattr(main, "generate_answer", lambda *a, **k: "an answer")

    res = client.post("/api/wisdom", json={"question": "what is meditation?", "language": "en"})
    assert res.status_code == 200
    # First message: no reformulation call, retrieval used the original question.
    assert captured["reformulated"] is False
    assert captured["embed_text"] == "what is meditation?"


@pytest.mark.parametrize("language", ["hi", "en"])
def test_sentinel_maps_to_localized_fallback_and_nulls_book(monkeypatch, language) -> None:
    # The model "declines" by emitting the sentinel; even a translated/decorated
    # form must map to the localized fallback and null the book.
    _stub_retrieval(monkeypatch)
    monkeypatch.setattr(main, "generate_answer", lambda *a, **k: "NO_ANSWER")
    res = client.post("/api/wisdom", json={"question": "something off-topic", "language": language})
    assert res.status_code == 200
    body = res.json()
    assert body["book"] is None
    assert body["source"] is None  # decline nulls source too
    assert body["answer"] == fallback_message(language)


def test_real_answer_keeps_its_book_and_source(monkeypatch) -> None:
    _stub_retrieval(monkeypatch)
    monkeypatch.setattr(main, "generate_answer", lambda *a, **k: "A real grounded reflection.")
    res = client.post("/api/wisdom", json={"question": "what is meditation?", "language": "en"})
    body = res.json()
    assert body["answer"] == "A real grounded reflection."
    assert body["book"] == "Some Book"
    assert body["source"] == "Osho"


def test_secret_gate_rejects_without_header(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "api_shared_secret", "s3cret")
    res = client.post("/api/wisdom", json={"question": CRISIS_QUESTION, "language": "hi"})
    assert res.status_code == 401


def test_secret_gate_allows_with_correct_header(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "api_shared_secret", "s3cret")
    # Correct key + a crisis question: passes the gate, then short-circuits
    # on the crisis path (still no RAG call needed).
    res = client.post(
        "/api/wisdom",
        json={"question": CRISIS_QUESTION, "language": "hi"},
        headers={"X-API-Key": "s3cret"},
    )
    assert res.status_code == 200
    assert res.json()["book"] is None
