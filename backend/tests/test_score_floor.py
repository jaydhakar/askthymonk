"""English-only retrieval-relevance floor (EN_SCORE_FLOOR, default 0.45).

Offline: query_index is mocked to control the top score, generate_answer is a spy
so we can assert it is (or isn't) called. The floor applies to English only;
Hindi (score_floor 0.0) must bypass it entirely.
"""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import fallback_message

client = TestClient(main.app)


def _setup(monkeypatch, score, answer="A grounded reflection."):
    """Stub the pipeline so only the score + language drive routing."""
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    monkeypatch.setattr(main, "is_class_judgment", lambda q: False)
    monkeypatch.setattr(main, "embed_question", lambda text, model: [0.0, 0.1])
    monkeypatch.setattr(
        main, "query_index",
        lambda *a, **k: [{"score": score, "book": "B", "source": "Osho", "text": "t"}],
    )
    calls = {"generate": 0}

    def spy_generate(*a, **k):
        calls["generate"] += 1
        return answer

    monkeypatch.setattr(main, "generate_answer", spy_generate)
    return calls


_ip_counter = [0]


def _ask(question, language):
    # Unique X-Real-Client-IP per call so each request lands in its own rate-limit
    # bucket — otherwise these POSTs share the in-process limiter with the rest of
    # the suite and the tail of a full run would 429. (Also exercises the real
    # client-IP keying path end-to-end.)
    _ip_counter[0] += 1
    return client.post(
        "/api/wisdom",
        json={"question": question, "language": language},
        headers={"X-Real-Client-IP": f"203.0.113.{_ip_counter[0] % 250 + 1}"},
    )


# --- English floor routing --------------------------------------------------

def test_en_below_floor_declines_without_generation(monkeypatch):
    calls = _setup(monkeypatch, score=0.30)
    res = _ask("how do I make profit in stock market", "en")
    body = res.json()
    assert body["answer"] == fallback_message("en")
    assert body["book"] is None and body["source"] is None
    assert calls["generate"] == 0  # floor short-circuits BEFORE the LLM call


def test_en_above_floor_generates(monkeypatch):
    calls = _setup(monkeypatch, score=0.60)
    res = _ask("what is meditation?", "en")
    body = res.json()
    assert body["answer"] == "A grounded reflection."
    assert body["book"] == "B" and body["source"] == "Osho"
    assert calls["generate"] == 1


def test_en_exactly_at_floor_generates(monkeypatch):
    # 0.45 is NOT below 0.45 -> passes the floor and generates.
    calls = _setup(monkeypatch, score=0.45)
    res = _ask("borderline question", "en")
    assert res.json()["answer"] == "A grounded reflection."
    assert calls["generate"] == 1


# --- Hindi bypass -----------------------------------------------------------

@pytest.mark.parametrize("score", [0.05, 0.30, 0.44])
def test_hi_bypasses_floor_regardless_of_score(monkeypatch, score):
    # Hindi has score_floor 0.0 -> even a very low score still generates.
    calls = _setup(monkeypatch, score=score)
    res = _ask("ध्यान क्या है?", "hi")
    body = res.json()
    assert body["answer"] == "A grounded reflection."
    assert body["book"] == "B"
    assert calls["generate"] == 1  # floor never short-circuits Hindi


# --- Post-generation nulling still intact (floor passed, LLM still declines) --

def test_en_above_floor_llm_declines_still_nulls(monkeypatch):
    calls = _setup(monkeypatch, score=0.60, answer="NO_ANSWER")
    res = _ask("what is meditation?", "en")
    body = res.json()
    assert body["answer"] == fallback_message("en")
    assert body["book"] is None and body["source"] is None
    assert calls["generate"] == 1  # reached the LLM, which declined post-hoc


def test_hi_llm_declines_still_nulls(monkeypatch):
    calls = _setup(monkeypatch, score=0.30, answer="NO_ANSWER")
    res = _ask("शेयर बाजार में मुनाफा कैसे कमाएं", "hi")
    body = res.json()
    assert body["answer"] == fallback_message("hi")
    assert body["book"] is None and body["source"] is None
    assert calls["generate"] == 1  # Hindi still relies on the LLM NO_ANSWER gate
