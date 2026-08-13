"""Layer-1 guardrail tests — fully offline (the filter is a pure function; the
endpoint test mocks generation). Verifies the matching rules, nukta
normalization, the allow-list safeguards, and end-to-end suppression.
"""

import pytest
from fastapi.testclient import TestClient

from app import guardrail, main
from app.config import fallback_message

client = TestClient(main.app)


# --- 1. Blocklisted terms are caught, in sentences, both scripts ---------------

BLOCKED_SENTENCES = [
    "The teaching reminds me of what Muhammad once conveyed.",  # HIGHEST, Latin
    "इस विषय पर मुहम्मद ने भी कुछ कहा है।",                      # HIGHEST, Devanagari
    "This echoes Sathya Sai Baba's message of love.",           # phrase
    "साईं बाबा ने प्रेम की बात की।",                             # phrase, Devanagari
    "Consider what Mother Teresa embodied.",                    # ELEVATED phrase
    "That is the way of Gandhi.",                               # ELEVATED bare surname
    "गांधी ने अहिंसा सिखाई।",                                    # Devanagari surname
    "The Pope has spoken on forgiveness.",                      # POLITICAL/religious
    "This is like the era of Nehru.",                           # POLITICAL
    "Maharishi Mahesh Yogi taught a technique.",                # phrase
]


@pytest.mark.parametrize("sentence", BLOCKED_SENTENCES)
def test_blocked_terms_are_detected(sentence):
    assert guardrail.is_blocked(sentence) is True


# --- 2. Nukta normalization: with and without the nukta both match -------------

def test_nukta_variants_both_blocked():
    # खुमैनी (no nukta) and ख़ुमैनी (with nukta) must be treated identically.
    assert guardrail.is_blocked("खुमैनी की बात") is True
    assert guardrail.is_blocked("ख़ुमैनी की बात") is True


def test_precomposed_nukta_letter_blocked():
    # ख़ can arrive as the precomposed codepoint U+0959 OR as ख + ़ (U+0916 U+093C).
    precomposed = "ख़ुमैनी"   # ख़ुमैनी via U+0959
    decomposed = "ख़ुमैनी"  # ख + nukta + ...
    assert guardrail.is_blocked(precomposed) is True
    assert guardrail.is_blocked(decomposed) is True


# --- 3. Allow-list safeguards: these must NOT be suppressed --------------------

SAFE_SENTENCES = [
    "Krishna speaks of devotion in the Gita.",       # Krishna (not Muktananda/etc.)
    "कृष्ण ने भक्ति की बात की।",
    "Say yes to life, like a Sai within.",           # 'Sai' alone (not 'Sai Baba')
    "Teresa is a common name of grace.",             # 'Teresa' alone (not 'Mother Teresa')
    "Patel worked in the fields at dawn.",           # bare 'Patel' (only full forms blocked)
    "पटेल खेत में काम करता था।",
    "The maharishi sat in silence.",                 # 'maharishi' alone (not the full name)
    "महर्षि मौन में बैठे थे।",
    "Ram walked the forest path.",                   # Ram (not Nehru/etc.)
    "राम वन में चले।",
    "Ramana pointed to the Self.",                   # Ramana (not blocked, not 'Ram' substring)
    "Ramakrishna spoke of the Mother.",              # Ramakrishna
    "Buddha sat under the tree.",                    # Buddha
    "बुद्ध वृक्ष के नीचे बैठे।",
    "Jesus blessed the poor.",                       # Jesus
    "Lao Tzu wrote of the Way.",                     # Lao Tzu
    "Mahavira taught non-violence.",                 # Mahavira
    "महावीर ने अहिंसा सिखाई।",
    "Transcend the mind and meditate deeply.",       # 'Transcend'/'meditate' != 'Transcendental Meditation'
    "साई तत्व भीतर है।",                              # 'साई' alone (not 'साई बाबा')
    "Indira is an epithet of the goddess Lakshmi.",  # bare 'Indira' deliberately NOT blocked
    "इंदिरा लक्ष्मी का एक नाम है।",                    # bare 'इंदिरा' deliberately NOT blocked
]


