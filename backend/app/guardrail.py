"""Layer 1 of the name/content guardrail: a hard post-generation suppression filter.

After an answer is generated, `is_blocked()` scans it against a blocklist of
names/terms. If ANY term matches, the caller (main.py) FULLY SUPPRESSES the
answer and returns the ordinary localized decline instead — so a suppressed
answer is indistinguishable from a normal "I have not spoken on this" decline.

Matching rules:
  - case-insensitive (Latin case folded; Devanagari is caseless),
  - WORD-BOUNDARY, not raw substring — "Sai Baba" never fires on bare "Sai",
  - both Latin and Devanagari scripts,
  - multi-word entries match the full phrase (internal spaces required),
  - NUQTA-NORMALIZED — the nukta (़ U+093C) is stripped from BOTH the blocklist
    terms and the generated text before matching, and precomposed nukta letters
    (e.g. ख़ U+0959) are decomposed first, so खुमैनी and ख़ुमैनी are identical.

The blocklist itself is loaded from an env var or a GITIGNORED file — never from
a committed source file. See blocklist.example.txt for the format. Layer 2 (the
prompt-level rules in services/llm.py) is the primary defense against critical
FRAMING that a term filter cannot catch; this filter is the hard backstop for
NAMES.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("askthymonk.guardrail")

_NUKTA = "़"  # combining Devanagari nukta

# Characters that count as "inside a word" for boundary purposes: Latin
# alphanumerics + the Devanagari block EXCEPT the danda/double-danda punctuation
# (U+0964/U+0965), which must act as a boundary. Python's own \b relies on
# str.isalnum(), which is unreliable for Devanagari vowel signs / anusvara, so we
# define the boundary explicitly instead.
_WORD = r"A-Za-z0-9ऀ-ॣ०-ॿ"


def _normalize(text: str) -> str:
    """Fold case and strip the nukta so Latin case and nukta spelling variants
    collapse together. NFD first so precomposed nukta letters (क़ ख़ ग़ ज़ ड़ ढ़ फ़ य़)
    split into base + U+093C, then drop U+093C, recompose, lowercase."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = decomposed.replace(_NUKTA, "")
    return unicodedata.normalize("NFC", stripped).casefold()


def _read_raw_terms() -> list[str]:
    """Load blocklist lines from BLOCKLIST_TERMS (env; '|'- or newline-separated)
    if set, else from the gitignored file at BLOCKLIST_FILE (default
    backend/blocklist.txt). Missing/empty is allowed but logged loudly — the
    filter is then inert and only Layer 2 (the prompt) is protecting answers."""
    env_val = os.getenv("BLOCKLIST_TERMS", "")
    if env_val.strip():
        raw_lines = env_val.replace("|", "\n").splitlines()
        source = "env:BLOCKLIST_TERMS"
    else:
        default_path = Path(__file__).resolve().parent.parent / "blocklist.txt"
        path = Path(os.getenv("BLOCKLIST_FILE", str(default_path)))
        try:
            raw_lines = path.read_text(encoding="utf-8").splitlines()
            source = f"file:{path.name}"
        except FileNotFoundError:
            logger.warning(
                "GUARDRAIL blocklist not found (looked for env BLOCKLIST_TERMS and file %s). "
                "Layer-1 name suppression is INERT; only Layer-2 prompt rules are active.",
                path,
            )
            return []

    terms: list[str] = []
    for line in raw_lines:
        # Strip inline '#' comments and surrounding whitespace; skip blanks.
        term = line.split("#", 1)[0].strip()
        if term:
            terms.append(term)
    if not terms:
        logger.warning(
            "GUARDRAIL blocklist source %s is present but empty; Layer-1 suppression is INERT.",
            source,
        )
    else:
        logger.info("GUARDRAIL blocklist loaded: %d terms from %s", len(terms), source)
    return terms


@lru_cache(maxsize=1)
def _patterns() -> tuple[re.Pattern[str], ...]:
    """Compile one word-boundary regex per normalized blocklist term. Cached — the
    blocklist is read once per process; a change needs a restart."""
    pats: list[re.Pattern[str]] = []
    for term in _read_raw_terms():
        norm = _normalize(term)
        if not norm:
            continue
        # (?<![word]) ... (?![word]) is a script-aware word boundary: the term
        # must not be flanked by another word character in either script.
        pattern = rf"(?<![{_WORD}]){re.escape(norm)}(?![{_WORD}])"
        pats.append(re.compile(pattern))
    return tuple(pats)


def is_blocked(text: str) -> bool:
    """True if `text` contains any blocklisted term (see module docstring for the
    matching rules). Used by the endpoint to decide whether to suppress an
    otherwise-generated answer."""
    if not text:
        return False
    normalized = _normalize(text)
    return any(pat.search(normalized) for pat in _patterns())


def blocklist_size() -> int:
    """Number of active blocklist terms (0 = filter is inert). For startup logging."""
    return len(_patterns())
