# pyxis-agent

Agent framework built around **declarative chain-of-thought** as its organizing philosophy.

## Core philosophy

```
declarative CoT = code as prompt + schema as workflow
```

- **Code as prompt**: a Python function's docstring is the system prompt; its return value is the user message. The function *is* the prompt.
- **Schema as workflow**: a Pydantic output model's field order *is* the chain of thought — the LLM must fill it top-to-bottom, so the schema literally declares the reasoning steps.

## Two orchestration layers

| Scope | Mechanism | Responsibility |
|-------|-----------|----------------|
| **Implicit** (single LLM call) | `instructor` + Pydantic field order | Chain-of-thought *inside* one call |
| **Explicit** (multi LLM call) | Plain Python code | Composition, branching, looping *across* calls |

The framework intentionally refuses to invent a DSL for explicit orchestration — Python already has `if`, `for`, and functions. We only supply:

- `@step(output=...)` — decorator turning a prompt function into a typed, callable LLM step. Sync `def` → `Step[T]`; async `async def` → `AsyncStep[T]`.
- `@flow` — thin wrapper giving explicit flows a `.run_traced(...)` convenience. Same sync/async dispatch.
- `Tool` — `BaseModel` subclass with `run() -> str`. Actions are schemas; `run()` is the code. The LLM emits a tool by filling a discriminated-union `action` field; Python dispatches via `isinstance` / `action.run()`.
- `Client` / `AsyncClient` — provider-agnostic LLM interfaces returning `CompletionResult[T]` (output + optional `Usage`). Instructor-backed real client; `FakeClient` for tests.
- `trace()` + `TraceRecord` — `ContextVar`-based observability that works across asyncio tasks. Records carry `usage`; `Trace.to_dict()` / `to_json()` / `total_usage()` for export.
- `@step(..., max_retries=N)` forwards a retry budget to instructor for structured-output validation failures.

Non-goals: graph DSLs, YAML pipelines, node-based editors, hidden reactivity, function-calling adapters, agent-loop helpers. If it can be a Python function, it is one.

## Layout

```
src/pyxis/        library code
  step.py         Step / AsyncStep + @step decorator
  flow.py         Flow / AsyncFlow + @flow decorator
  tool.py         Tool base class
  trace.py        Trace / TraceRecord + trace() context manager
  client.py       Client + AsyncClient protocols, CompletionResult, Usage,
                  FakeClient, InstructorClient
tests/            pytest suite (uses FakeClient, no network)
tests/integration/ live LLM smoke tests — require OPENROUTER_API_KEY
specs/            SDD specs — one markdown file per primitive/iteration
examples/         runnable demos against OpenRouter
```

## Dev workflow

- Package manager: **uv** (`uv sync`, `uv run`). Never use pip directly.
- Lint/format: **ruff** (`uv run ruff check`, `uv run ruff format`).
- Tests: **pytest** (`uv run pytest`). Unit tests must pass without network.
- Integration: `uv run --env-file .env pytest tests/integration/` (needs `OPENROUTER_API_KEY`).
- Python: **3.12+**. Use PEP 695 generics (`class Foo[T: Base]`, `def f[T: Base]`).
- Keep CLAUDE.md synced with every feature iteration.

## Iteration methodology: SDD + TDD

Each iteration lands as **one commit** shaped like:

1. Write `specs/NNN-<name>.md` — short spec: purpose, API sketch, acceptance criteria, non-goals.
2. Write failing tests in `tests/` that reflect the spec.
3. Implement until tests pass.
4. Run `uv run ruff format && uv run ruff check && uv run pytest`.
5. Run the integration suite with a key when touching Client, Step, or provider wiring.
6. Update CLAUDE.md and README if the public surface changed.
7. Commit with a message referencing the spec.

Specs are contracts, not design docs. Keep them under ~40 lines; if a spec grows, split the iteration.

## Testing contract

Unit tests never hit a real LLM. The `FakeClient` returns queued Pydantic instances in order (same queue for sync and async paths), records every call in `.calls`, and raises on exhaustion or type mismatch. If you need to assert prompt content, capture it via the fake's `.calls` log. Integration smoke tests live under `tests/integration/` and self-skip when the env var is absent.
