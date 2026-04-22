"""Flow：显式多步编排。

`@flow` 是一层很薄的语义标记——套在一个普通 Python 函数外面，按
`async def` / `def` 分派成 `AsyncFlow` / `Flow`。多步编排直接写
`if` / `for` / 函数组合。

语义上 `@flow` 的价值是声明意图：读代码的人一眼看出"这段是协调多次
LLM 调用的 flow"。运行时就是一个透明包装，调用时等价于调原函数；
图状调度 / 断点续跑 / checkpointer 等能力由调用方的代码和 APM 层
负责。

生成器版 `@flow` 配合 `ask_human` + `run_flow` / `run_aflow` 做
human-in-the-loop——中间 `yield` 挂起等人类回应，驱动器 `.send()` 答案
回生成器。细节见 `pyxis.human`。
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
