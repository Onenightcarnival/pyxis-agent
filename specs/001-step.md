# 001: Step — single LLM call with schema-as-CoT

## Purpose

A `Step` is one LLM call whose reasoning is declared by the Pydantic output
schema's field order (the implicit CoT). The function's docstring is the
system prompt; its return value is the user message (the code-as-prompt).

## API sketch

```python
from pydantic import BaseModel, Field
from pyxis import step, FakeClient, set_default_client

class Plan(BaseModel):
    goal: str = Field(description="restate the request")
    subtasks: list[str] = Field(description="break into concrete subtasks")
    next_action: str = Field(description="pick the first subtask")

@step(output=Plan)
def plan(request: str) -> str:
    """You are a meticulous planner. Produce a JSON plan for the request."""
    return f"Request: {request}"

# production
set_default_client(InstructorClient())       # OpenAI-backed by default
result: Plan = plan("build a todo app")

# tests
fake = FakeClient([Plan(goal="g", subtasks=[], next_action="a")])
result = plan_with_fake("build x")            # decorator passed client=fake
assert fake.calls[0].messages[0]["role"] == "system"
```

## Acceptance criteria

- `@step(output=M)` wraps a function into a callable returning an instance of `M`.
- The wrapped callable preserves `__name__` and `__doc__` of the original function.
- Invocation builds messages: `system` = stripped docstring (omitted if empty),
  `user` = function's string return value. In that order.
- Client resolution at call time: `client=` kwarg on `@step` > global default
  set by `set_default_client` > lazy `InstructorClient()` (requires OpenAI env).
- `FakeClient(responses=[...])`:
  - returns queued responses in order;
  - records every call in `.calls` (messages, response_model, model);
  - raises `RuntimeError` when exhausted;
  - raises `TypeError` when a queued response isn't an instance of the requested model.
- `model` kwarg on `@step` is forwarded to the client; default is `"gpt-4o-mini"`.

## Non-goals (deferred)

- Streaming, async, tool calling, retries, cost tracking, message-list prompts.
