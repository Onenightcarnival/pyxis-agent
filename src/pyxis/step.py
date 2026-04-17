"""Step primitive: one LLM call with schema-as-CoT.

code-as-prompt : the function's docstring is the system prompt,
                 the function's string return value is the user message.
schema-as-CoT  : the output Pydantic model's field order is the reasoning chain.

`@step` detects `async def` prompt functions and dispatches to `AsyncStep`.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from .client import Message, get_default_client
from .trace import TraceRecord, record

DEFAULT_MODEL = "gpt-4o-mini"


class Step[T: BaseModel]:
    """A typed sync LLM call. Usually built via `@step(output=...)`."""

    def __init__(
        self,
        prompt_fn: Callable[..., str],
        output: type[T],
        *,
        model: str = DEFAULT_MODEL,
        client: Any = None,
    ):
        self.prompt_fn = prompt_fn
        self.output = output
        self.model = model
        self.client = client
        self.system_prompt: str = _normalize_docstring(prompt_fn.__doc__ or "")
        functools.update_wrapper(self, prompt_fn)

    def __call__(self, *args: object, **kwargs: object) -> T:
        user_content = self.prompt_fn(*args, **kwargs)
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
        client = self.client or get_default_client()
        result: T = client.complete(messages, self.output, self.model)
        record(
            TraceRecord(
                step=self.__name__,
                messages=messages,
                output=result,
                model=self.model,
            )
        )
        return result


class AsyncStep[T: BaseModel]:
    """A typed async LLM call. Built by `@step` when the prompt fn is `async def`."""

    def __init__(
        self,
        prompt_fn: Callable[..., Awaitable[str] | str],
        output: type[T],
        *,
        model: str = DEFAULT_MODEL,
        client: Any = None,
    ):
        self.prompt_fn = prompt_fn
        self.output = output
        self.model = model
        self.client = client
        self.system_prompt: str = _normalize_docstring(prompt_fn.__doc__ or "")
        functools.update_wrapper(self, prompt_fn)

    async def __call__(self, *args: object, **kwargs: object) -> T:
        ret = self.prompt_fn(*args, **kwargs)
        user_content = await ret if inspect.isawaitable(ret) else ret
        messages = _build_messages(self.prompt_fn, self.system_prompt, user_content)
        client = self.client or get_default_client()
        result: T = await client.acomplete(messages, self.output, self.model)
        record(
            TraceRecord(
                step=self.__name__,
                messages=messages,
                output=result,
                model=self.model,
            )
        )
        return result


def step[T: BaseModel](
    *,
    output: type[T],
    model: str = DEFAULT_MODEL,
    client: Any = None,
) -> Callable[[Callable[..., Any]], Step[T] | AsyncStep[T]]:
    """Decorator: turn a prompt function into a typed Step.

    Sync `def` -> `Step[T]`. Async `async def` -> `AsyncStep[T]`.
    Either way, the docstring is the system prompt, the return string is
    the user message, and `output=` declares the structured reply schema.
    """

    def decorator(fn: Callable[..., Any]) -> Step[T] | AsyncStep[T]:
        if inspect.iscoroutinefunction(fn):
            return AsyncStep(fn, output, model=model, client=client)
        return Step(fn, output, model=model, client=client)

    return decorator


def _build_messages(
    prompt_fn: Callable[..., Any], system_prompt: str, user_content: object
) -> list[Message]:
    if not isinstance(user_content, str):
        raise TypeError(
            f"@step function {prompt_fn.__name__!r} must return str, "
            f"got {type(user_content).__name__}"
        )
    messages: list[Message] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})
    return messages


def _normalize_docstring(doc: str) -> str:
    return inspect.cleandoc(doc).strip()
