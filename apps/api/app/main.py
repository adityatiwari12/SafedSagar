"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.auth.router import router as auth_router

app = FastAPI(title="IP-SAKTI Sahayak API")

app.include_router(auth_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
