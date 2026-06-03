# Interview Prep Quiz — Design

**Date:** 2026-06-03
**Status:** Approved design, pre-implementation

## Problem Statement

When preparing for technical interviews, I want to drill myself on topical
knowledge (Python, SQL, etc.) by answering practice questions and immediately
seeing whether I was right and why. I don't have a lightweight, local tool for
this that I fully control and can grow my own question bank in.

## Solution

A local, single-user quiz app. I pick a topic, get a randomized set of
single-choice questions, answer them, and see my score plus explanations for
each. Questions live as plain JSON files on disk that I can edit by hand or,
later, generate automatically. Each run is a clean slate — no accounts, no
saved history, no setup beyond starting the app.

## User Stories

1. As a user, I want to see the list of available topics, so that I can choose
   what to study.
2. As a user, I want to see how many questions each topic has, so that I can
   judge whether it's worth drilling.
3. As a user, I want to pick a topic and start a quiz, so that I can begin
   practicing immediately.
4. As a user, I want to optionally choose how many questions to answer, so that
   I can do a quick 5-question drill or an exhaustive run.
5. As a user, I want the questions to come in a randomized order each run, so
   that I'm not memorizing sequence instead of content.
6. As a user, I want the answer options shuffled in the UI, so that the correct
   answer isn't always in the same position and I can't memorize by position.
7. As a user, I want to select one answer per question, so that the interaction
   is simple and unambiguous.
8. As a user, I want to see immediately whether my answer was right or wrong, so
   that I get tight feedback.
9. As a user, I want to read an explanation after answering (when one exists),
   so that I understand the reasoning, not just the right letter.
10. As a user, I want a final score and a list of which questions I missed, so
    that I know where I'm weak.
11. As a user, I want each run to be independent (refresh = fresh), so that I
    don't have to manage saved state or accounts.
12. As a user, I want to add a new question by dropping a JSON file into a topic
    folder, so that growing the bank requires no code changes or restarts.
13. As a user, I want a malformed question file to be skipped (not crash the
    whole quiz), so that one bad file doesn't block my study session.
14. As a user, I want a clear error if I request a topic that doesn't exist, so
    that I understand what went wrong.
15. As a future capability, I want to generate new questions for a topic
    automatically, so that I can expand the bank without writing every question
    by hand. (Out of scope for this iteration — see below.)

## Implementation Decisions

### Stack

- **Backend:** Python + FastAPI, served via Uvicorn.
- **Frontend:** Vue 3 + TypeScript + Vite, Pinia for in-memory quiz state.
- **Persistence:** none. The filesystem (`questions/`) is the only data store.
- **Explicitly cut:** Redis, any database, auth, server-side sessions. The app
  is local, single-user, and ephemeral, so none of these earn their place.

### Project layout

```
prepare_for_interview/
  questions/                 # source of truth, git-tracked
    python/
      gil.json
    sql/
      window-functions.json
  backend/
    app/
      main.py                # app + routes
      corpus.py              # read questions/ from disk
      models.py              # Pydantic: Question, Topic
    pyproject.toml
  frontend/
    src/
      api.ts                 # typed client for backend
      types.ts               # Question type, mirrors backend
      views/
        TopicPicker.vue
        Quiz.vue
        Results.vue
      stores/quiz.ts         # Pinia: current quiz, answers, score
```

### Question file schema

