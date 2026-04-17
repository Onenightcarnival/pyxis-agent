"""Flow primitive: explicit multi-step orchestration as Python code.

@flow is intentionally thin — Python already composes functions. It adds a
marker for intent and a `run_traced(...)` convenience. `async def` flows
get an `AsyncFlow` wrapper whose methods are coroutines.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from .trace import Trace, trace


class Flow[R]:
    """Callable wrapper around a sync function marked as a multi-step flow."""

    def __init__(self, fn: Callable[..., R]):
        self.fn = fn
        functools.update_wrapper(self, fn)

    def __call__(self, *args: Any, **kwargs: Any) -> R:
        return self.fn(*args, **kwargs)

    def run_traced(self, *args: Any, **kwargs: Any) -> tuple[R, Trace]:
        """Call the flow inside a fresh trace scope; return `(result, trace)`."""
        with trace() as t:
            result = self.fn(*args, **kwargs)
        return result, t


class AsyncFlow[R]:
    """Callable wrapper around an async function marked as a multi-step flow."""

    def __init__(self, fn: Callable[..., Awaitable[R]]):
        self.fn = fn
        functools.update_wrapper(self, fn)

    async def __call__(self, *args: Any, **kwargs: Any) -> R:
        return await self.fn(*args, **kwargs)

    async def run_traced(self, *args: Any, **kwargs: Any) -> tuple[R, Trace]:
        """Await the flow inside a fresh trace scope; return `(result, trace)`."""
        with trace() as t:
            result = await self.fn(*args, **kwargs)
        return result, t


def flow(fn: Callable[..., Any]) -> Flow[Any] | AsyncFlow[Any]:
    """Mark a function as a multi-step flow. Dispatches on `async def`."""
    if inspect.iscoroutinefunction(fn):
        return AsyncFlow(fn)
    return Flow(fn)
