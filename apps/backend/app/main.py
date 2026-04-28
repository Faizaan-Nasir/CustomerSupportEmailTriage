"""Backend application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.agent import router as agent_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.tickets import router as tickets_router


app = FastAPI(
    title="Customer Support Email Triage API",
    version="0.1.0",
    description="Backend API for ingesting, interpreting, and managing support tickets.",
)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    """Simple root endpoint for local boot verification."""
    return {"message": "Customer Support Email Triage API is running."}


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Lightweight health endpoint for smoke tests and local monitoring."""
    return {"status": "ok"}


app.include_router(ingest_router)
app.include_router(tickets_router)
app.include_router(agent_router)
