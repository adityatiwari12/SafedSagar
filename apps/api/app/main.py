"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.cases.router import router as cases_router
from app.chat.router import router as chat_router
from app.query.router import router as query_router
from app.translation.router import router as translation_router

app = FastAPI(title="IP-SAKTI Sahayak API")

# Prototype CORS — Vite dev server talks to the API (Chroma already owns
# :8000). 5174 included since Vite falls back to it when another Vite
# instance (e.g. a concurrent session's dev server) already holds 5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(query_router)
app.include_router(chat_router)
app.include_router(cases_router)
app.include_router(admin_router)
app.include_router(translation_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
