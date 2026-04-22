"""Step：一次 LLM 调用 + 结构即思维链（schema-as-CoT）。

- code-as-prompt：函数 docstring 是 system prompt，字符串返回是 user
  message。
- schema-as-CoT：Pydantic 输出模型的字段顺序就是思维链——LLM 必须
  自上而下把它们填完。

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
        prompt_fn: Callable[..., str],
        output: type[T],
        *,
        client: Any,
        model: str = DEFAULT_MODEL,
        params: dict[str, Any] | None = None,
        max_retries: int = 0,
    ):
        self.prompt_fn = prompt_fn
        self.output = output
        self.model = model
        self.params = params
        self.max_retries = max_retries
        self.system_prompt: str = _normalize_docstring(prompt_fn.__doc__ or "")
        self._backend = _adapt_sync_client(client)
        functools.update_wrapper(self, prompt_fn)

    def __call__(self, *args: object, **kwargs: object) -> T:
        user_content = self.prompt_fn(*args, **kwargs)
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
        return self._backend.complete(
            messages,
            self.output,
            self.model,
            max_retries=self.max_retries,
            params=self.params,
        )

    def stream(self, *args: object, **kwargs: object) -> Iterator[T]:
        """按字段逐步 yield partial 实例；最后一帧即完整实例。"""
        user_content = self.prompt_fn(*args, **kwargs)
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
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
        prompt_fn: Callable[..., Awaitable[str] | str],
        output: type[T],
        *,
        client: Any,
        model: str = DEFAULT_MODEL,
        params: dict[str, Any] | None = None,
        max_retries: int = 0,
    ):
        self.prompt_fn = prompt_fn
        self.output = output
        self.model = model
        self.params = params
        self.max_retries = max_retries
        self.system_prompt: str = _normalize_docstring(prompt_fn.__doc__ or "")
        self._backend = _adapt_async_client(client)
        functools.update_wrapper(self, prompt_fn)

    async def __call__(self, *args: object, **kwargs: object) -> T:
        ret = self.prompt_fn(*args, **kwargs)
        user_content = await ret if inspect.isawaitable(ret) else ret
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
        return await self._backend.acomplete(
            messages,
            self.output,
            self.model,
            max_retries=self.max_retries,
            params=self.params,
        )

    async def astream(self, *args: object, **kwargs: object) -> AsyncIterator[T]:
        """异步流式对偶。"""
        ret = self.prompt_fn(*args, **kwargs)
        user_content = await ret if inspect.isawaitable(ret) else ret
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
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
) -> Callable[[Callable[..., Any]], Step[T] | AsyncStep[T]]:
    """装饰器：把 prompt 函数变成一个类型化的 Step。

    - 同步 `def` 得到 `Step[T]`；异步 `async def` 得到 `AsyncStep[T]`。
    - docstring 会被解析为 system prompt（会去首尾空白与缩进）。
    - 函数的返回值必须是 `str`，它就是 user message。
    - `client` 必填。吃 `openai.OpenAI` / `openai.AsyncOpenAI` 或已经
      `instructor.from_openai(...)` 的实例；sync / async 不匹配会立即 `TypeError`。
    - `params`：字典，透传给 provider API（`temperature` / `max_tokens`
      / `seed` / `top_p` / `stop` / ...），不做枚举或校验。
    - `max_retries`：instructor 校验失败的重试次数，透传给 instructor。
    """

    def decorator(fn: Callable[..., Any]) -> Step[T] | AsyncStep[T]:
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


def _build_messages(
    prompt_fn: Callable[..., Any], system_prompt: str, user_content: object
) -> list[dict[str, str]]:
    if not isinstance(user_content, str):
        raise TypeError(
            f"@step 装饰的函数 {prompt_fn.__name__!r} 必须返回 str，"
            f"实际返回 {type(user_content).__name__}"
        )
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})
    return messages


def _normalize_docstring(doc: str) -> str:
    """去首尾空白并规范化缩进，得到干净的 system prompt。"""
    return inspect.cleandoc(doc).strip()
