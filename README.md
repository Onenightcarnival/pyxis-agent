# pyxis-agent

Declarative chain-of-thought agent framework for Python.

> **`declarative CoT = code as prompt + schema as workflow`**

Most agent frameworks either give you a node-based graph DSL (Airflow for LLMs)
or hide the reasoning inside opaque `chain.run()` calls. **pyxis** takes a
different bet:

- The Python **function's docstring** *is* the system prompt.
- The function's **string return** *is* the user message.
- The **Pydantic output schema's field order** *is* the chain of thought —
  the LLM must fill fields top-to-bottom, so the schema literally declares
  the reasoning steps.
- For multi-step flows, you write **plain Python**. No DSL. `if`, `for`, and
  function composition are already the best orchestration language we have.

## Two orchestration layers

| Scope                      | Mechanism                                       |
|----------------------------|-------------------------------------------------|
| Implicit (single LLM call) | `instructor` + the output schema's field order  |
| Explicit (multiple calls)  | plain Python                                    |

## What's in the box

| Primitive            | What it is                                                           |
|----------------------|----------------------------------------------------------------------|
| `@step(output=M)`    | Turns a prompt function into a typed LLM call. Sync or `async def`.  |
| `@flow`              | Thin wrapper for multi-step functions; `.run_traced()` included.     |
| `Tool`               | `BaseModel` with `run()`. Actions are schemas; code dispatches.      |
| `trace()`            | `ContextVar`-based capture across sync *and* `asyncio.gather`.       |
| `Trace.to_json()`    | Structured export + `total_usage()` aggregation.                     |
| `FakeClient`         | Deterministic canned responses + call log for tests (no network).    |
| `InstructorClient`   | Production client; OpenAI-compatible; async + sync.                  |

## Install

```bash
uv add pyxis-agent
```

## Quickstart

```python
from pydantic import BaseModel, Field
from pyxis import flow, step, trace

class Analysis(BaseModel):
    observation: str = Field(description="what you notice")
    reasoning: str = Field(description="why it matters")
    conclusion: str = Field(description="one-sentence takeaway")

class Plan(BaseModel):
    goal: str
    steps: list[str]
    next_action: str

@step(output=Analysis)
def analyze(topic: str) -> str:
    """You are a careful analyst. Observe, reason, conclude."""
    return f"Topic: {topic}"

@step(output=Plan, max_retries=2)
def plan_from(a: Analysis) -> str:
    """You turn analyses into plans."""
    return a.model_dump_json()

@flow
def research(topic: str) -> Plan:
    return plan_from(analyze(topic))

result, t = research.run_traced("declarative CoT agents")
print(t.total_usage())          # Usage(prompt_tokens=..., ...)
print(t.to_json(indent=2))      # structured log
```

## Agents with tools (ReAct-style, in plain Python)

```python
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from pyxis import Tool, flow, step

class Calculate(Tool):
    """Evaluate a math expression."""
    kind: Literal["calculate"] = "calculate"
    expression: str
    def run(self) -> str:
        return str(eval(self.expression, {"__builtins__": {}}, {}))

class Finish(Tool):
    """Stop and report the answer."""
    kind: Literal["finish"] = "finish"
    answer: str
    def run(self) -> str:
        return self.answer

Action = Annotated[Calculate | Finish, Field(discriminator="kind")]

class Decision(BaseModel):
    thought: str
    action: Action

@step(output=Decision)
def decide(q: str, scratch: str) -> str:
    """Think. Then emit exactly one tool call."""
    return f"Q: {q}\n{scratch}"

@flow
def agent(q: str, max_steps: int = 6) -> str:
    scratch: list[str] = []
    for _ in range(max_steps):
        d = decide(q, "\n".join(scratch))
        scratch += [f"thought: {d.thought}", f"obs: {d.action.run()}"]
        if isinstance(d.action, Finish):
            return d.action.answer
    raise RuntimeError("max_steps exhausted")
```

## Async

```python
import asyncio
from pyxis import flow, step

@step(output=Analysis)
async def analyze(topic: str) -> str:
    """..."""
    return topic

@flow
async def research(topics: list[str]) -> list[Analysis]:
    return await asyncio.gather(*(analyze(t) for t in topics))

asyncio.run(research(["x", "y", "z"]))
```

## Testing without a key

`FakeClient` is shipped in the library. It returns queued Pydantic instances
in order, records every call, and supports the async path too:

```python
from pyxis import FakeClient, Usage, step

fake = FakeClient(
    responses=[Analysis(observation="o", reasoning="r", conclusion="c")],
    usages=[Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)],
)

@step(output=Analysis, client=fake)
def analyze(t: str) -> str:
    """..."""
    return t

analyze("x")
assert fake.calls[0].messages[-1]["content"] == "x"
```

## Running the examples against OpenRouter

```bash
cp .env.example .env      # edit in your key
uv run --env-file .env python examples/research.py
uv run --env-file .env python examples/agent_tool_use.py
```

## Dev

```bash
uv sync
uv run ruff format && uv run ruff check
uv run pytest                                        # unit tests, no network
uv run --env-file .env pytest tests/integration/     # live smoke tests
```

Every iteration lands with a spec in [specs/](specs/) (SDD) and tests first
(TDD). See [CHANGELOG.md](CHANGELOG.md) for release history and
[ROADMAP.md](ROADMAP.md) for what's deferred (and what is *intentionally*
not on the roadmap). Design rationale lives in [CLAUDE.md](CLAUDE.md).
