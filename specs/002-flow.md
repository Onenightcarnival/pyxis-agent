# 002: Flow — explicit multi-call orchestration, Python-native

## Purpose

The framework refuses to invent a DSL for multi-call orchestration —
Python already has `if`, `for`, and function composition. `@flow` is a
thin wrapper that gives any normal Python function two things:

1. a well-known marker/name for the flow;
2. `.run_traced(*args, **kwargs)` → `(result, Trace)` for observability.

`trace()` is a context manager that captures every `Step` call within scope,
independent of whether a flow wraps them.

## API sketch

```python
from pyxis import flow, step, trace
from pydantic import BaseModel

class A(BaseModel):
    observation: str
    conclusion: str

class P(BaseModel):
    plan: str

@step(output=A, client=fake_a)
def analyze(text: str) -> str:
    """You analyze text."""
    return text

@step(output=P, client=fake_p)
def plan(a: A) -> str:
    """You turn analyses into plans."""
    return a.conclusion

@flow
def research(topic: str) -> P:
    """Research a topic: analyze, then plan."""
    return plan(analyze(topic))

# plain call: works like a normal function
p = research("AI agents")

# trace one flow call
p, t = research.run_traced("AI agents")
assert [r.step for r in t.records] == ["analyze", "plan"]

# ad-hoc trace spanning many calls
with trace() as t:
    research("a")
    research("b")
assert len(t.records) == 4
```

## Acceptance criteria

- `@flow` returns a callable that preserves `__name__` and `__doc__`.
- Calling a flow directly behaves identically to the wrapped function.
- `flow.run_traced(*args, **kwargs)` returns `(result, Trace)` with one
  `TraceRecord` per `Step` call made synchronously within the flow.
- `trace()` context manager captures all step calls within its scope,
  across one or multiple flow invocations.
- `TraceRecord` exposes: `step` (str — the Step's name), `messages`
  (list of messages as passed to the client), `output` (the BaseModel
  instance returned), `model` (str).
- A Step call made outside any trace context records nothing and returns normally.
- Nested `trace()` contexts: the innermost scope captures; the outer scope
  does not duplicate. Documented and tested.

## Non-goals (deferred)

- Async flows, parallel fan-out, retry/backoff, streaming traces,
  persistence to files, cost accounting, flow-scoped client override.
