# Zen Wisdom Explorer — Backend

FastAPI RAG service over a Pinecone index of ~90 Hindi Osho books. Given a
question, it embeds the question, retrieves the most relevant passages from the
namespace for the chosen language, and asks a chat model to answer — grounded
strictly in those passages, in the requested language, in 3–4 spoken-friendly
sentences. Distress/crisis questions bypass retrieval and return caring
resources instead.

The index is treated as **read-only**: this app only ever queries it.

## Requirements

- Python 3.11+ (tested target: 3.14)
- [uv](https://docs.astral.sh/uv/) for env/dependency management
- API keys for OpenAI and Pinecone, plus your Pinecone index name

## Setup

```bash
cd backend

# 1. Create your local env file and fill it in (see .env.example for every var)
cp .env.example .env        # then edit .env

# 2. Install deps into a uv-managed virtual env
uv sync
```

`.env` must contain at least `OPENAI_API_KEY`, `PINECONE_API_KEY`, and
`PINECONE_INDEX`. The model names default to `text-embedding-3-large` and
`gpt-4o-mini` but can be overridden via `EMBEDDING_MODEL` / `CHAT_MODEL`.

> The embedding model **must** match the one your index was built with
> (`text-embedding-3-large`, 3072 dims) or similarity search will silently
> return garbage.

## Run locally

```bash
# From the backend/ directory
uv run uvicorn app.main:app --reload --port 8000
```

The server listens on `http://localhost:8000`.

## Endpoints & curl tests

### 1. Health check

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

### 2. Supported languages

The mobile app reads this to populate its language toggle — it never hardcodes
the options. Today it returns only Hindi.

```bash
curl http://localhost:8000/api/languages
```

Expected (with the default `SUPPORTED_LANGUAGES=["hi"]`):

```json
{"languages":[{"code":"hi","label":"Hindi"}]}
```

### 3. Ask wisdom (Hindi — the populated corpus)

`language` defaults to `"hi"` if omitted.

```bash
curl -X POST http://localhost:8000/api/wisdom \
  -H "Content-Type: application/json" \
  -d '{"question": "मन को शांत कैसे करें?", "language": "hi"}'
```

Expected shape (actual text depends on your index):

```json
{"answer":"...", "book":"...", "language":"hi"}
```

If nothing relevant is retrieved, `answer` is exactly:
`"I have not spoken on this specific matter in the indexed literature."` and
`book` is `null`.

### 4. Ask wisdom in English (paraphrased from the Hindi sources)

```bash
curl -X POST http://localhost:8000/api/wisdom \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I quiet my mind?", "language": "hi"}'
```

Note: send `"language":"hi"` to search the Hindi corpus but you can also ask the
question in English — retrieval is by meaning. The **`en`** language searches the
(currently empty) `en` namespace and will gracefully return the "not indexed"
fallback until English books are added.

### 5. Empty namespace fallback (English namespace, empty today)

```bash
curl -X POST http://localhost:8000/api/wisdom \
  -H "Content-Type: application/json" \
  -d '{"question": "What is meditation?", "language": "en"}'
```

> Only works if `en` is in `SUPPORTED_LANGUAGES`; otherwise the server treats the
> request as the default language. Expected when `en` is empty:

```json
{"answer":"I have not spoken on this specific matter in the indexed literature.","book":null,"language":"en"}
```

### 6. Crisis / distress path (no API calls, no RAG)

```bash
curl -X POST http://localhost:8000/api/wisdom \
  -H "Content-Type: application/json" \
  -d '{"question": "I want to end my life", "language": "en"}'
```

Returns a direct, caring message with crisis helpline resources and `book:null`.
This path never touches OpenAI or Pinecone, so it works even without API keys.

## Configuration reference

| Env var | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI auth (required) |
| `PINECONE_API_KEY` | — | Pinecone auth (required) |
| `PINECONE_INDEX` | — | Index name (required) |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | Query embedding model |
| `CHAT_MODEL` | `gpt-4o-mini` | Answer generation model |
| `SUPPORTED_LANGUAGES` | `["hi"]` | Languages the app may offer |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `RATE_LIMIT` | `20/minute` | Per-IP limit on `/api/wisdom` |
| `TOP_K` | `3` | Chunks retrieved per query |
| `API_SHARED_SECRET` | *(empty)* | If set, `/api/wisdom` requires a matching `X-API-Key` header |

## Tests

```bash
uv run pytest
```

Covers the crisis/distress matcher (both languages, transliteration, nukta
spelling variants, and the exact phrase that once slipped through) plus the
crisis routing and the `X-API-Key` gate — all offline, no API keys needed.

## Optional: shared-secret gate

Set `API_SHARED_SECRET` (and the matching `EXPO_PUBLIC_API_KEY` in `mobile/.env`)
to require an `X-API-Key` header on `/api/wisdom`. Empty by default (open, for
local dev). This deters casual direct hits on a deployed URL, but note that a
secret shipped inside a public mobile app is extractable — it is not a
substitute for real authentication.

## How language maps to Pinecone

| `language` | Namespace | Contents |
|---|---|---|
| `hi` | *(default namespace, `""`)* | ~90 Hindi Osho books |
| `en` | `en` | reserved for future English books (empty today) |
