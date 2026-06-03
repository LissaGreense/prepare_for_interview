# prepare_for_interview

Local single-user interview-prep quiz app. FastAPI backend + Vue 3 frontend.
No DB, no auth — each run is ephemeral and reads quiz content from disk.

## Layout

```
backend/    Python 3.14 + FastAPI (app.main), Pydantic. Tests: pytest. Setuptools.
frontend/   Vue 3 + TS + Vite + Pinia. Tests: Vitest. Typecheck: vue-tsc.
questions/  Quiz content. GITIGNORED, local-only. folder = topic, one JSON file = one
            question, optional topic.json manifest.
```

## Commands

Backend (run from `backend/`, inside its `.venv`):

```bash
uvicorn app.main:app --reload --port 8000   # dev server on :8000
ruff check . && ruff format --check .        # lint + format check
mypy app tests                               # type check
pytest                                       # tests
```

Frontend (run from `frontend/`):

```bash
npm run dev -- --strictPort --port 5173      # MUST be 5173 (backend CORS is pinned to it)
npm run lint:check                           # eslint (report only)
npm run build                                # typecheck (vue-tsc) + bundle
npm test                                     # vitest
```

## Conventions

- Simple over complex, boring over clever. YAGNI. Don't abstract before the third use.
- Explicit over implicit; make impossible states impossible (discriminated unions, not
  optional grab-bags).
- Test behavior, not implementation. Mock only the network boundary (`fetch`). Use
  FastAPI `TestClient` + httpx on the backend.
- Frontend: server-state lives in Pinia; prefer string-literal unions over enums.

## Gotchas

- **Frontend dev port is load-bearing.** Backend CORS is pinned to
  `http://localhost:5173`. Always start Vite with `--strictPort --port 5173` — if the
  port drifts, the app silently can't call the API.
- **Backend runs in `backend/.venv`.** Activate it (or use the venv's interpreter)
  before `pytest`/`uvicorn`/`ruff`/`mypy`; don't run backend tooling from repo root.
- **`questions/` is gitignored, per-user content.** Never commit it; never assume its
  contents exist in CI. Code must handle an empty/missing topic gracefully.
