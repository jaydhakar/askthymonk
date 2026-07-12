"""Distress / crisis detection.

A deliberately small keyword list. When a question matches, we skip RAG and the
Osho persona entirely and return a direct, caring message with crisis resources.
This is a safety net, not a diagnostic tool.
"""

from __future__ import annotations

import re

# English (incl. common transliterated Hindi) and Devanagari markers of
# self-harm / suicidal ideation / acute despair. Devanagari has no case, and we
# lowercase the haystack, so these match case-insensitively via substring.
CRISIS_KEYWORDS: list[str] = [
    # English
    "suicide",
    "suicidal",
    "kill myself",
    "killing myself",
    "end my life",
    "end it all",
    "want to die",
    "wanna die",
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
    "jeena nahi chahta",
    "jeena nahi chahti",
    # Devanagari
    "आत्महत्या",
    "खुदकुशी",
    "मरना चाहता",
    "मरना चाहती",
    "जीना नहीं चाहता",
    "जीना नहीं चाहती",
    "खुद को खत्म",
    "अपनी जान ले",
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
    return re.sub(r"\s+", " ", text.lower()).strip()


def is_crisis(text: str) -> bool:
    haystack = _normalize(text)
    return any(keyword in haystack for keyword in CRISIS_KEYWORDS)


def crisis_response(language: str) -> str:
    return _CRISIS_MESSAGES.get(language, _CRISIS_MESSAGES["en"])
