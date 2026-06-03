"""FastAPI application entrypoint for the interview-prep quiz app."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .corpus import TopicNotFoundError, load_quiz
from .models import Question

app = FastAPI(title="Interview Prep Quiz")

# Allow the Vite dev server to call the API cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns a static ok payload."""
    return {"status": "ok"}


@app.get("/quiz")
def quiz(topic: str) -> list[Question]:
    """Return all questions for a topic. Unknown topic -> 404."""
    try:
        return load_quiz(topic)
    except TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {topic}")
