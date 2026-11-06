"""Main FastAPI application entry point for Sonar."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sonar.api.routes_audit import router as audit_router
from sonar.api.routes_cloak import router as cloak_router
from sonar.api.routes_verify import router as verify_router

app = FastAPI(
    title="Sonar API",
    description="Local-first Acoustic Side-Channel Security & Forensics Suite",
    version="0.1.0",
)

# Explicit CORS allowlist conforming to OWASP specifications
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "SONAR_ALLOWED_ORIGINS",
        "http://localhost:50242,http://127.0.0.1:50242,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(audit_router)
app.include_router(cloak_router)
app.include_router(verify_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sonar-core",
        "version": "0.1.0",
    }
