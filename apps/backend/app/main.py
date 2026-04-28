"""Backend application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent import router as agent_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.tickets import router as tickets_router


app = FastAPI(
    title="Customer Support Email Triage API",
    version="0.1.0",
    description="Backend API for ingesting, interpreting, and managing support tickets.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
