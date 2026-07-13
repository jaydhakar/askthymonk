"""Endpoint tests that run fully offline.

The crisis path and the shared-secret gate both short-circuit before any
embedding or Pinecone/OpenAI call, so these tests need no API keys.
"""

from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)

CRISIS_QUESTION = "मैं अपनी ज़िंदगी खत्म करना चाहता हूँ"


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


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
    assert "1800-599-0019" in body["answer"]  # KIRAN helpline present


def test_empty_question_rejected(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    res = client.post("/api/wisdom", json={"question": "   ", "language": "hi"})
    assert res.status_code == 422


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
