"""FastAPI application entrypoint for the interview-prep quiz app."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .corpus import TopicNotFoundError, list_topics, load_quiz, select_questions
from .generation import service
from .models import Question, Topic

app = FastAPI(title="Interview Prep Quiz")

# Allow the Vite dev server to call the API cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns a static ok payload."""
    return {"status": "ok"}


@app.get("/topics")
def topics() -> list[Topic]:
    """Return every topic with its count of valid questions, read from disk."""
    return list_topics()


@app.get("/quiz")
def quiz(topic: str, count: int | None = None) -> list[Question]:
    """Return a topic's questions in random order, optionally capped at `count`.

    `count` omitted returns the whole topic shuffled; a `count` larger than the
    topic returns all of it. Unknown topic -> 404.
    """
    try:
        questions = load_quiz(topic)
    except TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {topic}") from None
    return select_questions(questions, count)


# --- AI question generator, Phase 1: interactive topic scoping ---------------


class StartScopeRequest(BaseModel):
    """Body for `POST /scope/start`."""

    root_topic: str


class ResumeScopeRequest(BaseModel):
    """Body for `POST /scope/{thread_id}/resume`."""

    selected: list[str] = []
    deeper_into: str | None = None


@app.post("/scope/start")
def scope_start(req: StartScopeRequest) -> service.ScopeState:
    """Begin scoping a broad topic; returns the first pick prompt."""
    return service.start(req.root_topic)


@app.post("/scope/{thread_id}/resume")
def scope_resume(thread_id: str, req: ResumeScopeRequest) -> service.ScopeState:
    """Resume a scoping session with the user's pick; returns next pick or scope."""
    try:
        return service.resume(thread_id, req.selected, req.deeper_into)
    except service.UnknownThreadError:
        raise HTTPException(
            status_code=404, detail=f"Unknown scope session: {thread_id}"
        ) from None


# --- AI question generator, Phase 2: generation ------------------------------


@app.post("/scope/{thread_id}/generate")
def scope_generate(thread_id: str) -> service.GenerationResult:
    """Generate and write questions from a finished scope; returns per-topic counts."""
    try:
        return service.generate(thread_id)
    except service.UnknownThreadError:
        raise HTTPException(
            status_code=404, detail=f"Unknown scope session: {thread_id}"
        ) from None
    except service.ScopeNotReadyError:
        raise HTTPException(
            status_code=409, detail="Scope is not finished yet; finish picking first."
        ) from None
