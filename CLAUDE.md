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

## Working with Claude

- **When you correct a recurring mistake, write the fix down — don't just re-prompt.**
  Project rules go in this file; session/task notes go in auto-memory. A correction
  given only in chat fixes one run; a correction written down fixes every future run.
  Keep this file short — add a rule only after the same mistake recurs, and prune stale
  ones.
- **New task → `/clear` and write a fresh brief. Related follow-up → `/compact <hint>`**
  naming what to keep (e.g. "focus on the generation pipeline, drop scope-API debugging").
- **Kick off real tasks with Goal / Constraints / Acceptance criteria** so Claude plans
  the whole problem instead of guessing.
- **`.claude/` is committed Claude tooling** (see below) — treat it as project code.
  - `commands/` — `/check` (full CI-equivalent gate) and `/test` (fast loop). They encode
    the `backend/.venv` and `:5173` gotchas so they don't get re-learned.
  - `agents/code-reviewer.md` — read-only pre-PR review agent wrapping the vendored skill.
  - `settings.json` — committed permission allowlist for safe everyday commands.
    `settings.local.json` is personal/gitignored.
  - `skills/<skill>` is a **symlink** into `.agents/skills/<skill>` (the canonical
    vendored files); `skills-lock.json` pins the source + hash. Don't "tidy up" the
    symlink — it's how Claude Code discovers the skill.
