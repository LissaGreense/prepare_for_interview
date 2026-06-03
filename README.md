# Interview Prep Quiz

A small, local, single-user quiz app for drilling topical knowledge before
technical interviews. Pick a topic, answer a randomized set of single-choice
questions, and review what you missed. Questions are plain JSON files on disk
that you own and edit.

- **Backend:** Python + FastAPI (reads questions from disk; no database)
- **Frontend:** Vue 3 + TypeScript + Vite + Pinia
- No accounts, no persistence — each run is a clean slate.

## Layout

```
backend/      FastAPI app + tests
frontend/     Vue 3 + TS SPA
questions/    your question bank — LOCAL ONLY, gitignored (see below)
docs/         design docs and UI design mockups
```

## The question bank is local

`questions/` is intentionally **gitignored** — it's your personal content, not
part of the repo. A fresh clone has no questions; add your own to populate the
app.

Each topic is a folder under `questions/`, each question is one JSON file, and
an optional `topic.json` manifest gives the topic its display card:

```
questions/
  python/
    topic.json            # optional display metadata
    gil.json              # one question per file
    decorators.json
```

**Question** (`python/gil.json`) — the filename is the question id, the folder
is the topic; neither is stored in the file:

```json
{
  "question": "What does CPython's GIL protect?",
  "options": [
    "Access to Python objects' reference counts",
    "The filesystem from concurrent writes",
    "GPU memory allocation",
    "Network sockets"
  ],
  "correct": 0,
  "explanation": "Optional; shown after you answer."
}
```

`correct` is the zero-based index of the right option. Options are shuffled in
the UI, so position doesn't give the answer away.

**Topic manifest** (`python/topic.json`, all fields optional):

```json
{ "title": "Python", "icon": "🐍", "description": "Core language and concurrency." }
```

Drop in a new file or folder and refresh — no restart needed. Malformed files
are skipped (logged), so one bad file never breaks a topic.

## Run it

**Backend** (port 8000):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --port 8000
```

**Frontend** (port 5173 — required):

```bash
cd frontend
npm install
npm run dev -- --port 5173 --strictPort
```

> The backend's CORS allowlist is pinned to `http://localhost:5173`, so the
> frontend must run on port 5173. `--strictPort` makes Vite fail loudly instead
> of silently picking another port.

Open <http://localhost:5173>.

## Tests

```bash
cd backend && pytest          # corpus + API behavior
cd frontend && npm test       # shuffle/remap + scoring
```
