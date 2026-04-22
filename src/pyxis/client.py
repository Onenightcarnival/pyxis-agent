"""LLM 客户端：内部规范化层 + 测试用 `FakeClient`。

`@step(client=...)` 吃 `openai.OpenAI` / `openai.AsyncOpenAI` 或
`instructor.from_openai(...)` 返回的实例。`@step` 内部用
`_adapt_sync_client` / `_adapt_async_client` 把它规范化成内部的
`_SyncBackend` / `_AsyncBackend`。

对外导出的只有 `FakeClient` + `FakeCall`：零网络、按队列返回预置
Pydantic 实例、`.calls` 记录每次调用的 messages / model / max_retries /
params，用于单测断言。
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Iterable, Iterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

_Messages = list[dict[str, str]]


@runtime_checkable
class _SyncBackend(Protocol):
    """pyxis 内部契约：同步后端。用户不直接实现，仅 `FakeClient` 与内部
    adapter 走这个接口。"""

    def complete[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> T: ...

    def stream[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> Iterator[T]: ...


@runtime_checkable
class _AsyncBackend(Protocol):
    """pyxis 内部契约：异步后端。"""

    async def acomplete[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> T: ...

    def astream[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> AsyncIterator[T]: ...


@dataclass
class FakeCall:
    """`FakeClient` 捕获的一次调用。`params` 记录 `@step(params=...)` 透传
    过来的字典，方便测试断言"这次调用的采样参数是什么"。"""

    messages: _Messages
    response_model: type[BaseModel]
    model: str
    max_retries: int = 0
    params: dict[str, Any] | None = None


class FakeClient:
    """测试用的确定性后端——按队列顺序返回预置响应，零网络。

    同时实现 `_SyncBackend` 与 `_AsyncBackend`；async 路径直接委托 sync
    （共享队列 / 调用日志 / 错误语义）。调用耗尽抛 `RuntimeError`；响应
    与 `response_model` 类型不符抛 `TypeError`。
    """

    def __init__(self, responses: Iterable[BaseModel]):
        self._responses: list[BaseModel] = list(responses)
        self._cursor: int = 0
        self.calls: list[FakeCall] = []

    def complete[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> T:
        self.calls.append(
            FakeCall(
                messages=list(messages),
                response_model=response_model,
                model=model,
                max_retries=max_retries,
                params=dict(params) if params is not None else None,
            )
        )
        if self._cursor >= len(self._responses):
            raise RuntimeError(
                f"FakeClient 已在第 {self._cursor} 次调用后耗尽；"
                f"第 {self._cursor + 1} 次调用缺少预置响应"
                f"（期望 {response_model.__name__}）"
            )
        resp = self._responses[self._cursor]
        self._cursor += 1
        if not isinstance(resp, response_model):
            raise TypeError(
                f"FakeClient 第 {self._cursor} 个响应是 "
                f"{type(resp).__name__}，期望 {response_model.__name__}"
            )
        return resp

    async def acomplete[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> T:
        return self.complete(
            messages, response_model, model, max_retries=max_retries, params=params
        )

    def stream[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> Iterator[T]:
        """模拟"一帧流"：消费一个响应并 yield 一次。"""
        yield self.complete(messages, response_model, model, max_retries=max_retries, params=params)

    async def astream[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> AsyncIterator[T]:
        yield self.complete(messages, response_model, model, max_retries=max_retries, params=params)


class _SyncInstructorAdapter:
    """包一层 instructor-patched 同步客户端，暴露 `_SyncBackend` 接口。"""

    def __init__(self, client: Any):
        self._c = client

    def complete[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> T:
        extra = dict(params) if params is not None else {}
        return self._c.chat.completions.create(
            messages=messages,
            response_model=response_model,
            model=model,
            max_retries=max_retries,
            **extra,
        )

    def stream[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> Iterator[T]:
        extra = dict(params) if params is not None else {}
        yield from self._c.chat.completions.create_partial(
            messages=messages,
            response_model=response_model,
            model=model,
            max_retries=max_retries,
            **extra,
        )


class _AsyncInstructorAdapter:
    """包一层 instructor-patched 异步客户端，暴露 `_AsyncBackend` 接口。"""

    def __init__(self, client: Any):
        self._c = client

    async def acomplete[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> T:
        extra = dict(params) if params is not None else {}
        return await self._c.chat.completions.create(
            messages=messages,
            response_model=response_model,
            model=model,
            max_retries=max_retries,
            **extra,
        )

    async def astream[T: BaseModel](
        self,
        messages: _Messages,
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
        params: dict[str, Any] | None = None,
    ) -> AsyncIterator[T]:
        extra = dict(params) if params is not None else {}
        async for partial in self._c.chat.completions.create_partial(
            messages=messages,
            response_model=response_model,
            model=model,
            max_retries=max_retries,
            **extra,
        ):
            yield partial


def _looks_like_async_instructor(client: Any) -> bool:
    create = getattr(getattr(getattr(client, "chat", None), "completions", None), "create", None)
    return create is not None and inspect.iscoroutinefunction(create)


def _adapt_sync_client(client: Any) -> _SyncBackend:
    """把用户传进来的 client 规范化为 `_SyncBackend`。

    - `FakeClient` / 鸭子类型实现了 `_SyncBackend`（带 `complete` + `stream`）
      的对象 → 直接返回。用户要接第三方 mock / cache wrapper 走这条路。
    - `openai.AsyncOpenAI` / 异步 instructor 实例 → 报 `TypeError`。
    - `openai.OpenAI` → 懒 patch 成 instructor 再包 adapter。
    - 其余假设已经是同步 instructor 实例 → 直接包 adapter。
    """
    if isinstance(client, FakeClient):
        return client

    # 只在真正需要的时候 import openai / instructor，避免给纯 FakeClient
    # 的单元测试强加硬依赖（虽然本项目都装了，但保持入口干净）。
    from openai import AsyncOpenAI, OpenAI

    if isinstance(client, AsyncOpenAI):
        raise TypeError("同步 @step 拿到 AsyncOpenAI；请传同步 OpenAI 实例，或改写成 async def")
    if isinstance(client, OpenAI):
        import instructor

        return _SyncInstructorAdapter(instructor.from_openai(client))

    # 鸭子类型：实现了 _SyncBackend 协议（测试桩、cache wrapper、
    # 自研 non-instructor 后端等）。runtime_checkable Protocol 的
    # isinstance 走方法存在性检查。
    if isinstance(client, _SyncBackend):
        return client

    if _looks_like_async_instructor(client):
        raise TypeError("同步 @step 拿到异步 instructor 实例；请传同步版本，或改写成 async def")
    return _SyncInstructorAdapter(client)


def _adapt_async_client(client: Any) -> _AsyncBackend:
    """把用户传进来的 client 规范化为 `_AsyncBackend`。"""
    if isinstance(client, FakeClient):
        return client

    from openai import AsyncOpenAI, OpenAI

    if isinstance(client, OpenAI):
        raise TypeError("异步 @step 拿到 OpenAI（同步）；请传 AsyncOpenAI，或改写成 def")
    if isinstance(client, AsyncOpenAI):
        import instructor

        return _AsyncInstructorAdapter(instructor.from_openai(client))

    if isinstance(client, _AsyncBackend):
        return client

    if not _looks_like_async_instructor(client):
        raise TypeError("异步 @step 拿到同步 instructor 实例；请传异步版本，或改写成 def")
    return _AsyncInstructorAdapter(client)
