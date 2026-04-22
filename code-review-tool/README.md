# AI Code Review Tool

An AI-powered code review tool that connects to your GitHub repos and provides structured feedback using a locally-running LLM via Ollama.

## Features

- **GitHub Integration** — OAuth Device Flow (no redirect URI), repo browsing, file tree, file content fetching
- **Local LLM Review** — Ollama-backed review engine (codellama, deepseek-coder, etc.)
- **Structured Output** — Bug flags, complexity analysis, security issues, suggestions, quality score (0–100)
- **Session History** — Every review is persisted; track improvements over time
- **Diff Viewer** — Line-level diff between two reviews of the same file

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy (async) |
| LLM | Ollama (local) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | React + Vite (Sprint 3) |
| Auth | GitHub OAuth Device Flow |
| Testing | pytest, pytest-asyncio, respx, 97 tests |

## Project Structure

```
code-review-tool/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI route handlers
│   │   ├── services/         # Business logic (GitHub, Ollama, Review, Session)
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── tests/            # pytest test suite (97 tests)
│   ├── .env.example
│   ├── pytest.ini
│   └── requirements.txt
├── docker-compose.yml
└── .gitignore
```

## Getting Started

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com) installed and running
- A GitHub OAuth App (Client ID only needed for Device Flow)

### 1. Pull a model

```bash
ollama pull codellama
ollama serve
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your GITHUB_CLIENT_ID
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 4. Run the tests

```bash
pytest
```

## API Endpoints

### GitHub
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/github/auth/device` | Start OAuth Device Flow |
| GET | `/api/v1/github/auth/poll` | Poll for token |
| GET | `/api/v1/github/repos` | List user repos |
| GET | `/api/v1/github/repos/{owner}/{repo}/tree` | Get file tree |
| GET | `/api/v1/github/repos/{owner}/{repo}/file` | Get file content |

### Review
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/review/health` | Ollama status + available models |
| POST | `/api/v1/review/` | Submit code for review |
| GET | `/api/v1/review/sessions` | List all sessions |
| GET | `/api/v1/review/sessions/{id}` | Get session + review history |
| DELETE | `/api/v1/review/sessions/{id}` | Delete session |
| GET | `/api/v1/review/sessions/{id}/diff` | Diff two reviews |

## Production (Docker)

```bash
cp .env.example .env
# Fill in GITHUB_CLIENT_ID
docker-compose up
```

This starts the FastAPI backend + PostgreSQL. Point Ollama at `host.docker.internal:11434`.

## Sprint Roadmap

- [x] Sprint 1 — GitHub OAuth + repo/file fetching
- [x] Sprint 2 — Ollama review engine + session persistence
- [ ] Sprint 3 — React frontend (repo browser, review panel, diff viewer)
