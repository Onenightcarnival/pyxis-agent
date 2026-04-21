"""Step：一次 LLM 调用 + 结构即思维链（schema-as-CoT）。

- **code-as-prompt**：函数的 docstring 是 system prompt，字符串返回是 user message。
- **schema-as-CoT**：Pydantic 输出模型的字段顺序就是思维链——LLM 必须自上
  而下把它们填完。

`@step` 装饰器会检测 `async def` 的 prompt 函数，并分派到 `AsyncStep`，
调用方就能拿到一个 coroutine function 直接 `await`。
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any

from pydantic import BaseModel

from .client import Message, get_default_client
from .hooks import notify_end, notify_error, notify_start
from .trace import TraceRecord, record

DEFAULT_MODEL = "gpt-4o-mini"


class Step[T: BaseModel]:
    """一次类型化的同步 LLM 调用，通常通过 `@step(output=...)` 构造。"""

    def __init__(
        self,
        prompt_fn: Callable[..., str],
        output: type[T],
        *,
        model: str = DEFAULT_MODEL,
        max_retries: int = 0,
        client: Any = None,
    ):
        self.prompt_fn = prompt_fn
        self.output = output
        self.model = model
        self.max_retries = max_retries
        self.client = client
        self.system_prompt: str = _normalize_docstring(prompt_fn.__doc__ or "")
        functools.update_wrapper(self, prompt_fn)

    def __call__(self, *args: object, **kwargs: object) -> T:
        user_content = self.prompt_fn(*args, **kwargs)
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
        client = self.client or get_default_client()
        notify_start(self.__name__, messages, self.model)
        try:
            result = client.complete(
                messages, self.output, self.model, max_retries=self.max_retries
            )
        except Exception as exc:
            err = _format_error(exc)
            record(
                TraceRecord(
                    step=self.__name__,
                    messages=messages,
                    output=None,
                    model=self.model,
                    error=err,
                )
            )
            notify_error(self.__name__, messages, self.model, err)
            raise
        rec = TraceRecord(
            step=self.__name__,
            messages=messages,
            output=result.output,
            model=self.model,
            usage=result.usage,
        )
        record(rec)
        notify_end(rec)
        return result.output

    def stream(self, *args: object, **kwargs: object) -> Iterator[T]:
        """按字段逐步 yield partial 实例；消费完整个流后才写 TraceRecord。"""
        user_content = self.prompt_fn(*args, **kwargs)
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
        client = self.client or get_default_client()
        notify_start(self.__name__, messages, self.model)
        last: T | None = None
        try:
            for partial in client.stream(
                messages, self.output, self.model, max_retries=self.max_retries
            ):
                last = partial
                yield partial
        except Exception as exc:
            err = _format_error(exc)
            record(
                TraceRecord(
                    step=self.__name__,
                    messages=messages,
                    output=None,
                    model=self.model,
                    error=err,
                )
            )
            notify_error(self.__name__, messages, self.model, err)
            raise
        rec = TraceRecord(
            step=self.__name__,
            messages=messages,
            output=last,
            model=self.model,
        )
        record(rec)
        notify_end(rec)


class AsyncStep[T: BaseModel]:
    """一次类型化的异步 LLM 调用。当 `@step` 装饰的是 `async def` 时自动生成。"""

    def __init__(
        self,
        prompt_fn: Callable[..., Awaitable[str] | str],
        output: type[T],
        *,
        model: str = DEFAULT_MODEL,
        max_retries: int = 0,
        client: Any = None,
    ):
        self.prompt_fn = prompt_fn
        self.output = output
        self.model = model
        self.max_retries = max_retries
        self.client = client
        self.system_prompt: str = _normalize_docstring(prompt_fn.__doc__ or "")
        functools.update_wrapper(self, prompt_fn)

    async def __call__(self, *args: object, **kwargs: object) -> T:
        ret = self.prompt_fn(*args, **kwargs)
        user_content = await ret if inspect.isawaitable(ret) else ret
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
        client = self.client or get_default_client()
        notify_start(self.__name__, messages, self.model)
        try:
            result = await client.acomplete(
                messages, self.output, self.model, max_retries=self.max_retries
            )
        except Exception as exc:
            err = _format_error(exc)
            record(
                TraceRecord(
                    step=self.__name__,
                    messages=messages,
                    output=None,
                    model=self.model,
                    error=err,
                )
            )
            notify_error(self.__name__, messages, self.model, err)
            raise
        rec = TraceRecord(
            step=self.__name__,
            messages=messages,
            output=result.output,
            model=self.model,
            usage=result.usage,
        )
        record(rec)
        notify_end(rec)
        return result.output

    async def astream(self, *args: object, **kwargs: object) -> AsyncIterator[T]:
        """异步流式对偶。"""
        ret = self.prompt_fn(*args, **kwargs)
        user_content = await ret if inspect.isawaitable(ret) else ret
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
        client = self.client or get_default_client()
        notify_start(self.__name__, messages, self.model)
        last: T | None = None
        try:
            async for partial in client.astream(
                messages, self.output, self.model, max_retries=self.max_retries
            ):
                last = partial
                yield partial
        except Exception as exc:
            err = _format_error(exc)
            record(
                TraceRecord(
                    step=self.__name__,
                    messages=messages,
                    output=None,
                    model=self.model,
                    error=err,
                )
            )
            notify_error(self.__name__, messages, self.model, err)
            raise
        rec = TraceRecord(
            step=self.__name__,
            messages=messages,
            output=last,
            model=self.model,
        )
        record(rec)
        notify_end(rec)


def step[T: BaseModel](
    *,
    output: type[T],
    model: str = DEFAULT_MODEL,
    max_retries: int = 0,
    client: Any = None,
) -> Callable[[Callable[..., Any]], Step[T] | AsyncStep[T]]:
    """装饰器：把 prompt 函数变成一个类型化的 Step。

    - 同步 `def` 得到 `Step[T]`；异步 `async def` 得到 `AsyncStep[T]`。
    - docstring 会被解析为 system prompt（会去首尾空白与缩进）。
    - 函数的返回值必须是 `str`，它就是 user message。
    - `max_retries` 会透传给 client；对 `InstructorClient` 而言，它就是
      instructor 自己的校验驱动重试次数。
    """

    def decorator(fn: Callable[..., Any]) -> Step[T] | AsyncStep[T]:
        if inspect.iscoroutinefunction(fn):
            return AsyncStep(fn, output, model=model, max_retries=max_retries, client=client)
        return Step(fn, output, model=model, max_retries=max_retries, client=client)

    return decorator


def _build_messages(
    prompt_fn: Callable[..., Any], system_prompt: str, user_content: object
) -> list[Message]:
    if not isinstance(user_content, str):
        raise TypeError(
            f"@step 装饰的函数 {prompt_fn.__name__!r} 必须返回 str，"
            f"实际返回 {type(user_content).__name__}"
        )
    messages: list[Message] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})
    return messages


def _normalize_docstring(doc: str) -> str:
    """去首尾空白并规范化缩进，得到干净的 system prompt。"""
    return inspect.cleandoc(doc).strip()


def _format_error(exc: BaseException) -> str:
    """把异常格式化为 `类型: 消息`，写进 TraceRecord.error。"""
    return f"{type(exc).__name__}: {exc}"
