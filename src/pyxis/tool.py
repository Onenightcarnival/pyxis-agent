"""Tool primitive: actions declared as Pydantic schemas.

A `Tool` is a BaseModel whose fields *are* the parameters of an action and
whose `run()` *is* the action's implementation. The LLM picks a tool by
emitting a matching instance (typically within a discriminated union on a
Step output's `action` field); Python dispatches by calling `.run()`.

The framework ships no function-calling adapter — the schema is the interface.
"""

from __future__ import annotations

from pydantic import BaseModel


class Tool(BaseModel):
    """Base class for a callable action the LLM can emit.

    Subclass with Pydantic fields (the tool's parameters) and override `run`.
    For use in a discriminated union, add a `Literal["..."] = "..."` kind field.
    """

    def run(self) -> str:
        raise NotImplementedError(f"Tool subclass {type(self).__name__!r} must override run()")
