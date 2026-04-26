"""Interrupt：用生成器函数在中间挂起等外部输入。

普通生成器函数用 `yield ask_interrupt(...)` 声明外部输入点。
`InterruptRequest` 描述需要什么外部输入，`FlowResult` 是异步生成器的
终态哨兵，`run_flow` / `run_aflow` 把生成器驱动起来并把外部答案 send
回去。

没有 checkpoint、没有 state 快照、没有特殊语法。生成器状态留在当前进程里，
外部参与者在中间接一次请求，再把答案送回来。
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class InterruptRequest:
    """一次 yield 给驱动器的外部输入请求。"""

    question: str
    schema: type[BaseModel] | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FlowResult:
    """生成器流程的终态哨兵。异步生成器不能写 `return value`，用它替代。"""

    value: Any


def ask_interrupt(
    question: str,
    *,
    schema: type[BaseModel] | None = None,
    **context: Any,
) -> InterruptRequest:
    """构造一个 `InterruptRequest`。约定在生成器函数里以 `yield` 发出。

    - `schema` 非 None 时，驱动器会把 `on_interrupt` 的返回值先 validate
      成对应 Pydantic 实例再 send 回生成器。
    - `**context` 会原样放进 `InterruptRequest.context`，留给
      `on_interrupt` 渲染 UI、转发给另一个 agent 或做判断。
    """
    return InterruptRequest(question=question, schema=schema, context=dict(context))


def finish(value: Any) -> FlowResult:
    """构造一个终态哨兵。建议作为 async 生成器流程的最后一个 yield。"""
    return FlowResult(value=value)


def _coerce_answer(answer: Any, schema: type[BaseModel] | None) -> Any:
    if schema is None or isinstance(answer, schema):
        return answer
    return schema.model_validate(answer)


def _not_a_yield(req: Any) -> TypeError:
    return TypeError(f"期望 yield InterruptRequest 或 FlowResult，实际是 {type(req).__name__}")


def run_flow(
    gen: Generator[Any, Any, Any],
    *,
    on_interrupt: Callable[[InterruptRequest], Any],
) -> Any:
    """同步驱动一个生成器流程。"""
    try:
        req = next(gen)
    except StopIteration as stop:
        return stop.value
    while True:
        if isinstance(req, FlowResult):
            gen.close()
            return req.value
        if not isinstance(req, InterruptRequest):
            raise _not_a_yield(req)
        answer = _coerce_answer(on_interrupt(req), req.schema)
        try:
            req = gen.send(answer)
        except StopIteration as stop:
            return stop.value


async def run_aflow(
    gen: Generator[Any, Any, Any] | AsyncGenerator[Any, Any],
    *,
    on_interrupt: Callable[[InterruptRequest], Awaitable[Any] | Any],
) -> Any:
    """异步驱动；同时支持同步与异步生成器、同步与异步 `on_interrupt`。"""
    if inspect.isasyncgen(gen):
        return await _drive_async_gen(gen, on_interrupt)
    return await _drive_sync_gen_async(gen, on_interrupt)  # type: ignore[arg-type]


async def _drive_async_gen(
    gen: AsyncGenerator[Any, Any],
    on_interrupt: Callable[[InterruptRequest], Awaitable[Any] | Any],
) -> Any:
    try:
        req = await gen.__anext__()
    except StopAsyncIteration:
        return None
    while True:
        if isinstance(req, FlowResult):
            await gen.aclose()
            return req.value
        if not isinstance(req, InterruptRequest):
            raise _not_a_yield(req)
        answer = await _maybe_await(on_interrupt(req))
        answer = _coerce_answer(answer, req.schema)
        try:
            req = await gen.asend(answer)
        except StopAsyncIteration:
            return None


async def _drive_sync_gen_async(
    gen: Generator[Any, Any, Any],
    on_interrupt: Callable[[InterruptRequest], Awaitable[Any] | Any],
) -> Any:
    try:
        req = next(gen)
    except StopIteration as stop:
        return stop.value
    while True:
        if isinstance(req, FlowResult):
            gen.close()
            return req.value
        if not isinstance(req, InterruptRequest):
            raise _not_a_yield(req)
        answer = await _maybe_await(on_interrupt(req))
        answer = _coerce_answer(answer, req.schema)
        try:
            req = gen.send(answer)
        except StopIteration as stop:
            return stop.value


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
