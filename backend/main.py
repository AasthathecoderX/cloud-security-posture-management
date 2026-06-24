"""Minimal API entry point used to verify the Phase 0 environment."""

from fastapi import FastAPI

app = FastAPI(title="CSPM API")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report that the API process is ready to receive requests."""

    return {"status": "ok"}
