# AI Question Generator — Design & Findings

> Status: **in progress.** Phase 1 (interactive topic scoping) backend complete and
> verified live. This doc captures the research, decisions, and build progress so the
> feature can be resumed cold.

## Goal

Add an AI question generator to the local interview-prep quiz app. A broad topic
("web development") is interactively narrowed — with the user picking subtopics and
drilling deeper — into a curated set of leaf topics, each backed by fetched
documentation. That scope then feeds question generation (Phase 2).

Built in two phases:

- **Phase 1 — interactive topic scoping** *(this work).* Output: a `StudyScope`.
- **Phase 2 — generation** *(not yet designed).* Consume one `ScopeTopic` at a time,
  emit questions in the on-disk shape `{ question, options[], correct, explanation }`.

## Why LangGraph (and when it would be overkill)

Research (official docs at docs.langchain.com) was unambiguous: for a **single** LLM
call that returns structured JSON, LangGraph is overkill — a plain LCEL chain
(`model.with_structured_output(Schema)`) is right-sized. The stack hierarchy is
LCEL → prebuilt agent → LangGraph (lowest-level, most control).

Phase 1 is **not** a single call. It is four things at once, and LangGraph has a
named primitive for each:

| Requirement | LangGraph primitive |
|---|---|
| topic tree + picks + docs persist across turns | `StateGraph` + checkpointer (`MemorySaver`) + `thread_id` |
| "ask the user to pick" pauses the run | `interrupt(payload)` → `Command(resume=…)` |
| "drill deeper, ask again" loop | `add_conditional_edges` (cyclic), bounded by `recursion_limit` |
| fetch docs for N picks in parallel | `Send("fetch_docs", …)` + accumulating reducer |

The Vercel AI SDK gives tool-loops but no checkpointed pause/resume and no graph
cycles — that is the gap LangGraph fills here.

### Hard LangGraph requirements (from official docs)

- `interrupt()` **requires** a checkpointer + a `thread_id` in config; reuse the same
  `thread_id` on resume.
- Never wrap `interrupt()` in try/except — it raises `GraphInterrupt` as control flow.
- Logic **before** `interrupt()` must be idempotent (the node replays from the top on
  resume).
- Parallel `Send` results must merge via a reducer (`Annotated[list, operator.add]`),
  not overwrite.
- Bound the deepen loop with `recursion_limit` / a depth cap.

## Locked decisions

- **LLM provider: env-driven factory, swappable with no graph change** (`llm.py`).
  - **Default (dev/testing): local LM Studio** — OpenAI-compatible at
    `http://localhost:1234/v1`, free. Verified working with a small (~7B-class)
    local model: it returns schema-valid structured output via
    `response_format: json_schema` (LM Studio grammar-constrains, so structure
    holds even on a small model). Uses `with_structured_output(Schema,
    method="json_schema")`. Set `QUIZGEN_LLM_MODEL` to whatever model id you have
    loaded.
  - **Quality option: Anthropic Claude** — set `QUIZGEN_LLM_PROVIDER=anthropic`
    (+ `ANTHROPIC_API_KEY`). Uses `method="function_calling"`.
- **Search: DuckDuckGo** (`DuckDuckGoSearchResults`, package `ddgs`) — free, **no API
  key**, returns result `link` URLs for doc fetching. Risk: undocumented rate limits
  (fine at single-user volume; `_search` adds linear backoff). Rejected Brave/Tavily
  (both need a key; Brave also needs a card).
- **Interrupt UI: Vue frontend** (not CLI) — FastAPI bridge endpoints + per-session
  `thread_id`.
- **Deepen loop: user-driven, hard cap 3 levels** (`MAX_DEEPEN_LEVELS`).

## The scoping graph

```
            START
              │
              ▼
        ┌──────────┐      ┌──────────┐   deeper=True ──┐  (loop back, cursor=picked node)
        │  expand  │─────▶│   pick   │─────────────────┘
        └──────────┘      └──────────┘
        search + LLM      interrupt() ⇧ pauses
        → child topics    Command(resume) ⇩          deeper=False
                                │  conditional edge → list[Send] (fan out per leaf)
                                ▼
                   ┌────────────────────────┐
                   │  fetch_docs  (×N)       │  one Send per picked leaf,
                   │  DDG → WebBaseLoader    │  results append via operator.add
                   └───────────┬─────────────┘
                               ▼
                         ┌──────────┐
                         │ assemble │ → StudyScope
                         └────┬─────┘
                              ▼  END
```

