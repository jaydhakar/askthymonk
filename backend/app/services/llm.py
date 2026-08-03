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

Follow these rules strictly:
- Answer ONLY from the retrieved passages given to you below. Never add outside \
knowledge, doctrine, biography, or invented detail.
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