def test_indira_full_phrase_still_blocked():
    # The full phrase remains blocked (also covered by the Gandhi block).
    assert guardrail.is_blocked("Indira Gandhi led the country.") is True
    assert guardrail.is_blocked("इंदिरा गांधी ने देश का नेतृत्व किया।") is True


@pytest.mark.parametrize("sentence", SAFE_SENTENCES)
def test_safeguards_pass(sentence):
    assert guardrail.is_blocked(sentence) is False


# --- 4. Word-boundary: a blocked word inside a larger word does NOT fire -------

def test_word_boundary_no_substring_false_positive():
    # 'Ram' is allowed and must not fire inside 'Ramakrishna' / 'framework'.
    assert guardrail.is_blocked("framework") is False
    assert guardrail.is_blocked("Ramakrishna Paramahansa") is False
    # 'Pope' must not fire inside a longer alphabetic run.
    assert guardrail.is_blocked("Popester is not a word") is False


# --- 5. End-to-end suppression through the endpoint (generation mocked) --------

def _stub_retrieval(monkeypatch):
    monkeypatch.setattr(main.settings, "api_shared_secret", "")
    monkeypatch.setattr(main, "is_class_judgment", lambda q: False)
    monkeypatch.setattr(main, "embed_question", lambda text, model: [0.0, 0.1])
    monkeypatch.setattr(
        main,
        "query_index",
        lambda api_key, index, vec, k: [
            {"score": 0.5, "book": "Some Book", "source": "Osho", "text": "..."}
        ],
    )


@pytest.mark.parametrize("language", ["hi", "en"])
def test_blocklisted_answer_is_suppressed_to_fallback(monkeypatch, language):
    _stub_retrieval(monkeypatch)
    # The model returns an answer that names a blocklisted figure.
    monkeypatch.setattr(
        main, "generate_answer", lambda *a, **k: "This reflects what Gandhi taught about truth."
    )
    res = client.post("/api/wisdom", json={"question": "tell me about truth", "language": language})
    assert res.status_code == 200
    body = res.json()
    # Fully suppressed -> identical to a normal decline: localized fallback, null book/source.
    assert body["answer"] == fallback_message(language)
    assert body["book"] is None
    assert body["source"] is None


def test_clean_answer_passes_through(monkeypatch):
    _stub_retrieval(monkeypatch)
    monkeypatch.setattr(
        main, "generate_answer", lambda *a, **k: "Truth is found in silence and awareness."
    )
    res = client.post("/api/wisdom", json={"question": "tell me about truth", "language": "en"})
    body = res.json()
    assert body["answer"] == "Truth is found in silence and awareness."
    assert body["book"] == "Some Book"
    assert body["source"] == "Osho"


# --- 6. Pre-generation class-judgment gate (classifier mocked) -----------------

@pytest.mark.parametrize("language", ["hi", "en"])
def test_class_judgment_query_declines_before_generation(monkeypatch, language):
    _stub_retrieval(monkeypatch)
    # Classified as a group-judgment query -> decline BEFORE retrieval/generation.
    monkeypatch.setattr(main, "is_class_judgment", lambda q: True)
    # If generation were reached, this would wrongly succeed; assert it is NOT.
    monkeypatch.setattr(main, "generate_answer", lambda *a, **k: "SHOULD NOT BE GENERATED")
    res = client.post("/api/wisdom", json={"question": "what about politicians?", "language": language})
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == fallback_message(language)
    assert body["book"] is None
    assert body["source"] is None


def test_class_judgment_failure_degrades_to_answering(monkeypatch):
    # A transient classifier error must NOT block a normal question.
    _stub_retrieval(monkeypatch)

    def boom(q):
        raise RuntimeError("classifier down")

    monkeypatch.setattr(main, "is_class_judgment", boom)
    monkeypatch.setattr(main, "generate_answer", lambda *a, **k: "A grounded reflection.")
    res = client.post("/api/wisdom", json={"question": "what is meditation?", "language": "en"})
    assert res.status_code == 200
    assert res.json()["answer"] == "A grounded reflection."


# --- 7. The blocklist actually loaded (guards against a silent inert filter) ---

def test_blocklist_is_loaded():
    assert guardrail.blocklist_size() > 0
