# IP-SAKTI Sahayak — Web

React + TypeScript frontend for the Ministry of Ayush Sahayak service. Visual language follows
**UX4G / GIGW** conventions (State Emblem, tricolor bar, skip link, breadcrumbs, high-contrast
focus, Noto Sans).

## Run

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:5173 — unauthenticated users are sent to `/login`.

API default: `VITE_API_BASE_URL=http://localhost:8001` (see `.env.example`). Start the
FastAPI service for real register/login. ChromaDB uses port 8000; the API runs on 8001.

## Test

```bash
npm test
```

## Chat backend

`VITE_USE_MOCK_CHAT` defaults to **true**. Mock fixtures cover patent / ABS / Ayurveda
Aahara paths with clarifying questions, citations, confidence, ABS/TK flags, and action
plans. Set `VITE_USE_MOCK_CHAT=false` when `/chat` and `/escalations` exist.
