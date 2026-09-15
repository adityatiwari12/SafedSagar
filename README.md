# IP-SAKTI Sahayak

Citation-grounded assistant for **Ayurveda intellectual property, biodiversity / ABS, and
regulatory guidance**, built for the **Ministry of Ayush, Government of India**.

India and international jurisdictions are kept strictly separate. Answers cite statutes,
rules, treaties, and selected case law from a version-tracked corpus.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React + TypeScript + Vite + Tailwind (`apps/web`) |
| Backend | FastAPI + LangGraph (`apps/api`) |
| Vector store | ChromaDB |
| Relational store | Postgres (users, RBAC, source metadata) |
| Embeddings / LLM | Ollama (local default); optional cloud Llama |
| Ingestion | `ingestion/` — fetch, parse, chunk, embed, load |

## Repo layout

```
apps/web       — Ministry of Ayush–styled citizen UI (UX4G / GIGW conventions)
apps/api       — Auth, /query graph, RAG nodes
ingestion      — source_registry.yaml + pipeline scripts
corpus/raw     — downloaded PDFs (gitignored)
infra          — docker-compose (Postgres + Chroma)
```

## Quick start

### 1. Infrastructure

```bash
cd infra
docker compose up -d
```

Postgres: `localhost:5432` · Chroma: `localhost:8000`

### 2. API

```bash
cd apps/api
# configure .env from .env.example (set a strong JWT_SECRET)
.venv\Scripts\activate   # Windows
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

API runs on **:8001** (Chroma already uses :8000). Health: http://127.0.0.1:8001/health

### 3. Web

```bash
cd apps/web
cp .env.example .env     # VITE_API_BASE_URL=http://localhost:8001
npm install
npm run dev
```

Open http://127.0.0.1:5173 — register / login against the API. Chat uses a mock adapter by
default (`VITE_USE_MOCK_CHAT=true`) until a dedicated `/chat` endpoint is wired.

## Guided citizen journey

1. Language & jurisdiction (India / International)
2. Describe the Ayurvedic product or question
3. Minimum clarifying questions
4. Product / need classification
5. ABS / TK awareness check when relevant
6. Citation-grounded answer + confidence
7. Action plan + optional human facilitator escalation

## Important product rules

- **TKDL** is awareness-only (not retrieved live).
- **WIPO GRATK** (May 2024) is signed but **not yet in force**.
- Guidance is informational — verify against official gazettes for filings.

## Tests

```bash
# API
cd apps/api && .venv\Scripts\python.exe -m pytest tests/ -q

# Web
cd apps/web && npm test
```

## Branch

`v1` is the primary release line for this milestone (Phase 5 frontend + Wave A corpus backend).
