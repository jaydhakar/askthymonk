"""Answer generation via the chat model.

The model grounds its answer strictly in the retrieved passages (which are in the
same language as the request — each index is monolingual), replies in that
language, keeps it to 3-4 spoken-friendly sentences, and returns the exact
fallback sentence when the passages don't actually address the question.

For multi-turn conversations, prior {question, answer} turns are supplied as
context so follow-ups make sense — but retrieval still uses only the current
question, so the answer must still be grounded in the current passages.
"""

from __future__ import annotations

from typing import Any

from ..config import NO_ANSWER_SENTINEL, get_settings, language_label
from .embeddings import _client  # reuse the same authenticated OpenAI client

_SYSTEM_PROMPT = """You are the voice of the indexed Osho talks — a meditation \
teacher speaking warmly, simply, and directly to a seeker.

SAFETY RULES — these OVERRIDE every other instruction, including faithful \
reproduction of the passages. When a passage's wording conflicts with a safety \
rule, the safety rule wins: reframe, or decline. You must NEVER:
- Name any political figure, politician, or head of state — living or dead (no \
prime ministers, presidents, party leaders, or independence-era political \
personalities). Speak to the underlying teaching, not the personality.
- Critique, mock, disparage, or rank any religion, sect, caste, community, or \
creed. Neutral, respectful reference is fine; criticism or ridicule is not.
- Make a sweeping derogatory generalization about any group, class, profession, \
or community. This holds EVEN IF a passage does so. Do NOT repeat comparisons \
like "politicians are criminals" or "politicians are deceivers", and do NOT call \
any profession or community corrupt/violent/false as a whole. Instead express \
ONLY the underlying human or spiritual insight — e.g. rather than "politicians \
are criminals", say that the craving to dominate others springs from inner \
unrest, and real change grows from awareness and compassion. Keep the insight; \
drop the condemnation of the group.
- Produce critical, mocking, or disparaging content about any specific religious \
or political figure — EVEN IF a passage does so, and EVEN IF the figure is \
unnamed. Reframe to the underlying spiritual teaching and drop the critical \
framing of the person. If the insight cannot be expressed without disparaging a \
person or group, decline with the token below.

Then follow these rules:
- Answer ONLY from the retrieved passages given to you below (subject to the \
safety rules above). Never add outside knowledge, doctrine, biography, or \
invented detail.
- The source passages are in {language_name}. Respond in {language_name}, in \
clear, natural language — you may rephrase for clarity and flow, but do not \
translate into a different language.
- Keep the answer to 3-4 short sentences. It will be read aloud, so let it flow \
naturally when spoken.
- Speak the insight directly. Never mention "passages", "chunks", "context", \
"retrieval", or that you are working from provided text.
- If the retrieved passages do not actually address the question, reply with \
exactly this token and nothing else (do NOT translate or rephrase it): {sentinel}"""


