# Roadmap

Features intentionally **deferred** so the surface stays aligned with the
core thesis (`code as prompt + schema as workflow`) and the iteration budget
stays sane. Each item is a future spec iteration — add `specs/NNN-*.md`
when you pick one up.

## Near-term candidates

- **Streaming** — token-by-token schema population via `instructor`'s
  partial streaming; trace records emit progressively.
- **Retry backoff + error visibility** — expose validation errors on
  `TraceRecord` when retries are exhausted; add optional exponential
  backoff between retries.
- **Tool decorator sugar** — `@tool` that generates a `Tool` subclass from
  a plain function signature + docstring (auto-derived Pydantic fields).
- **Provider convenience factories** — `openrouter_client(api_key=...)`,
  `anthropic_client(...)` that return a ready `InstructorClient`. Keep
  the framework provider-agnostic; factories are opt-in sugar.
- **Typed `@step` overloads** — `@overload` pair so mypy/pyright infer
  `Step[T]` vs `AsyncStep[T]` at the call site without `Any` leakage.

## Medium-term

- **Cost estimation** — optional per-model rate table -> currency.
- **Trace persistence** — JSONL sink for shipping traces to files / log
  collectors / OpenTelemetry.
- **Parallel step helpers** — `@flow` utilities for fan-out/gather
  ergonomics beyond what `asyncio.gather` already gives.
- **Persistent memory** — conversation-history helpers (still just
  arguments passed in; no hidden state).
- **CLI** — `pyxis run path/to/flow.py` with env-file support, dry-run,
  and trace-as-JSON output.

## Intentionally not on the roadmap

These would violate the core thesis. Don't add them:

- Graph/DAG DSL for flows. Python already composes functions.
- YAML pipeline configs. Python already composes functions.
- Function-calling protocol adapters baked into the framework. The
  output schema *is* the interface; users wanting provider function
  calling can use instructor directly.
- Hidden reactive state or global mutable agent context. Pass arguments.
- Agent-loop helpers that hide the loop. The loop is the user's `@flow`.

## Contributing an iteration

1. Pick an item. Open a branch.
2. Write `specs/NNN-<name>.md` (≤ 40 lines, acceptance criteria, non-goals).
3. Write failing tests first.
4. Implement.
5. `uv run ruff format && uv run ruff check && uv run pytest`.
6. If touching `Client` or Step/Flow wiring, run
   `uv run --env-file .env pytest tests/integration/`.
7. Update `CLAUDE.md` and `CHANGELOG.md`.
8. One commit per iteration; message references the spec.
