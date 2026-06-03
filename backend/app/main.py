"""FastAPI application entrypoint for the interview-prep quiz app."""

from fastapi import FastAPI

app = FastAPI(title="Interview Prep Quiz")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns a static ok payload."""
    return {"status": "ok"}
