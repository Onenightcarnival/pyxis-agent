"""LLM 客户端抽象。

一个 `Client` 做一次结构化的 LLM 调用：输入 messages 与目标 response_model，
返回 `CompletionResult[T]`（解析出的实例 + 可选的 token 用量）。生产环境
用 `InstructorClient`（背后是 instructor 补丁过的 provider SDK），测试环境
用 `FakeClient`（按队列返回预置响应，零网络）。两者都同时提供同步与异步两路。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

Message = dict[str, str]


@dataclass
class Usage:
    """一次 LLM 调用的 token 账单，字段默认为 0。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class CompletionResult[T: BaseModel]:
    """一次结构化调用的结果：解析出的 output，以及可选的 usage。"""

    output: T
    usage: Usage | None = None


@runtime_checkable
class Client(Protocol):
    """最小同步结构化调用接口。"""

    def complete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> CompletionResult[T]: ...

    def stream[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> Iterator[T]:
        """按字段逐步 yield partial 实例；最后一帧是完整实例。"""
        ...


@runtime_checkable
class AsyncClient(Protocol):
    """`Client` 的异步孪生。"""

    async def acomplete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> CompletionResult[T]: ...

    def astream[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> AsyncIterator[T]: ...


@dataclass
class FakeCall:
    """`FakeClient` 捕获的一次调用。"""

    messages: list[Message]
    response_model: type[BaseModel]
    model: str
    max_retries: int = 0


class FakeClient:
    """给测试用的确定性客户端——按队列顺序返回预置响应。

    构造时可以同时传入 `usages` 并列列表；每次调用弹出一个（列表短于
    `responses` 时，后续调用的 usage 为 None）。同时实现 `Client` 与
    `AsyncClient` 两个协议，async 路径直接委托给 sync（共享队列、共享
    调用日志、共享错误语义）。

    调用耗尽时抛 `RuntimeError`；预置响应与目标 `response_model` 不匹配
    时抛 `TypeError`。
    """

    def __init__(
        self,
        responses: Iterable[BaseModel],
        *,
        usages: Iterable[Usage | None] | None = None,
    ):
        self._responses: list[BaseModel] = list(responses)
        self._usages: list[Usage | None] = list(usages) if usages is not None else []
        self._cursor: int = 0
        self.calls: list[FakeCall] = []

    def complete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> CompletionResult[T]:
        self.calls.append(
            FakeCall(
                messages=list(messages),
                response_model=response_model,
                model=model,
                max_retries=max_retries,
            )
        )
        if self._cursor >= len(self._responses):
            raise RuntimeError(
                f"FakeClient 已在第 {self._cursor} 次调用后耗尽；"
                f"第 {self._cursor + 1} 次调用缺少预置响应"
                f"（期望 {response_model.__name__}）"
            )
        resp = self._responses[self._cursor]
        usage = self._usages[self._cursor] if self._cursor < len(self._usages) else None
        self._cursor += 1
        if not isinstance(resp, response_model):
            raise TypeError(
                f"FakeClient 第 {self._cursor} 个响应是 "
                f"{type(resp).__name__}，期望 {response_model.__name__}"
            )
        return CompletionResult(output=resp, usage=usage)

    async def acomplete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> CompletionResult[T]:
        return self.complete(messages, response_model, model, max_retries=max_retries)

    def stream[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> Iterator[T]:
        """模拟"一帧流"：消费一个 response 并 yield 一次。"""
        result = self.complete(messages, response_model, model, max_retries=max_retries)
        yield result.output

    async def astream[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> AsyncIterator[T]:
        result = self.complete(messages, response_model, model, max_retries=max_retries)
        yield result.output


def _extract_usage(raw: Any) -> Usage | None:
    """尽力从 OpenAI 风格的 raw response 里提一个 `Usage` 出来。"""
    if raw is None:
        return None
    u = getattr(raw, "usage", None)
    if u is None:
        return None
    return Usage(
        prompt_tokens=int(getattr(u, "prompt_tokens", 0) or 0),
        completion_tokens=int(getattr(u, "completion_tokens", 0) or 0),
        total_tokens=int(getattr(u, "total_tokens", 0) or 0),
    )


class InstructorClient:
    """基于 instructor 的真实客户端，同时承担同步与异步两路。

    两路后端在未指定时都会从 OpenAI 默认环境懒构造出来。想接 Anthropic
    或其他 provider？直接传一个 instructor 已经 patch 过的 client 进来。
    """

    def __init__(
        self,
        instructor_client: Any = None,
        async_instructor_client: Any = None,
    ):
        self._sync = instructor_client
        self._async = async_instructor_client

    def _get_sync(self) -> Any:
        if self._sync is None:
            import instructor
            from openai import OpenAI

            self._sync = instructor.from_openai(OpenAI())
        return self._sync

    def _get_async(self) -> Any:
        if self._async is None:
            import instructor
            from openai import AsyncOpenAI

            self._async = instructor.from_openai(AsyncOpenAI())
        return self._async

    def complete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> CompletionResult[T]:
        result, raw = self._get_sync().chat.completions.create_with_completion(
            messages=messages,
            response_model=response_model,
            model=model,
            max_retries=max_retries,
        )
        return CompletionResult(output=result, usage=_extract_usage(raw))

    async def acomplete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> CompletionResult[T]:
        result, raw = await self._get_async().chat.completions.create_with_completion(
            messages=messages,
            response_model=response_model,
            model=model,
            max_retries=max_retries,
        )
        return CompletionResult(output=result, usage=_extract_usage(raw))

    def stream[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> Iterator[T]:
        """基于 instructor `create_partial` 的同步流式。"""
        yield from self._get_sync().chat.completions.create_partial(
            messages=messages,
            response_model=response_model,
            model=model,
            max_retries=max_retries,
        )

    async def astream[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> AsyncIterator[T]:
        """基于 instructor `create_partial` 的异步流式。"""
        async for partial in self._get_async().chat.completions.create_partial(
            messages=messages,
            response_model=response_model,
            model=model,
            max_retries=max_retries,
        ):
            yield partial


@dataclass
class _DefaultClient:
    client: Any = None
    _lazy: Any = field(default=None, repr=False)


_default = _DefaultClient()


def set_default_client(client: Any) -> None:
    """设置进程级默认 client。传 `None` 则重置为懒构造 `InstructorClient`。"""
    _default.client = client
    _default._lazy = None


def get_default_client() -> Any:
    """取当前默认 client，必要时懒构造出 `InstructorClient`。"""
    if _default.client is not None:
        return _default.client
    if _default._lazy is None:
        _default._lazy = InstructorClient()
    return _default._lazy
