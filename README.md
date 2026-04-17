# pyxis-agent

Declarative chain-of-thought agent framework for Python.

> **`declarative CoT = code as prompt + schema as workflow`**

Most agent frameworks either give you a node-based graph DSL (Airflow for LLMs) or
hide the reasoning inside opaque `chain.run()` calls. **pyxis** takes a different bet:

- The Python **function's docstring** *is* the system prompt.
- The function's **string return** *is* the user message.
- The **Pydantic output schema's field order** *is* the chain of thought —
  the LLM must fill fields top-to-bottom, so the schema literally declares the
  reasoning steps.
- For multi-step flows, you write **plain Python**. No DSL. `if`, `for`, and
  function composition are already the best orchestration language we have.

## Two orchestration layers

| Scope                       | Mechanism                                      |
|-----------------------------|------------------------------------------------|
| Implicit (single LLM call)  | `instructor` + the output schema's field order |
| Explicit (multiple calls)   | plain Python                                   |

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

@step(output=Plan)
def plan_from(a: Analysis) -> str:
    """You turn analyses into plans."""
    return a.model_dump_json()

@flow
def research(topic: str) -> Plan:
    return plan_from(analyze(topic))

# normal call
p = research("declarative CoT agents")

# traced call — one TraceRecord per step
result, t = research.run_traced("declarative CoT agents")
for rec in t:
    print(rec.step, "->", rec.output)
```

## Testing without a key

`FakeClient` is shipped in the library. It returns queued Pydantic instances
in order and records every call:

```python
from pyxis import FakeClient, step

fake = FakeClient([Analysis(observation="o", reasoning="r", conclusion="c")])

@step(output=Analysis, client=fake)
def analyze(t: str) -> str:
    """..."""
    return t

analyze("x")
assert fake.calls[0].messages[-1]["content"] == "x"
```

## Running the example against OpenRouter

```bash
cp .env.example .env   # edit in your key
uv run --env-file .env python examples/research.py
```

## Dev

```bash
uv sync
uv run ruff format && uv run ruff check
uv run pytest                                        # unit tests, no network
uv run --env-file .env pytest tests/integration/     # smoke tests, needs key
```

Every iteration lands with a spec in [specs/](specs/) (SDD) and tests written
first (TDD). Design rationale lives in [CLAUDE.md](CLAUDE.md).
