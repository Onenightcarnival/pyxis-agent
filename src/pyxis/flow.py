"""Flow：显式多步编排，完全用普通 Python 写。

`@flow` 是有意做得很薄的——Python 本身就能组合函数；这里只加一件事：
一个"这是多步 flow"的语义标记 + 按 `async def` / `def` 分派到
`AsyncFlow` / `Flow`。

pyxis 本体不做可观测；生产接 Langfuse / OpenTelemetry / APM，测试用
`FakeClient` 断言 `.calls`。
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any


class Flow[R]:
    """包装一个同步函数，标记它是多步 flow。"""

    def __init__(self, fn: Callable[..., R]):
        self.fn = fn
        functools.update_wrapper(self, fn)

    def __call__(self, *args: Any, **kwargs: Any) -> R:
        return self.fn(*args, **kwargs)


class AsyncFlow[R]:
    """包装一个异步函数，标记它是多步 flow。"""

    def __init__(self, fn: Callable[..., Awaitable[R]]):
        self.fn = fn
        functools.update_wrapper(self, fn)

    async def __call__(self, *args: Any, **kwargs: Any) -> R:
        return await self.fn(*args, **kwargs)


def flow(fn: Callable[..., Any]) -> Flow[Any] | AsyncFlow[Any]:
    """装饰器：把一个函数标记为多步 flow。根据 `async def` 自动分派。"""
    if inspect.iscoroutinefunction(fn):
        return AsyncFlow(fn)
    return Flow(fn)
