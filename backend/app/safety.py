"""Distress / crisis detection.

A deliberately small keyword list. When a question matches, we skip RAG and the
Osho persona entirely and return a direct, caring message with crisis resources.
This is a safety net, not a diagnostic tool.
"""

from __future__ import annotations

import re
import unicodedata

# English (incl. common transliterated Hindi) and Devanagari markers of
# self-harm / suicidal ideation / acute despair. Matching is case-insensitive
# and nukta-insensitive (see _normalize), so a keyword written one way also
# catches its nukta variants (e.g. ज़िंदगी vs जिंदगी).
CRISIS_KEYWORDS: list[str] = [
    # English
    "suicide",
    "suicidal",
    "kill myself",
    "killing myself",
    "kill me",
    "end my life",
    "ending my life",
    "end it all",
    "want to die",
    "wanna die",
    "want to end it",
    "take my life",
    "self harm",
    "self-harm",
    "hurt myself",
    "hurting myself",
    "cut myself",
    "no reason to live",
    "don't want to live",
    "dont want to live",
    "better off dead",
    "overdose",
    # Transliterated Hindi
    "aatmahatya",
    "atmahatya",
    "khudkushi",
    "marna chahta",
    "marna chahti",
    "mar jaunga",
    "mar jaana chahta",
    "mujhe marna",
    "mujhe mar jana",
    "jeena nahi chahta",
    "jeena nahi chahti",
    "zindagi khatm",
    "jindagi khatam",
    "jaan dena",
    "jaan de dunga",
    # Devanagari (write the nukta form; _normalize collapses both spellings)
    "आत्महत्या",
    "खुदकुशी",
    "मरना चाहता",
    "मरना चाहती",
    "मर जाना चाहता",
    "मर जाऊं",
    "मर जाऊँ",
    "मुझे मरना",  # first-person "I ... die" (avoids impersonal "सबको मरना है")
    "मुझे मर जा",
    "मुझे नहीं जीना",
    "मुझे जीना नहीं",
    "जीना नहीं चाहता",
    "जीना नहीं चाहती",
    "जीना नहीं चाहत",  # catches चाहता/चाहती/चाहते variants
    "ज़िंदगी खत्म",
    "ज़िंदगी समाप्त",
    "जीवन खत्म",
    "जीवन समाप्त",
    "खुद को खत्म",
    "खुद को मार",
    "अपने आप को खत्म",
    "अपने आप को मार",
    "अपनी जान ले",
    "जान दे दूं",
    "जान देना चाहता",
]

_CRISIS_MESSAGES: dict[str, str] = {
    "en": (
        "It sounds like you may be carrying something very heavy right now, and "
        "I'm really glad you reached out. Please don't go through this alone — talk "
        "to someone who can help right away. In India you can call KIRAN at "
        "1800-599-0019 (24/7) or the Vandrevala Foundation at 1860-2662-345; if you "
        "are elsewhere or in immediate danger, please contact your local emergency "
        "services. Your life matters, and support is available."
    ),
    "hi": (
        "ऐसा लगता है कि आप इस समय बहुत गहरी पीड़ा से गुज़र रहे हैं, और मुझे खुशी है कि "
        "आपने अपनी बात कही। कृपया इसे अकेले मत सहिए — अभी किसी ऐसे व्यक्ति से बात करें "
        "जो मदद कर सके। भारत में आप किरण हेल्पलाइन 1800-599-0019 (24 घंटे) या वंद्रेवाला "
        "फ़ाउंडेशन 1860-2662-345 पर कॉल कर सकते हैं; यदि आप तत्काल ख़तरे में हैं तो कृपया "
        "अपनी स्थानीय आपातकालीन सेवाओं से संपर्क करें। आपका जीवन मूल्यवान है, और मदद उपलब्ध है।"
    ),
}


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, and strip the Devanagari nukta so that
    nukta and non-nukta spellings (e.g. ज़िंदगी / जिंदगी, ख़त्म / खत्म) match."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = text.replace("़", "")  # combining Devanagari nukta
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


# Pre-normalize keywords through the same pipeline as the haystack.
_NORMALIZED_KEYWORDS: list[str] = [_normalize(k) for k in CRISIS_KEYWORDS]


def is_crisis(text: str) -> bool:
    haystack = _normalize(text)
    return any(keyword in haystack for keyword in _NORMALIZED_KEYWORDS)


def crisis_response(language: str) -> str:
    return _CRISIS_MESSAGES.get(language, _CRISIS_MESSAGES["en"])
