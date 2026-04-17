"""Tracing primitives: capture Step calls within a scope.

A `Trace` is a bag of `TraceRecord`s. The active trace is propagated via a
`ContextVar`, safe across asyncio tasks that inherit context.
Records are exportable as plain dicts / JSON for logging.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from .client import Message, Usage


@dataclass
class TraceRecord:
    """One captured Step call."""

    step: str
    messages: list[Message]
    output: BaseModel
    model: str
    usage: Usage | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "messages": list(self.messages),
            "output": self.output.model_dump(mode="json"),
            "model": self.model,
            "usage": (
                None
                if self.usage is None
                else {
                    "prompt_tokens": self.usage.prompt_tokens,
                    "completion_tokens": self.usage.completion_tokens,
                    "total_tokens": self.usage.total_tokens,
                }
            ),
        }


@dataclass
class Trace:
    """Ordered sequence of Step calls captured within a `trace()` scope."""

    records: list[TraceRecord] = field(default_factory=list)

    def __iter__(self) -> Iterator[TraceRecord]:
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)

    def total_usage(self) -> Usage:
        """Sum all non-None usages; returns a zero `Usage` if none captured."""
        total = Usage()
        for rec in self.records:
            if rec.usage is not None:
                total = total + rec.usage
        return total

    def to_dict(self) -> dict[str, Any]:
        return {"records": [rec.to_dict() for rec in self.records]}

    def to_json(self, **json_kwargs: Any) -> str:
        return json.dumps(self.to_dict(), **json_kwargs)


_current: ContextVar[Trace | None] = ContextVar("pyxis_trace", default=None)


@contextmanager
def trace() -> Iterator[Trace]:
    """Open a fresh trace scope. Captures every Step call made inside.

    Nested scopes shadow outer ones: an inner `trace()` captures its own
    records; the outer does not duplicate them.
    """
    t = Trace()
    token = _current.set(t)
    try:
        yield t
    finally:
        _current.reset(token)


def record(entry: TraceRecord) -> None:
    """Push a record into the current trace, if any. No-op otherwise."""
    current = _current.get()
    if current is not None:
        current.records.append(entry)
