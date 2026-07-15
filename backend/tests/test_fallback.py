"""Unit tests for decline-sentinel detection and localized fallback messages."""

from app.config import FALLBACK_ANSWER, fallback_message, is_no_answer


def test_is_no_answer_matches_sentinel_variants():
    for text in ["NO_ANSWER", "no_answer", "NO ANSWER", "No-Answer.", "  NO_ANSWER  ", '"NO_ANSWER"']:
        assert is_no_answer(text), text


def test_is_no_answer_ignores_real_answers():
    for text in ["Meditation is the journey inward.", "", "मन को शांत करें", "There is no simple answer here."]:
        assert not is_no_answer(text), text


def test_fallback_message_is_localized():
    assert fallback_message("en") == FALLBACK_ANSWER
    assert "अनुक्रमित" in fallback_message("hi")  # Hindi decline message
    # Unknown language falls back to English.
    assert fallback_message("xx") == FALLBACK_ANSWER
