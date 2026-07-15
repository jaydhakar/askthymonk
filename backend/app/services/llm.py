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
