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

- `@step(output=...)` — decorator turning a prompt function into a typed, callable LLM step.
- `@flow` — thin wrapper giving explicit flows a context for tracing and config injection.
- `Client` — provider-agnostic LLM interface (instructor-backed real clients + a `FakeClient` for tests).

Non-goals: graph DSLs, YAML pipelines, node-based editors, hidden reactivity. If it can be a Python function, it is one.

## Layout

```
src/pyxis/        library code
  step.py         @step decorator + Step primitive
  flow.py         @flow decorator + run context
  client.py       Client protocol + instructor-backed impl + FakeClient
tests/            pytest suite (uses FakeClient, no network)
specs/            SDD specs — one markdown file per primitive/iteration
examples/         runnable demos
```

## Dev workflow

- Package manager: **uv** (`uv sync`, `uv run`). Never use pip directly.
- Lint/format: **ruff** (`uv run ruff check`, `uv run ruff format`).
- Tests: **pytest** (`uv run pytest`). All tests must pass without network.
- Python: **3.12+**.

## Iteration methodology: SDD + TDD

Each iteration lands as **one commit** shaped like:

1. Write `specs/NNN-<name>.md` — short spec: purpose, API sketch, acceptance criteria.
2. Write failing tests in `tests/` that reflect the spec.
3. Implement until tests pass.
4. Run `uv run ruff format && uv run ruff check && uv run pytest`.
5. Commit with message referencing the spec.

Specs are contracts, not design docs. Keep them under ~40 lines; if a spec grows, split the iteration.

## Testing contract

Tests never hit a real LLM. The `FakeClient` returns canned Pydantic instances keyed by `(response_model, call_index)`. If you need to assert prompt content, capture it via the fake's `.calls` log.
