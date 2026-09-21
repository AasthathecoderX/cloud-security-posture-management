"""API entry point.

Exposes the Phase 0 ``/health`` probe plus the Phase 2 scan endpoints and
Phase 7 compliance endpoints. The ``backend/src`` directory is placed on ``sys.path``
(mirroring the test harness) so the modules there can be imported as top-level modules
whether the app is run from ``backend/`` (``uvicorn main:app``) or elsewhere.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC))

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from parser import MAX_FILE_SIZE
from routes import router as scans_router
from compliance.routes import router as compliance_router

app = FastAPI(title="CSPM API")

# CORS is off by default (secure). Phase 3 (React dashboard) runs on a different
# origin and the browser will block calls unless that origin is allowed here, so
# set CORS_ALLOW_ORIGINS (comma-separated, e.g. "http://localhost:5173") to opt
# in per environment. Credentials are allowed so Phase 3 can use httpOnly
# auth cookies once Phase 8 lands. Phase 8 tightens this to the deployed origin.
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

# Reject over-large bodies at the edge, before the multipart parser buffers the
# whole request into memory/disk. Allow modest overhead above the file cap for
# multipart boundaries and headers.
_MAX_REQUEST_BYTES = MAX_FILE_SIZE + 64 * 1024


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400, content={"detail": "Invalid Content-Length header."}
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


app.include_router(scans_router)
app.include_router(compliance_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report that the API process is ready to receive requests."""

    return {"status": "ok"}