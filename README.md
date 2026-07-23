# Ask Thy Monk

A cross-platform (iOS + Android) mobile app that lets you ask questions and
receive short, spoken-friendly answers drawn from a corpus of ~90 Hindi Osho
books — a RAG chat interface with **voice input and output** as a first-class
feature. A language toggle is built in from day one so English translations can
be added later without reworking the app.

- **Backend:** FastAPI (Python), retrieval over a Pinecone index, answers via an
  OpenAI chat model. See [`backend/README.md`](backend/README.md) for full detail.
- **Mobile:** React Native + Expo (managed workflow + `expo-dev-client`), with
  `expo-speech-recognition` (STT) and `expo-speech` (TTS).

```
/backend   FastAPI RAG service
/mobile    Expo app
```

## Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (backend)
- Node 20+ and npm (mobile)
- API keys: OpenAI + Pinecone, and your Pinecone index name
- For device voice testing: an Expo account and `eas-cli`
  (`npm i -g eas-cli`), plus a custom dev-client build (voice modules do not run
  in plain Expo Go)

## 1. Run the backend

```bash
cd backend
cp .env.example .env      # fill in OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Quick check (encoding-safe on Windows too):

```bash
python smoke_test.py       # from backend/, with the server running
```

Full endpoint/curl docs: [`backend/README.md`](backend/README.md).

> To reach the backend from a physical phone, start it so it listens on your LAN
> and use your computer's LAN IP in the mobile `.env` (see below). You can bind
> all interfaces with `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`.

## 2. Run the mobile app

```bash
cd mobile
npm install
cp .env.example .env       # set EXPO_PUBLIC_API_URL (LAN IP for a real phone)
npx expo start
```

Because voice relies on a native module, full functionality requires a custom
**dev client** build via EAS rather than Expo Go. Build profiles live in
[`mobile/eas.json`](mobile/eas.json) (`development` / `preview` / `production`).
The dev-client build step is called out separately during setup.

### Configuration

| Where | Var | Purpose |
|---|---|---|
| `backend/.env` | `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX`, … | see backend README |
| `mobile/.env` | `EXPO_PUBLIC_API_URL` | backend base URL (LAN IP for local, or the deployed Render URL) |
| `mobile/.env` | `EXPO_PUBLIC_API_KEY` | must match backend `API_SHARED_SECRET` when the gate is on |

Secrets live only in `.env` files (gitignored); never commit real keys.

## Deployment

The backend deploys to **Render** (free tier) via the `render.yaml` Blueprint at
the repo root — see the "Deploying to Render" section in
[`backend/README.md`](backend/README.md) for the full flow (env vars, the
shared-secret gate, and the free-tier cold-start behavior). Point the app at the
deployed backend by setting `mobile/.env`'s `EXPO_PUBLIC_API_URL` to the Render
URL (and `EXPO_PUBLIC_API_KEY` to match `API_SHARED_SECRET`), then re-bundle.
