# AI Code Review Tool

An AI-powered code review tool that connects to your GitHub repositories and delivers structured, actionable feedback using a locally-running LLM via [Ollama](https://ollama.com). All inference runs on your own machine — no API keys, no data leaving your environment.

[![CI](https://github.com/jaidenanders/code-review-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/jaidenanders/code-review-tool/actions/workflows/ci.yml)

---

## Features

- **GitHub OAuth** — Device Flow authentication (no redirect URI or hosted callback required)
- **Repository browser** — browse repos, navigate file trees, and load files directly into the review panel
- **Multi-file review** — select multiple files from the tree, chunk them at logical boundaries, and receive a single aggregated report
- **Streaming reviews** — tokens stream back from Ollama in real time via Server-Sent Events so you see feedback as it's generated
- **Review profiles** — switch focus between General, Security, Performance, and Style to tune what the model prioritises
- **Structured output** — every review is parsed into a quality score (0–100), per-severity issue cards, and a strengths list
- **Session history** — all reviews are persisted; revisit any past review from the sidebar
- **Diff viewer** — line-level diff between any two reviews in a session with a score delta

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.11, FastAPI, SQLAlchemy (async) |
| LLM runtime | Ollama (local) — codellama, deepseek-coder, or any compatible model |
| Database | SQLite (development) / PostgreSQL 16 (production) |
| Auth | GitHub OAuth Device Flow |
| Streaming | Server-Sent Events (`fetch` + `ReadableStream`, FastAPI `StreamingResponse`) |
| Testing | pytest, pytest-asyncio, respx, Vitest, @testing-library/react |
| CI | GitHub Actions |
| Containers | Docker, Docker Compose |

---

## Quick Start

The fastest way to run the full stack is Docker Compose. You need [Docker](https://docs.docker.com/get-docker/) and a GitHub OAuth App Client ID (see [setup](#github-oauth-app)).

```bash
git clone https://github.com/jaidenanders/code-review-tool.git
cd code-review-tool

cp .env.example .env
# Edit .env and set GITHUB_CLIENT_ID=your_id_here

docker compose up -d
```

Then pull a model (first run only):

```bash
docker compose exec ollama ollama pull codellama
```

Open **http://localhost:3000**. The app will be ready once the Ollama healthcheck passes (~15 s).

> **GPU acceleration** — to use a GPU with the Ollama container, add `deploy.resources.reservations.devices` to the `ollama` service in `docker-compose.yml` per the [Ollama Docker docs](https://hub.docker.com/r/ollama/ollama).

---

## Local Development

For hot-reload on both frontend and backend, run the services separately.

### Prerequisites

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com) installed locally

### 1. Start Ollama

```bash
ollama pull codellama
ollama serve
```

### 2. Backend

```bash
cd code-review-tool/backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example .env
# Edit .env — set GITHUB_CLIENT_ID and optionally DATABASE_URL

uvicorn app.main:app --reload
# API: http://localhost:8000
# Interactive docs: http://localhost:8000/docs
```

### 3. Frontend

```bash
cd code-review-tool/frontend

npm install
npm run dev
# App: http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`, so no CORS config is needed locally.

### Dev compose (optional)

If you prefer running just the database and Ollama in Docker while the backend and frontend run natively:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up db ollama -d
```

The dev override mounts the backend source as a volume and enables `--reload`; the frontend is expected to run via `npm run dev` on the host.

---

## GitHub OAuth App

1. Go to **GitHub → Settings → Developer settings → OAuth Apps → New OAuth App**
2. Set any homepage URL (e.g. `http://localhost:3000`)
3. Leave the callback URL blank — Device Flow does not use one
4. Copy the **Client ID** into your `.env` as `GITHUB_CLIENT_ID`

No client secret is needed for the Device Flow.

---

## Project Structure

```
code-review-tool/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # FastAPI route handlers (github, review)
│   │   ├── services/           # Business logic
│   │   │   ├── ollama_service.py     # Prompt building, batch + streaming LLM calls
│   │   │   ├── review_service.py     # Orchestration + response parsing
│   │   │   ├── profile_service.py    # Review focus profiles
│   │   │   ├── language_service.py   # Extension → language detection
│   │   │   ├── chunker_service.py    # Split large files at logical boundaries
│   │   │   ├── aggregator_service.py # Weighted score merge + deduplication
│   │   │   ├── session_service.py    # Review persistence
│   │   │   └── github_service.py     # GitHub API client
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── tests/              # pytest suite (227 tests)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── api/                # fetch wrappers (github.ts, review.ts)
│   │   ├── components/
│   │   │   ├── auth/           # DeviceFlow
│   │   │   ├── diff/           # DiffViewer
│   │   │   ├── history/        # SessionSidebar
│   │   │   ├── repos/          # RepoList, FileTree (single + multi-select)
│   │   │   └── review/         # CodePanel, StreamingCodePanel, ProfileSelector,
│   │   │                       #   ReviewResult, ScoreRing, IssueCard,
│   │   │                       #   MultiFileReviewResult, SelectedFilesPanel
│   │   ├── hooks/
│   │   │   └── useSseReview.ts # SSE state machine (idle→streaming→done→error)
│   │   ├── test/               # Vitest + Testing Library suite (138 tests)
│   │   └── types/              # Shared TypeScript interfaces
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── .github/
│   └── workflows/ci.yml        # Backend tests + frontend tests + Docker build
├── docker-compose.yml          # Production stack
├── docker-compose.dev.yml      # Dev overrides (hot-reload, SQLite)
└── .env.example
```

---

## API Reference

### GitHub

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/github/auth/device` | Start OAuth Device Flow — returns user code + verification URI |
| `GET` | `/api/v1/github/auth/poll` | Poll for access token after user authorises |
| `GET` | `/api/v1/github/repos` | List authenticated user's repositories |
| `GET` | `/api/v1/github/repos/{owner}/{repo}/tree` | Recursive file tree for a branch |
| `GET` | `/api/v1/github/repos/{owner}/{repo}/file` | Raw file content |

### Review

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/review/health` | Ollama status and list of available models |
| `GET` | `/api/v1/review/profiles` | List review focus profiles |
| `POST` | `/api/v1/review/` | Batch review — returns full `ReviewResult` |
| `POST` | `/api/v1/review/stream` | Streaming review — SSE: `token` events then a final `result` event |
| `POST` | `/api/v1/review/multi` | Multi-file review with per-file breakdown and aggregated result |
| `GET` | `/api/v1/review/sessions` | List all sessions, newest first |
| `GET` | `/api/v1/review/sessions/{id}` | Session with full review history |
| `DELETE` | `/api/v1/review/sessions/{id}` | Delete session and all its reviews |
| `GET` | `/api/v1/review/sessions/{id}/diff` | Line diff + score delta between two reviews |

#### Review request body

```json
{
  "code": "def add(a, b): return a + b",
  "filename": "math.py",
  "language": "python",
  "context": "utility function used across the codebase",
  "profile": "general"
}
```

`language` and `context` are optional — language is auto-detected from `filename` when omitted. `profile` is one of `general` | `security` | `performance` | `style`.

#### Streaming SSE events

```
event: token
data: {"text": "SUMMARY"}

event: token
data: {"text": ": the function is..."}

event: result
data: {"session_id": "...", "review_id": "...", "result": { ... }}
```

An `event: error` with `{"message": "..."}` is emitted if Ollama is unreachable.

---

## Testing

```bash
# Backend (227 tests)
cd code-review-tool/backend
pytest

# Frontend (138 tests)
cd code-review-tool/frontend
npm test

# Frontend production build check
npm run build
```

The test suite covers:

- OllamaService — prompt construction, batch review, streaming (token yielding, done sentinel, error handling)
- ReviewService — response parsing for all structured output fields
- Aggregator — weighted scoring, issue deduplication, strength merging
- Chunker — boundary detection, oversized section slicing, unknown language fallback
- Language detection — 55 extension mappings
- Profile service — all 4 profiles, fallback behaviour
- All API routes — happy paths, error propagation, session lifecycle, language auto-detect, profile passthrough
- React components — all 12 components with user-event interaction tests
- `useSseReview` hook — full state machine including error and reset flows
- API fetch helpers

CI runs all of the above plus a Docker build on every push via GitHub Actions.

---

## How It Works

1. **Auth** — GitHub Device Flow: the user enters a code at `github.com/login/device`; the frontend polls until the token is granted.
2. **File loading** — the GitHub API returns a recursive file tree; selecting a file fetches its content and pre-populates the review panel.
3. **Chunking** — files over ~12 000 characters are split at language-specific function/class boundaries (regex lookahead patterns) before sending to Ollama, preventing context-window overflows.
4. **Prompt building** — `OllamaService.build_prompt` injects a structured format spec and, for non-General profiles, a focus instruction that tells the model what to prioritise.
5. **Streaming** — `POST /review/stream` uses an `httpx` async generator to read Ollama's NDJSON stream line-by-line, forwarding each token as an SSE `data:` frame. The frontend consumes this with `fetch` + `ReadableStream` (not `EventSource`, which is GET-only).
6. **Parsing** — after streaming completes, the accumulated text is parsed by `ReviewService.parse_response` into a typed `ReviewResult` (score, issues with severity/category, strengths).
7. **Aggregation** — multi-file or multi-chunk reviews are merged with weighted score averaging (weighted by byte count), issue deduplication by `(category, severity, title[:50])`, and strength deduplication.
8. **Persistence** — every review is saved to SQLite/PostgreSQL via SQLAlchemy async; the session sidebar loads history on demand.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GITHUB_CLIENT_ID` | — | Required. GitHub OAuth App client ID |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `codellama` | Default model name |
| `DATABASE_URL` | `sqlite+aiosqlite:///./dev.db` | SQLAlchemy async connection string |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed origins |
