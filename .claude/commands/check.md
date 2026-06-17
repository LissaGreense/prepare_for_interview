---
description: Run all quality gates (backend + frontend), matching CI
---

Run the full quality gate, same checks CI enforces. Report failures concisely with
the relevant output; do not fix anything unless I ask.

Backend (must run inside `backend/.venv` — use the venv interpreter, never repo root):

- `cd backend && .venv/bin/ruff check .`
- `cd backend && .venv/bin/ruff format --check .`
- `cd backend && .venv/bin/mypy app tests`
- `cd backend && .venv/bin/pytest`

Frontend:

- `cd frontend && npm run lint:check`
- `cd frontend && npm run build`   # vue-tsc typecheck + bundle
- `cd frontend && npm test`

Run them all even if an earlier one fails, then summarize which passed and which failed.