One question per file. The filename is the question id; the parent folder is the
topic. Neither id nor topic is stored inside the file — the filesystem already
encodes them, and duplicating them invites drift.

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
  "explanation": "The GIL serializes access to interpreter state, notably refcounts."
}
```

- `options` is an ordered array (JSON arrays are ordered by spec).
- `correct` is a zero-based index into `options`. Order is therefore
  load-bearing in the file — editing option order requires updating `correct`.
- `explanation` is optional.

### Reading strategy

The backend reads from disk **per request**, not cached at startup. Files are
few and tiny, so cost is negligible, and newly added (or generated) question
files appear immediately with no restart. The backend holds no state between
requests.

### API contract

| Endpoint | Returns |
|---|---|
| `GET /topics` | `[{ "topic": "python", "count": 12 }, ...]` |
| `GET /quiz?topic=python&count=10` | array of questions (see below) |

Quiz question shape returned to the client:

```json
{
  "id": "gil",
  "topic": "python",
  "question": "...",
  "options": ["...", "..."],
  "correct": 0,
  "explanation": "..."
}
```

- `count` is optional; omitting it returns all questions in the topic.
- Question order is randomized server-side.
- Per the grading decision below, the full question — including `correct` — is
  sent to the client.
- Unknown topic → `404` with a clear message.
- `count` greater than available → return what exists (not an error).

### Grading decision (frontend grades)

Grading happens on the **frontend**. The backend ships full questions including
the `correct` index; Vue compares the user's choice locally and reveals the
explanation.

Accepted trade-off: this makes the backend's *serving* responsibility a thin
file server that hides little. It is acceptable because (a) the app is a personal
study tool where cheating is moot, and (b) the backend still earns its place as
the server-side home for the future generation feature.

### Option shuffling (frontend only)

Options are shuffled at display time in Vue, never in the stored file. Because
`correct` is an index, the shuffle and the index remap must happen as one
operation:

```ts
const order = shuffle([0, 1, 2, 3]);
const options = order.map(i => q.options[i]);
const correct = order.indexOf(q.correct);
```

The stored JSON remains canonical; shuffling is purely a view concern and the
data layer is unaware of it.

### Module Boundaries

**`corpus.py` — corpus reader**

- **Interface:** `list_topics() -> list[Topic]`, `load_quiz(topic, count) ->
  list[Question]`.
- **Hides:** the on-disk layout (folder = topic, filename = id), how files are
  walked, how malformed files are skipped, how questions are randomized and
  truncated to `count`, and how id/topic are derived from paths.
- **Trust contract:** callers get validated `Question` objects with id and topic
  populated; they never touch the filesystem or parse JSON themselves. A bad
  file never reaches the caller — it is skipped at read time.

**Frontend `stores/quiz.ts` — quiz state + grading**

- **Interface:** current quiz, record-answer action, derived score/results.
- **Hides:** how answers are tracked, how the score is computed, the
  shuffle+remap of options.
- **Trust contract:** views read reactive quiz state and call actions; they do
  not implement grading or shuffling themselves.

### Data Isolation

Not applicable — no database, no user-scoped tables.

## Testing Decisions

A good test here exercises external behavior, not internals: it drives the real
HTTP API or the real store action and asserts on observable results, mocking
only at genuine boundaries.

### Backend

- Point the corpus reader at a small fixture `questions/` directory containing
  real files (the filesystem is the boundary worth exercising — no mocking it).
- Use FastAPI `TestClient` for real HTTP round-trips, no internal mocking.
- Cases:
  - `GET /topics` enumerates topics and counts correctly from fixtures.
  - A deliberately malformed fixture file is skipped, not fatal; the rest of the
    topic still loads.
  - `GET /quiz` returns the documented shape and respects `count` (including
    `count` larger than available → returns all).
  - Unknown topic → `404`.

### Frontend

- Unit-test the **shuffle + remap** with a fixed permutation: after shuffling,
  `correct` still points at the same option text. This is the highest bug-risk
  code in the app (index math) and gets a dedicated test.
- Unit-test the **scoring** function against a known set of answers.
- Skip testing Vue render plumbing and component wiring.

## Out of Scope

- **Question generation from topics.** This is the planned next iteration:
  generate new question JSON files for a topic (likely via an LLM call) and write
  them into the topic directory. The current serving/grading path requires no
  changes to support it — generated files are read like any other. Design for
  this lands in a separate PRD.
- Progress tracking, history, scores over time, spaced repetition.
- Multi-choice, multiple-correct, or free-text questions.
- Authentication, multi-user support, deployment to a shared/public host.
- Editing questions through the UI.

## Further Notes

- The whole system is deliberately stateless and storage-free. If a future need
  (e.g. progress tracking) genuinely requires persistence, SQLite is the first
  thing to reach for — not Redis or a server DB.
- Keep the question JSON minimal and filesystem-derived (no embedded id/topic)
  to avoid drift between file location and file contents.
