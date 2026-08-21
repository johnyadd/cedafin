"""
engine/main.py — FastAPI wrapper around the metrics engine.

Deploy to Render (Starter tier, no cold-start sleep).
Start command:  uvicorn main:app --host 0.0.0.0 --port $PORT
Local:          uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from metrics import ENGINE_VERSION, compute_metrics

app = FastAPI(title="CediWise Engine", version=ENGINE_VERSION)

# Only the Next.js app calls this. Set ALLOWED_ORIGIN in Render to your Vercel
# domain; the default keeps local development working.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class Observation(BaseModel):
    as_of: str
    nav: float | None = None
    yield_annualised: float | None = None


class BenchmarkPoint(BaseModel):
    as_of: str
    value: float


class MetricsRequest(BaseModel):
    product_id: str | None = None
    as_of: str | None = None
    currency: str = "GHS"
    observations: list[Observation] = Field(default_factory=list)
    benchmarks: dict[str, list[BenchmarkPoint]] = Field(default_factory=dict)
    windows: list[str] | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    """Render health check. Also the first thing to curl when Next.js 500s."""
    return {"status": "ok", "engine_version": ENGINE_VERSION}


@app.post("/compute/metrics")
def metrics(req: MetricsRequest) -> dict[str, Any]:
    if not req.observations:
        raise HTTPException(status_code=400, detail="observations required")
    try:
        return compute_metrics(req.model_dump())
    except (KeyError, ValueError) as exc:
        # Bad data is a 400, not a 500 — it means the ingestion layer let
        # something through that validation should have caught.
        raise HTTPException(status_code=400, detail=f"invalid payload: {exc}") from exc
