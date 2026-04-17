"""Flow primitive: explicit multi-step orchestration as Python code.

A `@flow` is intentionally thin — Python already composes functions.
It adds two things: a marker for intent, and `.run_traced(...)` for a
single-call observability path.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from .trace import Trace, trace


class Flow[R]:
    """Callable wrapper around a function marked as a multi-step flow."""

    def __init__(self, fn: Callable[..., R]):
        self.fn = fn
        functools.update_wrapper(self, fn)

    def __call__(self, *args: Any, **kwargs: Any) -> R:
        return self.fn(*args, **kwargs)

    def run_traced(self, *args: Any, **kwargs: Any) -> tuple[R, Trace]:
        """Call the flow inside a fresh trace scope; return (result, trace)."""
        with trace() as t:
            result = self.fn(*args, **kwargs)
        return result, t


def flow[R](fn: Callable[..., R]) -> Flow[R]:
    """Mark a function as a multi-step flow."""
    return Flow(fn)
