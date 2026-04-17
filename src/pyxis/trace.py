"""Tracing primitives: capture Step calls within a scope.

A `Trace` is a plain bag of `TraceRecord`s. The active trace is propagated
via a `ContextVar`, so it's safe across asyncio tasks and threads that
inherit context.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from pydantic import BaseModel

from .client import Message


@dataclass
class TraceRecord:
    """One captured Step call."""

    step: str
    messages: list[Message]
    output: BaseModel
    model: str


@dataclass
class Trace:
    """Ordered sequence of Step calls captured within a `trace()` scope."""

    records: list[TraceRecord] = field(default_factory=list)

    def __iter__(self) -> Iterator[TraceRecord]:
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)


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
