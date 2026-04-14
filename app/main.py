"""Application entrypoint for the manufacturing analytics API."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router as analysis_router
from app.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "A production-style LangChain and LangGraph multi-agent system for "
        "manufacturing anomaly analysis."
    ),
)
app.include_router(analysis_router)


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Simple readiness endpoint."""

    return {"status": "ok"}

