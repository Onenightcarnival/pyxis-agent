# Changelog

All notable changes to pyxis-agent are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project tries to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-04-18

First feature-complete release. Seven SDD+TDD iterations on top of `main`.

### Added

- **Tool primitive** — `Tool(BaseModel)` subclass with `run() -> str` for
  declarative-CoT tool use. Tools participate in discriminated unions on a
  Step's output schema; Python dispatches by type.
  ([spec 003](specs/003-tool.md))
- **Async support** — `@step` / `@flow` detect `async def` and dispatch to
  `AsyncStep` / `AsyncFlow`. `AsyncClient` protocol sibling to `Client`;
  `FakeClient` and `InstructorClient` implement both. Trace `ContextVar`
  propagates across `asyncio.gather`.
  ([spec 004](specs/004-async.md))
- **Observability** — `Usage` dataclass + `CompletionResult[T]` wrapping the
  Client protocol's return; `@step(..., max_retries=N)` forwarded to
  instructor's validation retries; `TraceRecord.usage` populated per call;
  `Trace.to_dict()` / `to_json()` / `total_usage()` for structured export
  and cost aggregation. `InstructorClient` extracts usage via
  `create_with_completion`.
  ([spec 005](specs/005-observability.md))

### Changed

- `Client.complete` / `AsyncClient.acomplete` now return `CompletionResult[T]`
  instead of the bare model, and accept a `max_retries` kwarg. External
  clients implementing the protocol must update. (Pre-1.0 breaking change.)
- `FakeClient` constructor takes an optional `usages=` parallel list.
- `FakeCall` gains `max_retries: int` for test assertions on forwarding.

### Verified against real LLM

Four live smoke tests through OpenRouter (`openai/gpt-5.4-nano`):
single step, multi-step flow with trace, concurrent `asyncio.gather`,
and token-usage capture.

## [0.1.0] — 2026-04-18

Initial MVP. Declarative chain-of-thought philosophy in code.

### Added

- **`Step`** — `@step(output=M)` decorator. Docstring = system prompt;
  string return = user message; Pydantic field order = implicit CoT.
  ([spec 001](specs/001-step.md))
- **`Flow`** — `@flow` wrapper + `.run_traced(...)` for explicit multi-call
  orchestration in plain Python. No DSL.
  ([spec 002](specs/002-flow.md))
- **`trace()`** context manager + `TraceRecord` captured via `ContextVar`.
- **`Client`** protocol with `FakeClient` (tests, no network) and
  `InstructorClient` (production, OpenAI-compatible via instructor).
- SDD+TDD iteration protocol (`specs/NNN-*.md` + failing tests first + ruff
  + pytest gate + one commit per iteration).
- uv project layout with ruff + pytest + mypy configured.