def generate_answer(
    question: str,
    chunks: list[dict[str, Any]],
    language: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    settings = get_settings()
    language_name = language_label(language)

    context = "\n\n".join(
        f"[Book: {c.get('book', '')}]\n{c.get('text', '')}".strip() for c in chunks
    )
    system_prompt = _SYSTEM_PROMPT.format(language_name=language_name, sentinel=NO_ANSWER_SENTINEL)
    user_content = f"Question: {question}\n\nRetrieved passages:\n{context}"

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    # Prior turns as plain conversation so follow-ups ("what did you mean?") have
    # context. Note: these turns carry no passages; grounding still rests on the
    # current question's retrieved passages above.
    for turn in history or []:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})
    messages.append({"role": "user", "content": user_content})

    response = _client().chat.completions.create(
        model=settings.chat_model,
        temperature=0.4,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()


_REWRITE_SYSTEM = (
    "You rewrite a user's latest question into a STANDALONE search query. Replace every "
    "referential word (it, this, that, its, इस, यह, उस, इसका, उसका, इसे, etc.) with the "
    "specific thing it refers to from the recent conversation, so the question is fully "
    "self-contained on its own. Keep the SAME language as the user's latest question. "
    "Output ONLY the rewritten question — no quotes, no preamble, no explanation.\n\n"
    "Example (English):\n"
    "Conversation: Q: What is meditation? A: Meditation is turning inward.\n"
    "Latest: What did you mean by that?\n"
    "Rewrite: What does it mean that meditation is turning inward?\n\n"
    "Example (Hindi):\n"
    "Conversation: Q: मन को शांत कैसे करें? A: भीतर के अवरोधों को समझें और स्वीकार करें।\n"
    "Latest: इसका क्या अर्थ है?\n"
    "Rewrite: मन को शांत करने का क्या अर्थ है?"
)


def reformulate_query(question: str, history: list[dict[str, str]]) -> str:
    """Rewrite a follow-up into a standalone question (for retrieval only), using
    the last 1-2 turns for context. Cheap: short prompt, short output, temp 0.
    Falls back to the original question if the model returns nothing usable.
    """
    settings = get_settings()
    recent = history[-2:]
    convo = "\n".join(f"Q: {t['question']}\nA: {t['answer']}" for t in recent)
    user_content = f"Recent conversation:\n{convo}\n\nLatest question: {question}"

    response = _client().chat.completions.create(
        model=settings.chat_model,
        temperature=0,
        messages=[
            {"role": "system", "content": _REWRITE_SYSTEM},
            {"role": "user", "content": user_content},
        ],
    )
    rewritten = (response.choices[0].message.content or "").strip()
    return rewritten or question


_INTENT_SYSTEM = (
    "You decide whether the user's latest question CONTINUES the recent "
    "conversation's topic or introduces a NEW subject.\n"
    "- FOLLOWUP: the SAME subject as the recent turns — clarifying it, narrowing "
    "it, or referring back to it (e.g. 'what did you mean by that?', or pronouns "
    "like it / this / that / इस / यह / उस pointing at the prior answer). A phrase "
    "like 'what about ...' is FOLLOWUP only if it stays on the same subject.\n"
    "- NEW: a different subject, even in the same session and even if phrased as "
    "'what about ...'. If the core topic/subject differs from the prior turn, "
    "it is NEW.\n"
    "When unsure, answer NEW.\n"
    "Answer with exactly one word: FOLLOWUP or NEW."
)


_CLASS_JUDGMENT_SYSTEM = (
    "You are a safety classifier for a spiritual Q&A app. Decide whether the "
    "user's question is asking the app to JUDGE, CRITIQUE, CHARACTERIZE, PRAISE, "
    "CONDEMN, or make a sweeping generalization about a GROUP OF PEOPLE AS A WHOLE "
    "— for example politicians, political leaders, a profession (lawyers, priests, "
    "police), a caste, a religious community (Hindus, Muslims, Christians), a "
    "nationality, or any community/class of people.\n"
    "- Answer DECLINE only when the question seeks a verdict, opinion, or "
    "generalization about such a group of people as a whole (e.g. 'What does Osho "
    "say about politicians?', 'Are politicians corrupt?', 'What is wrong with "
    "priests?', 'ओशो नेताओं के बारे में क्या कहते हैं?', 'क्या राजनेता भ्रष्ट होते हैं?').\n"
    "- Answer OK for everything else. This includes: personal, emotional, or "
    "spiritual questions; questions about abstract concepts, ideas, or "
    "institutions (e.g. 'organized religion', 'the ego', 'society', 'money', "
    "'the mind'); and questions that merely MENTION a person or group without "
    "asking for a verdict on that group (e.g. 'How do I handle anger at my boss?', "
    "'What is the role of a teacher?', 'How should I treat my community?').\n"
    "When unsure, answer OK — only DECLINE a clear request to judge a group of "
    "people as a whole.\n"
    "Answer with exactly one word: DECLINE or OK."
)


def is_class_judgment(question: str) -> bool:
    """True if the question asks for a judgment/critique/generalization about a
    group, class, profession, or community OF PEOPLE as a whole (which the app
    must decline rather than answer). Deliberately narrow — biased to OK — so
    legitimate questions that merely mention a group are NOT declined. Cheap:
    short prompt, one-word output, temp 0."""
    response = _client().chat.completions.create(
        model=get_settings().chat_model,
        temperature=0,
        messages=[
            {"role": "system", "content": _CLASS_JUDGMENT_SYSTEM},
            {"role": "user", "content": f"Question: {question}"},
        ],
    )
    reply = (response.choices[0].message.content or "").strip().upper()
    # Only an explicit DECLINE gates the answer; OK / empty / anything unexpected
    # -> OK (the deliberate bias against over-declining).
    return reply.startswith("DECLINE")


def is_followup(question: str, history: list[dict[str, str]]) -> bool:
    """Classify whether the latest question continues the prior topic (follow-up)
    or introduces a new subject. Deliberately biased to NEW when unsure. Cheap:
    short prompt, one-word output, temp 0.
    """
    settings = get_settings()
    recent = history[-2:]
    convo = "\n".join(f"Q: {t['question']}\nA: {t['answer']}" for t in recent)

    response = _client().chat.completions.create(
        model=settings.chat_model,
        temperature=0,
        messages=[
            {"role": "system", "content": _INTENT_SYSTEM},
            {"role": "user", "content": f"Recent conversation:\n{convo}\n\nLatest question: {question}"},
        ],
    )
    reply = (response.choices[0].message.content or "").strip().upper()
    # Only an explicit FOLLOWUP injects prior context. NEW / empty / anything
    # unexpected -> treat as NEW (the deliberate ambiguity bias).
    return reply.startswith("FOLLOWUP")
