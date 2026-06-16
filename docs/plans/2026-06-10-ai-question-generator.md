# AI Question Generator — Design & Findings

> Status: **Phase 1 complete** (all 4 slices: graph + real discovery + FastAPI bridge +
> Vue view). **Phase 2 (generation) iteration 1 complete and live-verified** — full
> wire-through built, tested (backend lint/format/mypy/pytest + frontend lint/build/vitest
> all green), and exercised end-to-end in the browser against LM Studio (`google/gemma-4-e4b`):
> topic "Redis" → 2 picks → docs fetched → 10 questions written and re-served via `/quiz`
> (2026-06-16). This doc captures the research, decisions, and build progress so the
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
3. **FastAPI interrupt bridge** — `POST /scope/start`, `POST /scope/{thread_id}/resume`
   (`service.py` + `test_scope_api.py`). ✅ done.
4. **Vue scoping view** — enter topic, render pick options, resume, loop to scope
   (`ScopeBuilder.vue` + `stores/scope.ts` + `api.ts`). ✅ done.

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

## Phase 2 — generation (first iteration)

Consume a Phase-1 `StudyScope` and write quiz questions to disk. The smallest honest
slice is a **straight pipeline, no LangGraph**: one structured LLM call per topic,
filter-validate, write files. (The generate→validate→**retry** loop is iteration 2.)

```
StudyScope ──► for each ScopeTopic ──► generate(doc_text) ──► validate ──► write
               (skip empty doc_text)   structured: N drafts   drop bad     questions/<slug>/<id>.json
```

### Pieces (`backend/app/generation/`)

- `generation.py` — schemas + the generator, mirroring `discovery.py`'s shape:
  - `QuestionDraft(BaseModel)`: `question`, `options: list[str]` (exactly 4),
    `correct: int` (0-based), `explanation: str`. Schema descriptions constrain the
    model; **no** `id`/`topic` (those are filesystem-derived per `models.py`).
  - `QuestionBatch(BaseModel)`: `{ questions: list[QuestionDraft] }` — one
    `structured(QuestionBatch).invoke(prompt)` call returns N at once, exactly like
    `SubtopicList`. Prompt is grounded in `topic.doc_text` (+ label, sources).
  - `generate_for_topic(topic: ScopeTopic, *, count: int = 5) -> list[QuestionDraft]`.
- `writer.py` — `write_questions(topic_slug, drafts, base=QUESTIONS_DIR) -> list[Path]`:
  one JSON file per draft at `questions/<topic_slug>/<id>.json` holding only the four
  content fields. Creates the folder; optionally drops a `topic.json` manifest from the
  topic label. Re-runnable.

### Locked-in calls for iteration 1

- **One call per topic** returning a batch (not N single calls) — established precedent,
  cheaper, and the grammar-constrained `json_schema` method holds structure on small
  local models.
- **4 options, fixed.** Constrain in the schema; validate `len == 4`.
- **Validation = filter, not retry.** Reuse the `Question` model_validator
  (`0 <= correct < len(options)`); drop+log invalid drafts, just like `corpus._read_question`
  skips malformed files. Auto-retry on failure is **iteration 2** (the LangGraph upgrade).
- **Stable id = short content hash** (e.g. `sha1(question)[:8]`) — idempotent: re-running
  the same scope won't duplicate files; near-identical questions self-dedupe.
- **Empty `doc_text` ⇒ skip the topic with a warning** (fetch failures leave it `""`;
  generating from a label alone is pure hallucination — not worth shipping in iter 1).
- **Validation = structural only** (the `Question` validator). A wrong-but-in-range
  `correct` slips through; that's an iteration-2 quality concern, not a blocker.
- **Entry point = full wire-through**: functions → `POST /scope/{thread_id}/generate`
  → a "Generate from this scope" button in `ScopeBuilder.vue`. End-to-end in iter 1.

### Build order (iteration 1) — ✅ all done

1. `generation.py` — `QuestionDraft` / `QuestionBatch` + `generate_for_topic`; offline unit tests (`test_generation.py`). ✅
2. `writer.py` — `write_questions(...)`, sha1 content-hash ids, idempotent, round-trips through `corpus` (`test_writer.py`). ✅
3. `service.generate(thread_id)` — reads the done `StudyScope` from graph state, generates per topic, writes, returns `GenerationResult`. `UnknownThreadError` (404) vs `ScopeNotReadyError` (409). ✅
4. `POST /scope/{thread_id}/generate` — thin handler; `test_scope_api.py` covers success + 404 + 409. ✅
5. Vue: `generated` phase + `generate()` action in `scope.ts`, `generateScope` in `api.ts`, "Generate questions" button + summary screen in `ScopeBuilder.vue`. ✅

**Live-verified (2026-06-16):** ran end-to-end in the browser against LM Studio
(`google/gemma-4-e4b`) — "Redis" → picked 2 subtopics → docs fetched (5.8k / 7.1k chars)
→ 10 questions written to `questions/<slug>/<sha1>.json` (5 per topic), all structurally
valid (4 options, `correct` in range), and re-served through `/topics` + `/quiz`. One
caveat surfaced (an iteration-2 concern, not a wire-through bug): DuckDuckGo can land a
topic on an off-topic doc — "Core Data Structures and Operations" pulled an unrelated
enterprise-architecture page, so its questions are grounded but off-Redis. The pub/sub
topic fetched correctly and produced accurate questions.

### Deliberately deferred to iteration 2+

- generate→validate→**retry** LangGraph loop (auto-correct a bad `correct` index or a
  short batch) instead of dropping.
- Semantic quality: a wrong-but-in-range `correct`, duplicate options, or off-topic
  questions pass the structural validator. Needs an LLM-judge or self-critique pass.
- Difficulty levels / question-type mix (MCQ only for now).

## Known rough edges / deferred

- **Verbose labels** — small local models emit `"API Design and Development (REST
  principles, DRF)"` rather than a tight `"API Design"`. A prompt tweak fixes it.
- **`langchain-community` deprecation warning** — "being sunset"; works fine. Migration
  path is the standalone integration packages if it ever matters.
```