Selection semantics: at each frontier the user picks a set and may "go deeper" into
one. Picks that aren't deepened become final **leaves** and accumulate across levels;
the deepened pick's children become the next frontier. The deepened node is itself
**not** a leaf.

## StudyScope (Phase-1 output → Phase-2 input)

```json
{
  "root_topic": "Python backend development",
  "topics": [
    { "id": "web-frameworks", "label": "Web Frameworks (Django/Flask)",
      "doc_text": "…fetched, chunked documentation…",
      "sources": ["https://pypi.org/project/Flask/", "…"] }
  ]
}
```

## Module layout (`backend/app/generation/`)

- `llm.py` — `get_chat_model()` + `structured(schema)` factory (LM Studio / Anthropic).
- `discovery.py` — `default_expand` (DDG-grounded LLM → `TopicNode`s with slug ids) and
  `default_fetch` (DDG → `WebBaseLoader` → chunked, capped, failure-tolerant). Plus the
  `Subtopic`/`SubtopicList` structured-output schemas and `_slugify`.
- `scoping.py` — the graph. `TopicNode`/`FetchedDoc` (TypedDicts), `ScopeTopic`/
  `StudyScope` (Pydantic), `ScopingState`, `build_scoping_graph(expand_fn?, fetch_fn?)`.
  Discovery is **injected** so the graph mechanics test offline; defaults are the real
  search+LLM+fetch functions (lazy-imported to avoid a cycle).
- `service.py` — thin HTTP-facing wrapper: `start(root_topic)` / `resume(thread_id, …)`,
  returning a `ScopeState` discriminated union (`awaiting_pick` | `done`). *(Slice 3.)*

Dependencies live in the `gen` optional extra (`pip install -e ".[gen]"`): `langgraph`,
`langchain-openai`, `langchain-anthropic`, `langchain-community`,
`langchain-text-splitters`, `ddgs`, `beautifulsoup4`.

## Build slices

1. **Core scoping graph loop** — `expand → pick(interrupt) → [deeper|assemble]`,
   hardcoded `expand`. Proves checkpointer + interrupt + resume + cyclic edge + cap.
   ✅ done.
2. **Real expand + fetch_docs fan-out** — Claude/LM Studio + DDG; `Send` fan-out;
   `StudyScope`. ✅ done, verified live (see below).
3. **FastAPI interrupt bridge** — `POST /scope/start`, `POST /scope/{thread_id}/resume`.
   *(in progress)*
4. **Vue scoping view** — enter topic, render pick options, resume, loop to scope.
   *(in progress)*

## Live verification (Slice 2, local model)

```
>> expanding 'Python backend development' (LM Studio)...
   discovered 5 sub-areas in 5.6s:
     - [technology] Web Frameworks (Django/Flask)
     - [subtopic ] API Design and Development (REST principles, DRF)
     - [technology] Database Interaction (SQLAlchemy/ORM usage)
     - [subtopic ] Asynchronous Programming & Concurrency
     - [technology] Containerization and Deployment (Docker, …)
>> picking 2 leaves, fetching docs (DDG + WebBaseLoader)...
   built StudyScope in 2.7s
     - web-frameworks  doc=7438 chars  sources=[pypi.org/project/Flask, jetbrains.com/…]
     - api-design      doc=6050 chars  sources=[learn.microsoft.com/…/api-design, …]
```

## Running it locally

LM Studio (free, default) — start the server and load any chat model:

```bash
lms server start
lms load <your-model-id>      # then: lms ps  to see the served id
```

Backend (from `backend/`, inside `.venv`):

```bash
pip install -e ".[dev,gen]"
export QUIZGEN_LLM_MODEL="<your-loaded-model-id>"   # required for lmstudio
uvicorn app.main:app --reload --port 8000
```

To use Claude instead: `export QUIZGEN_LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=…`.

## Known rough edges / deferred

- **Verbose labels** — small local models emit `"API Design and Development (REST
  principles, DRF)"` rather than a tight `"API Design"`. A prompt tweak fixes it.
- **`langchain-community` deprecation warning** — "being sunset"; works fine. Migration
  path is the standalone integration packages if it ever matters.
- **Phase 2 (generation)** — not designed. Smallest core is a plain
  `model.with_structured_output(QuestionDraft)` chain; a generate→validate→retry
  LangGraph loop is the upgrade for auto-retry on the `0 <= correct < len(options)`
  invariant.
- **`questions/` write path** — generated questions will land in
  `questions/<topic>/<id>.json` (gitignored, local-only). Not built yet.
```
