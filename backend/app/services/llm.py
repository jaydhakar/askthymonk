"""Answer generation via the chat model.

The model grounds its answer strictly in the retrieved Hindi passages, replies in
the requested language (paraphrasing Hindi into English when asked), keeps it to
3-4 spoken-friendly sentences, and returns the exact fallback sentence when the
passages don't actually address the question.
"""

from __future__ import annotations

from typing import Any

from ..config import FALLBACK_ANSWER, get_settings, language_label
from .embeddings import _client  # reuse the same authenticated OpenAI client

_SYSTEM_PROMPT = """You are the voice of the indexed Osho talks — a meditation \
teacher speaking warmly, simply, and directly to a seeker.

Follow these rules strictly:
- Answer ONLY from the retrieved passages given to you below. Never add outside \
knowledge, doctrine, biography, or invented detail.
- The source passages are in Hindi. Respond in {language_name}. If {language_name} \
is English, paraphrase the *meaning* of the Hindi into clear, natural English \
rather than translating word for word.
- Keep the answer to 3-4 short sentences. It will be read aloud, so let it flow \
naturally when spoken.
- Speak the insight directly. Never mention "passages", "chunks", "context", \
"retrieval", or that you are working from provided text.
- If the retrieved passages do not actually address the question, reply with \
exactly this sentence and nothing else: "{fallback}\""""


def generate_answer(question: str, chunks: list[dict[str, Any]], language: str) -> str:
    settings = get_settings()
    language_name = language_label(language)

    context = "\n\n".join(
        f"[Book: {c.get('book', '')}]\n{c.get('text', '')}".strip() for c in chunks
    )
    system_prompt = _SYSTEM_PROMPT.format(language_name=language_name, fallback=FALLBACK_ANSWER)
    user_content = f"Question: {question}\n\nRetrieved passages:\n{context}"

    response = _client().chat.completions.create(
        model=settings.chat_model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return (response.choices[0].message.content or "").strip()
