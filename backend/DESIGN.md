# Ask Thy Monk — Backend Design Notes

Design decisions that aren't obvious from the code alone. Implementation lives in
`app/`; this file explains the *why*.

## Retrieval

- **Two separate Pinecone accounts** (Hindi + English), one index each, queried
  in their default namespace. `retrieval_target(language)` returns a frozen
  `RetrievalTarget` bundling `embedding_model` + `pinecone_api_key` +
  `pinecone_index` + `top_k` as one matched pair, so a query can never embed with
  one model and search an index built by another (dimension mismatch).
- Both indexes use `text-embedding-3-large` (3072-dim) at `top_k=3`, chosen after
  a head-to-head comparison against `-small`.

## Conversation memory (two-stage follow-up)

Turn 2+ only. First `is_followup()` classifies the latest question as a genuine
follow-up vs a new subject (biased to NEW on any doubt); only a follow-up is then
rewritten by `reformulate_query()` into a standalone retrieval query. A new/
ambiguous question is embedded verbatim, so a topic switch never grafts the prior
topic on. Only the *retrieval* query changes — answer generation always receives
the original question plus prior turns. Any failure degrades to the original
question.

## Decline handling

The model emits a language-independent sentinel (`NO_ANSWER`) when the passages
don't address the question. `is_no_answer()` detects it even if translated/
decorated, and the endpoint maps it to the localized fallback with `book`/
`source` nulled.

## Safety: crisis path

`is_crisis()` scans the *accumulated* conversation (all prior user turns + the
new message), so distress built up gradually is still caught. It runs before RAG
and returns caring, resource-bearing text — never the Osho persona. Matching is
nukta-normalized (see below) and covers English, transliterated, and Devanagari
forms.

## Safety: name/content guardrail

Zero risk appetite for the answer layer naming or disparaging real political/
religious figures or generalizing about groups. Three independent layers; the
corpus is untouched — this is purely a query/answer-layer guardrail.

- **Layer 0** — pre-generation gate that declines group-judgment *queries*.
- **Layer 2** — prompt rules that steer *framing* away from criticism.
- **Layer 1** — hard post-generation filter that suppresses answers containing a
  blocklisted *name*.

### Layer 0 — pre-generation class-judgment decline gate

Some queries (e.g. "what does Osho say about politicians?") retrieve passages
that are *inherently* critical of a group of people, so a grounded answer tends to
reproduce that criticism no matter how the prompt is worded. For these,
`is_class_judgment(question)` (`services/llm.py`, an LLM classifier, temp 0,
biased to OK) runs in `/api/wisdom` on the resolved standalone query — *before*
retrieval/generation. If it fires, the endpoint returns the ordinary localized
decline (indistinguishable from a normal one; `outcome=decline_class_judgment`),
never generating from the critical passages. A classifier error degrades to
answering normally, so a transient failure never blocks a legitimate question.

It is deliberately **narrow**: it declines only requests to judge/characterize a
group of *people* as a whole (politicians, a profession, a caste, a religious
community). It does NOT decline personal/spiritual questions, abstract or
institutional topics ("organized religion", "the ego", "society"), or questions
that merely mention a group without asking for a verdict on it. Verified live:
declines politician/leader/priest judgment queries (both languages) while
"anger at my boss", "how should I treat my community", "what is wrong with
organized religion", love, meditation, and anger questions all ground normally.

The corpus is untouched — this is purely a query/answer-layer gate.

### Layer 2 — prompt-level rules (primary defense for *framing*)

Rules baked into `_SYSTEM_PROMPT` (`services/llm.py`): never name any political
figure/head of state (living or dead); never critique/mock/disparage any
religion, sect, caste, or creed; never make sweeping derogatory generalizations
about any group, class, profession, or community (e.g. "politicians are
criminals") — not just named individuals; never produce critical/mocking content
about a specific religious or political figure **even if a passage does so and
even if the figure is unnamed** — reframe to the underlying teaching, or decline.
This catches critical *framing* that a term filter cannot see.

### Layer 1 — hard post-generation suppression filter (backstop for *names*)

`guardrail.is_blocked(answer)` (`app/guardrail.py`) scans the generated answer
against a blocklist. On any match the endpoint **fully suppresses** the answer
and returns the ordinary localized decline — indistinguishable from a normal
"not spoken on this" reply (same fallback text, `book`/`source` nulled). The
matched term is deliberately *not* logged (no-text-retention policy); only
`outcome=suppressed_blocklist` is logged.

Matching rules:

- case-insensitive (Latin folded; Devanagari is caseless),
- **word-boundary**, not raw substring — a phrase like "Sai Baba" never fires on
  bare "Sai"; boundaries are script-aware (Latin + Devanagari, excluding the
  danda `।`/`॥` which act as boundaries), because Python's native `\b` is
  unreliable around Devanagari vowel signs/anusvara,
- both Latin and Devanagari,
- multi-word entries match the whole phrase,
- **nukta-normalized** — the nukta (़ U+093C) is stripped from both the blocklist
  terms and the answer text, and precomposed nukta letters (e.g. ख़ U+0959) are
  NFD-decomposed first, so खुमैनी and ख़ुमैनी are identical.

### Blocklist storage

The blocklist is **never committed**. Loaded (in precedence order) from:

1. env var `BLOCKLIST_TERMS` (`|`- or newline-separated) — used on Render,
2. else the gitignored file at `BLOCKLIST_FILE` (default `backend/blocklist.txt`).

`blocklist.example.txt` (committed) documents the format with placeholders only.
A missing/empty blocklist is allowed but logged as a loud WARNING at startup
(`guardrail blocklist active terms=0`) — the filter is then inert and only
Layer 2 protects answers. `blocklist_size()` is logged at import as a deploy
check.

**Deploy note:** because the file is gitignored it is NOT present on Render. The
live backend must get the blocklist via the `BLOCKLIST_TERMS` env var (or a
Render Secret File mounted at the `BLOCKLIST_FILE` path). Confirm the startup log
shows a non-zero term count after deploy.

## Known residual false positives (accepted, zero-risk-appetite tradeoff)

Bare common-word entries over-suppress by design:

- **Pope** also suppresses unrelated senses (e.g. the poet Alexander Pope).
- **Gandhi / गांधी** (bare surname) suppresses any answer using the surname in any
  sense.

**Indira** is deliberately **full-phrase only** ("Indira Gandhi" / "इंदिरा गांधी"),
NOT a bare block — so the goddess-Lakshmi epithet "Indira" is not suppressed. The
bare Gandhi block already covers "Indira Gandhi" regardless.

These are intentional: over-suppression (a harmless decline) is preferred to any
risk of naming. Revisit only if false declines become noticeable in use.

## Versioning

`app.version` (surfaced on `/health`) doubles as a deploy-verification marker;
bump it with each user-visible backend behavior change.
