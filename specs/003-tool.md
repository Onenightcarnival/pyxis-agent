# 003: Tool — actions as declarative schemas

## Purpose

A `Tool` is a `BaseModel` whose fields *are* the action's parameters and whose
`run()` *is* the action's implementation. The LLM picks a tool by filling
a discriminated-union `action` field in its output schema; Python executes
the chosen tool by calling `.run()`. We do *not* adopt function-calling
protocols — the output schema declares intent, the code fulfills it.

This keeps the framework's two layers intact:
- implicit: schema says "the next token emits one of these tool types";
- explicit: plain Python drives the loop that calls `.run()` and decides to continue.

## API sketch

```python
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from pyxis import Tool, step

class SearchWeb(Tool):
    """Search the web for a query."""
    kind: Literal["search"] = "search"
    query: str

    def run(self) -> str:
        return f"results for {self.query}"

class Finish(Tool):
    """Stop and report the final answer."""
    kind: Literal["finish"] = "finish"
    answer: str

    def run(self) -> str:
        return self.answer

Action = Annotated[SearchWeb | Finish, Field(discriminator="kind")]

class Decision(BaseModel):
    thought: str
    action: Action

@step(output=Decision)
def decide(question: str, scratch: str) -> str:
    """You are an agent. Think, then pick a tool."""
    return f"Q: {question}\nSCRATCH:\n{scratch}"

# The explicit loop — plain Python:
scratch: list[str] = []
for _ in range(10):
    d = decide(question, "\n".join(scratch))
    scratch.append(f"thought: {d.thought}")
    obs = d.action.run()
    scratch.append(f"obs: {obs}")
    if isinstance(d.action, Finish):
        return obs
```

## Acceptance criteria

- `Tool` is a `BaseModel` subclass. Subclasses add fields and override `run()`.
- Calling `run()` on a base `Tool` (or a subclass that forgot to override)
  raises `NotImplementedError` with the subclass's name in the message.
- `Tool.run()` must return `str` (documented convention, not type-enforced at runtime).
- `Tool` subclasses participate in discriminated unions via a `Literal` `kind`
  field — standard Pydantic mechanism, no framework magic.
- A `Tool` instance inside a Pydantic schema round-trips through `FakeClient`
  and `@step` unchanged.

## Non-goals (deferred)

- Auto-generating Tool classes from Python functions.
- Async tool execution (iter 5 covers async broadly).
- A built-in agent loop helper — the loop is the user's `@flow`.
