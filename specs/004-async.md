# 004: Async support — mirror the sync path into asyncio

## Purpose

Production agents are IO-bound. Every primitive gains an async sibling that
follows exactly the sync semantics, dispatched by detecting coroutine
functions at decoration time. The trace `ContextVar` already works across
asyncio tasks that inherit context — no trace API change.

## API sketch

```python
import asyncio
from pydantic import BaseModel
from pyxis import FakeClient, flow, step, trace

class Analysis(BaseModel):
    observation: str
    conclusion: str

fake = FakeClient([Analysis(observation="o", conclusion="c")])

@step(output=Analysis, client=fake)
async def analyze(text: str) -> str:
    """Analyze asynchronously."""
    return text

@flow
async def research(topic: str) -> Analysis:
    return await analyze(topic)

async def main():
    result, t = await research.run_traced("AI")
    assert [r.step for r in t.records] == ["analyze"]

asyncio.run(main())
```

## Acceptance criteria

- `Client` protocol (sync) now has a sibling `AsyncClient` protocol with
  `acomplete(...)`.
- `FakeClient` implements both `complete` and `acomplete` (the async version
  delegates to sync — same queue, same call log, same errors).
- `InstructorClient` implements both; async requires an `AsyncOpenAI`-backed
  instructor client. Construction: `InstructorClient(sync=..., async_=...)`,
  each lazily built from its OpenAI default when `None`.
- `@step` detects `async def` prompt functions and returns an `AsyncStep`
  whose `__call__` is a coroutine function.
- `AsyncStep` awaits the prompt function, awaits `client.acomplete(...)`,
  and records a `TraceRecord` on success (same shape as sync).
- `@flow` detects `async def` functions and returns an `AsyncFlow`;
  `AsyncFlow.run_traced(*args)` is an `async def` returning `(result, Trace)`.
- `asyncio.gather` of parallel async steps all land in the same active trace,
  in completion order.

## Non-goals (deferred)

- Streaming responses.
- Mixed sync/async chains within a single flow (possible in principle;
  untested surface).
- Cancellation semantics beyond what asyncio gives us for free.
