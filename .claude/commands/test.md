---
description: Run backend + frontend tests (fast loop)
argument-hint: "[optional pytest -k filter]"
---

Run the test suites. If `$ARGUMENTS` is given, forward it to pytest as a `-k` filter.

- `cd backend && .venv/bin/pytest $ARGUMENTS`   # backend runs in its .venv
- `cd frontend && npm test`

Report failures only — full output for anything red, one line per green suite.
