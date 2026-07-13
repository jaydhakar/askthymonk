"""Regression tests for the distress/crisis detector.

Covers the exact miss we found during device testing — a direct Hindi
statement of suicidal intent ("मैं अपनी ज़िंदगी खत्म करना चाहता हूँ") that once
slipped past detection into the RAG path — plus nukta spelling variants,
transliteration, English phrasings, and benign questions that must NOT trip it.
"""

import pytest

from app.safety import crisis_response, is_crisis

# The specific phrase that previously bypassed the crisis path.
REGRESSION_MISS = "मैं अपनी ज़िंदगी खत्म करना चाहता हूँ"

CRISIS_PHRASES = [
    # English
    "I want to end my life",
    "I want to kill myself",
    "there is no reason to live",
    "I feel better off dead",
    # Transliterated Hindi
    "main apni zindagi khatm karna chahta hoon",
    "mujhe mar jaana chahta hai",
    # Devanagari — with and without nukta on ज़ / ख़
    REGRESSION_MISS,
    "मैं अपनी जिंदगी खत्म करना चाहता हूँ",
    "मैं आत्महत्या करना चाहता हूँ",
    "मैं जीना नहीं चाहता",
    "मुझे मर जाना है",
]

BENIGN_PHRASES = [
    "मन को शांत कैसे करें?",
    "जीवन का अर्थ क्या है?",
    "ध्यान कैसे करें?",
    "How do I quiet my mind?",
    "What did Osho say about love?",
    "मृत्यु के बारे में ओशो का क्या कहना है?",  # asks about death as a topic, not intent
]


@pytest.mark.parametrize("phrase", CRISIS_PHRASES)
def test_crisis_phrases_detected(phrase: str) -> None:
    assert is_crisis(phrase) is True, f"should be flagged as crisis: {phrase!r}"


def test_regression_exact_miss() -> None:
    """The precise phrase that once leaked through must be caught."""
    assert is_crisis(REGRESSION_MISS) is True


@pytest.mark.parametrize("phrase", BENIGN_PHRASES)
def test_benign_phrases_not_detected(phrase: str) -> None:
    assert is_crisis(phrase) is False, f"should NOT be flagged as crisis: {phrase!r}"


def test_detection_is_case_insensitive() -> None:
    assert is_crisis("I WANT TO END MY LIFE") is True


def test_crisis_response_language() -> None:
    hi = crisis_response("hi")
    en = crisis_response("en")
    # Hindi response contains the KIRAN helpline; both mention a helpline number.
    assert "1800-599-0019" in hi
    assert "KIRAN" in en
    # Unknown language falls back to English.
    assert crisis_response("xx") == en
