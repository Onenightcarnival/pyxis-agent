"""Step primitive: one LLM call with schema-as-CoT.

code-as-prompt : the function's docstring is the system prompt,
                 the function's string return value is the user message.
schema-as-CoT  : the output Pydantic model's field order is the reasoning chain.
"""

from __future__ import annotations

import functools
from collections.abc import Callable

from pydantic import BaseModel

from .client import Client, Message, get_default_client

DEFAULT_MODEL = "gpt-4o-mini"


class Step[T: BaseModel]:
    """A typed LLM call. Usually built via `@step(output=...)`."""

    def __init__(
        self,
        prompt_fn: Callable[..., str],
        output: type[T],
        *,
        model: str = DEFAULT_MODEL,
        client: Client | None = None,
    ):
        self.prompt_fn = prompt_fn
        self.output = output
        self.model = model
        self.client = client
        doc = prompt_fn.__doc__ or ""
        self.system_prompt: str = _normalize_docstring(doc)
        functools.update_wrapper(self, prompt_fn)

    def __call__(self, *args: object, **kwargs: object) -> T:
        user_content = self.prompt_fn(*args, **kwargs)
        if not isinstance(user_content, str):
            raise TypeError(
                f"@step function {self.prompt_fn.__name__!r} must return str, "
                f"got {type(user_content).__name__}"
            )
        messages: list[Message] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_content})
        client = self.client or get_default_client()
        return client.complete(messages, self.output, self.model)


def step[T: BaseModel](
    *,
    output: type[T],
    model: str = DEFAULT_MODEL,
    client: Client | None = None,
) -> Callable[[Callable[..., str]], Step[T]]:
    """Decorator: turn a prompt function into a typed `Step`.

    The decorated function's docstring becomes the system prompt.
    Its return value (a string) becomes the user message.
    Its return *type annotation* is irrelevant; the structured output type
    is declared by `output=`.
    """

    def decorator(fn: Callable[..., str]) -> Step[T]:
        return Step(fn, output, model=model, client=client)

    return decorator


def _normalize_docstring(doc: str) -> str:
    """Strip surrounding whitespace and normalize indentation."""
    import inspect

    return inspect.cleandoc(doc).strip()
