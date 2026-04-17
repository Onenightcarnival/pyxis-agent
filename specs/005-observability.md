# 005: Observability — retry + usage + trace export

## Purpose

Production use needs three knobs that share infrastructure:
- **retry** on structured-output validation failure (instructor handles the
  mechanics; we surface the knob at the `@step` level);
- **token usage** captured per LLM call so cost tracking works;
- **structured trace export** so logs can carry a full run.

All three touch `TraceRecord` and the `Client` protocol's return type, so
they land together.

## API sketch

```python
from pyxis import step, trace, Usage

@step(output=Plan, max_retries=2)
def plan(req: str) -> str:
    """..."""
    return req

with trace() as t:
    plan("x")

rec = t.records[0]
assert rec.usage is None or isinstance(rec.usage, Usage)

# serialize for logs
t.to_dict()                # {"records": [{"step": ..., "output": {...}, ...}]}
t.to_json(indent=2)        # str
t.total_usage()            # Usage(prompt_tokens=..., ...)
```

## Acceptance criteria

- `Usage` is a `@dataclass` with `prompt_tokens: int = 0`, `completion_tokens: int = 0`, `total_tokens: int = 0`.
- `CompletionResult[T]` is a `@dataclass` with `output: T`, `usage: Usage | None = None`.
- `Client.complete` and `AsyncClient.acomplete` now return `CompletionResult[T]` and accept `max_retries: int = 0`.
- `InstructorClient` uses `create_with_completion` on both sync/async paths;
  extracts `Usage` from the raw response's `.usage` when present; forwards `max_retries`.
- `FakeClient` accepts optional parallel `usages: Iterable[Usage | None]`;
  `FakeCall` gains `max_retries: int`.
- `@step(..., max_retries=N)` forwards N to the client; default is 0.
- `TraceRecord` gains `usage: Usage | None = None`; populated from the client result.
- `Trace.to_dict() -> dict`, `Trace.to_json(**json_kwargs) -> str`,
  `TraceRecord.to_dict() -> dict`. Output models serialize via `model_dump(mode="json")`.
- `Trace.total_usage() -> Usage` sums all non-None usages; returns a zero `Usage` if none were captured.

## Non-goals (deferred)

- Currency cost estimation.
- Streaming usage updates.
- Redacting sensitive content on export (post-process `to_dict()` yourself).
