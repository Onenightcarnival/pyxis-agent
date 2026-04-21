"""Human-in-the-loop：用生成器 flow 在中间挂起等人。

核心：`@flow` 本来就能接受生成器函数（`yield` + `return value`）。围着
它加三样东西——`HumanQuestion`（问什么）、`FlowResult`（终态哨兵）、
`run_flow` / `run_aflow`（把生成器驱动起来并把人类答案 send 回去）。

没有 checkpoint、没有 state 快照、没有特殊语法——生成器本身就是活的
状态。人在中间就是一段普通 Python 控制流。
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class HumanQuestion:
    """一次 yield 给驱动器的"问人类"请求。"""

    question: str
    schema: type[BaseModel] | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FlowResult:
    """生成器 flow 的终态哨兵。异步生成器不能写 `return value`，用它替代。"""

    value: Any


def ask_human(
    question: str,
    *,
    schema: type[BaseModel] | None = None,
    **context: Any,
) -> HumanQuestion:
    """构造一个 `HumanQuestion`。约定在 `@flow` 生成器里以 `yield` 发出。

    - `schema` 非 None 时，驱动器会把 `on_ask` 的返回值先 validate 成对应
      Pydantic 实例再 send 回生成器。
    - `**context` 会原样放进 `HumanQuestion.context`，留给 `on_ask` 渲染
      UI 或做判断。
    """
    return HumanQuestion(question=question, schema=schema, context=dict(context))


def finish(value: Any) -> FlowResult:
    """构造一个终态哨兵。建议作为 async 生成器 flow 的最后一个 yield。"""
    return FlowResult(value=value)


def _coerce_answer(answer: Any, schema: type[BaseModel] | None) -> Any:
    if schema is None or isinstance(answer, schema):
        return answer
    return schema.model_validate(answer)


def _not_a_yield(req: Any) -> TypeError:
    return TypeError(f"期望 yield HumanQuestion 或 FlowResult，实际是 {type(req).__name__}")


def run_flow(
    gen: Generator[Any, Any, Any],
    *,
    on_ask: Callable[[HumanQuestion], Any],
) -> Any:
    """同步驱动一个 `@flow` 生成器。"""
    try:
        req = next(gen)
    except StopIteration as stop:
        return stop.value
    while True:
        if isinstance(req, FlowResult):
            gen.close()
            return req.value
        if not isinstance(req, HumanQuestion):
            raise _not_a_yield(req)
        answer = _coerce_answer(on_ask(req), req.schema)
        try:
            req = gen.send(answer)
        except StopIteration as stop:
            return stop.value


async def run_aflow(
    gen: Generator[Any, Any, Any] | AsyncGenerator[Any, Any],
    *,
    on_ask: Callable[[HumanQuestion], Awaitable[Any] | Any],
) -> Any:
    """异步驱动；同时支持同步与异步生成器、同步与异步 `on_ask`。"""
    if inspect.isasyncgen(gen):
        return await _drive_async_gen(gen, on_ask)
    return await _drive_sync_gen_async(gen, on_ask)  # type: ignore[arg-type]


async def _drive_async_gen(
    gen: AsyncGenerator[Any, Any],
    on_ask: Callable[[HumanQuestion], Awaitable[Any] | Any],
) -> Any:
    try:
        req = await gen.__anext__()
    except StopAsyncIteration:
        return None
    while True:
        if isinstance(req, FlowResult):
            await gen.aclose()
            return req.value
        if not isinstance(req, HumanQuestion):
            raise _not_a_yield(req)
        answer = await _maybe_await(on_ask(req))
        answer = _coerce_answer(answer, req.schema)
        try:
            req = await gen.asend(answer)
        except StopAsyncIteration:
            return None


async def _drive_sync_gen_async(
    gen: Generator[Any, Any, Any],
    on_ask: Callable[[HumanQuestion], Awaitable[Any] | Any],
) -> Any:
    try:
        req = next(gen)
    except StopIteration as stop:
        return stop.value
    while True:
        if isinstance(req, FlowResult):
            gen.close()
            return req.value
        if not isinstance(req, HumanQuestion):
            raise _not_a_yield(req)
        answer = await _maybe_await(on_ask(req))
        answer = _coerce_answer(answer, req.schema)
        try:
            req = gen.send(answer)
        except StopIteration as stop:
            return stop.value


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
