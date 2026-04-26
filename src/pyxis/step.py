"""Step：把一次 LLM 调用写成函数。

Pydantic 输出模型、字段说明、函数签名和函数体返回的输入文本，共同定义
一次调用。函数 docstring 只用于 Python 文档，不进入 LLM 上下文。
Pydantic 输出模型的字段顺序，就是模型生成字段的顺序。

`@step` 按 `def` / `async def` 分派到 `Step` / `AsyncStep`。
`client` 参数必填，吃 `openai.OpenAI` / `openai.AsyncOpenAI` 或已经
`instructor.from_openai(...)` 过的实例。原生 SDK 实例在第一次调用时
懒 patch。
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any

from pydantic import BaseModel

from .client import _adapt_async_client, _adapt_sync_client

DEFAULT_MODEL = "gpt-4o-mini"


class Step[T: BaseModel]:
    """一次类型化的同步 LLM 调用，通常通过 `@step(output=..., client=...)` 构造。"""

    def __init__(
        self,
        input_fn: Callable[..., str],
        output: type[T],
        *,
        client: Any,
        model: str = DEFAULT_MODEL,
        params: dict[str, Any] | None = None,
        max_retries: int = 0,
    ):
        self.input_fn = input_fn
        self.output = output
        self.model = model
        self.params = params
        self.max_retries = max_retries
        self._backend = _adapt_sync_client(client)
        functools.update_wrapper(self, input_fn)
        self.__signature__ = _public_signature(input_fn, output)
        self.__annotations__ = _public_annotations(input_fn, output)

    def __call__(self, *args: object, **kwargs: object) -> T:
        user_content = self.input_fn(*args, **kwargs)
        messages = _build_messages(self.input_fn, user_content)
        return self._backend.complete(
            messages,
            self.output,
            self.model,
            max_retries=self.max_retries,
            params=self.params,
        )

    def stream(self, *args: object, **kwargs: object) -> Iterator[T]:
        """按字段逐步 yield partial 实例；最后一帧是完整实例。"""
        user_content = self.input_fn(*args, **kwargs)
        messages = _build_messages(self.input_fn, user_content)
        yield from self._backend.stream(
            messages,
            self.output,
            self.model,
            max_retries=self.max_retries,
            params=self.params,
        )


class AsyncStep[T: BaseModel]:
    """一次类型化的异步 LLM 调用。当 `@step` 装饰的是 `async def` 时自动生成。"""

    def __init__(
        self,
        input_fn: Callable[..., Awaitable[str] | str],
        output: type[T],
        *,
        client: Any,
        model: str = DEFAULT_MODEL,
        params: dict[str, Any] | None = None,
        max_retries: int = 0,
    ):
        self.input_fn = input_fn
        self.output = output
        self.model = model
        self.params = params
        self.max_retries = max_retries
        self._backend = _adapt_async_client(client)
        functools.update_wrapper(self, input_fn)
        self.__signature__ = _public_signature(input_fn, output)
        self.__annotations__ = _public_annotations(input_fn, output)

    async def __call__(self, *args: object, **kwargs: object) -> T:
        ret = self.input_fn(*args, **kwargs)
        user_content = await ret if inspect.isawaitable(ret) else ret
        messages = _build_messages(self.input_fn, user_content)
        return await self._backend.acomplete(
            messages,
            self.output,
            self.model,
            max_retries=self.max_retries,
            params=self.params,
        )

    async def astream(self, *args: object, **kwargs: object) -> AsyncIterator[T]:
        """异步流式输出。"""
        ret = self.input_fn(*args, **kwargs)
        user_content = await ret if inspect.isawaitable(ret) else ret
        messages = _build_messages(self.input_fn, user_content)
        async for partial in self._backend.astream(
            messages,
            self.output,
            self.model,
            max_retries=self.max_retries,
            params=self.params,
        ):
            yield partial


def step[T: BaseModel](
    *,
    output: type[T],
    client: Any,
    model: str = DEFAULT_MODEL,
    params: dict[str, Any] | None = None,
    max_retries: int = 0,
) -> Callable[[Callable[..., str] | Callable[..., Awaitable[str]]], Step[T] | AsyncStep[T]]:
    """装饰器：把输入函数变成一个类型化的 Step。

    - 同步 `def` 得到 `Step[T]`；异步 `async def` 得到 `AsyncStep[T]`。
    - `output` 的 Pydantic schema 定义这次调用的返回格式；字段顺序就是生成顺序。
    - 被装饰的 input builder 必须返回 `str`（异步版 await 后得到 `str`），
      它就是本次调用的 user message。
    - 装饰后绑定到原函数名的是 `Step[T]` / `AsyncStep[T]`，调用它会返回
      `output` 指定的 Pydantic 实例。
    - 函数 docstring 只用于 Python 文档，不会进入 messages。
    - `client` 必填。吃 `openai.OpenAI` / `openai.AsyncOpenAI` 或已经
      `instructor.from_openai(...)` 的实例；sync / async 不匹配会立即 `TypeError`。
    - `params`：字典，透传给 provider API（`temperature` / `max_tokens`
      / `seed` / `top_p` / `stop` / ...），不做枚举或校验。
    - `max_retries`：instructor 校验失败的重试次数，透传给 instructor。
    """

    def decorator(fn: Callable[..., str] | Callable[..., Awaitable[str]]) -> Step[T] | AsyncStep[T]:
        if inspect.iscoroutinefunction(fn):
            return AsyncStep(
                fn,
                output,
                client=client,
                model=model,
                params=params,
                max_retries=max_retries,
            )
        return Step(
            fn,
            output,
            client=client,
            model=model,
            params=params,
            max_retries=max_retries,
        )

    return decorator


def _build_messages(input_fn: Callable[..., Any], user_content: object) -> list[dict[str, str]]:
    if not isinstance(user_content, str):
        raise TypeError(
            f"@step 装饰的函数 {input_fn.__name__!r} 必须返回 str，"
            f"实际返回 {type(user_content).__name__}"
        )
    return [{"role": "user", "content": user_content}]


def _public_signature(input_fn: Callable[..., Any], output: type[BaseModel]) -> inspect.Signature:
    """公开签名表达装饰后的 callable：调用 step 返回 Pydantic 实例。"""
    return inspect.signature(input_fn).replace(return_annotation=output)


def _public_annotations(input_fn: Callable[..., Any], output: type[BaseModel]) -> dict[str, Any]:
    annotations = dict(getattr(input_fn, "__annotations__", {}))
    annotations["return"] = output
    return annotations
