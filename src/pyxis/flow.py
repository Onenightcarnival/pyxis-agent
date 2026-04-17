"""Flow 原语：显式多步编排，完全用普通 Python 写。

`@flow` 是有意做得很薄的 —— Python 本身就能组合函数；我们只加两件事：
一个"这是多步 flow"的标记，以及 `.run_traced(...)` 一键得到 `(结果, Trace)`。
遇到 `async def` 时，装饰器返回 `AsyncFlow`，它的方法都是 coroutine function。
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from .trace import Trace, trace


class Flow[R]:
    """包装一个同步函数，标记它是多步 flow。"""

    def __init__(self, fn: Callable[..., R]):
        self.fn = fn
        functools.update_wrapper(self, fn)

    def __call__(self, *args: Any, **kwargs: Any) -> R:
        return self.fn(*args, **kwargs)

    def run_traced(self, *args: Any, **kwargs: Any) -> tuple[R, Trace]:
        """在新建的 trace 作用域里调用 flow；返回 `(结果, trace)`。"""
        with trace() as t:
            result = self.fn(*args, **kwargs)
        return result, t


class AsyncFlow[R]:
    """包装一个异步函数，标记它是多步 flow。"""

    def __init__(self, fn: Callable[..., Awaitable[R]]):
        self.fn = fn
        functools.update_wrapper(self, fn)

    async def __call__(self, *args: Any, **kwargs: Any) -> R:
        return await self.fn(*args, **kwargs)

    async def run_traced(self, *args: Any, **kwargs: Any) -> tuple[R, Trace]:
        """在新建的 trace 作用域里 await flow；返回 `(结果, trace)`。"""
        with trace() as t:
            result = await self.fn(*args, **kwargs)
        return result, t


def flow(fn: Callable[..., Any]) -> Flow[Any] | AsyncFlow[Any]:
    """装饰器：把一个函数标记为多步 flow。根据 `async def` 自动分派。"""
    if inspect.iscoroutinefunction(fn):
        return AsyncFlow(fn)
    return Flow(fn)
