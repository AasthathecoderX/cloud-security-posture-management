"""API entry point.

Exposes:
- Phase 0 /health probe
- Authentication endpoints
- Phase 2 scan endpoints
- Phase 7 compliance endpoints
- Attack-path endpoints

The backend/src directory is placed on sys.path so modules there can be
imported as top-level modules whether the app is run from backend/
(uvicorn main:app) or elsewhere.
"""

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


# ---------------------------------------------------------------------------
# Make backend/src importable
# ---------------------------------------------------------------------------

SRC = Path(__file__).resolve().parent / "src"

# Force backend/src to be at index 0 of sys.path to prevent module collisions
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Application imports
# ---------------------------------------------------------------------------

from parser import MAX_FILE_SIZE
from routes import router as scans_router
from compliance.routes import router as compliance_router
from attack_paths.routes import router as attack_paths_router
from auth.routes import router as auth_router


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="CSPM API")


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
]

if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ---------------------------------------------------------------------------
# Request body size protection
# ---------------------------------------------------------------------------

_MAX_REQUEST_BYTES = MAX_FILE_SIZE + 64 * 1024


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    """Reject requests whose declared body size exceeds the configured limit."""

    content_length = request.headers.get("content-length")

    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Invalid Content-Length header."
                },
            )

        if declared > _MAX_REQUEST_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": (
                        f"Request body exceeds the maximum of "
                        f"{_MAX_REQUEST_BYTES} bytes."
                    )
                },
            )

    return await call_next(request)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# M1 Authentication
app.include_router(auth_router)

# Existing project routers
app.include_router(scans_router)
app.include_router(compliance_router)
app.include_router(attack_paths_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}