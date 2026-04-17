"""LLM client abstraction.

A `Client` makes one structured LLM call: messages + response model ->
`CompletionResult[T]` (output + optional usage). Production uses
`InstructorClient`; tests use `FakeClient`. Both ship sync and async paths.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

Message = dict[str, str]


@dataclass
class Usage:
    """Token accounting for one LLM call. Zero-initialized by default."""

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
    """Result of a single structured completion: the parsed output plus usage."""

    output: T
    usage: Usage | None = None


@runtime_checkable
class Client(Protocol):
    """Minimal structured-completion interface (sync)."""

    def complete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> CompletionResult[T]: ...


@runtime_checkable
class AsyncClient(Protocol):
    """Async sibling of `Client`."""

    async def acomplete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
        *,
        max_retries: int = 0,
    ) -> CompletionResult[T]: ...


@dataclass
class FakeCall:
    """One call recorded by `FakeClient`."""

    messages: list[Message]
    response_model: type[BaseModel]
    model: str
    max_retries: int = 0


class FakeClient:
    """Deterministic client for tests — returns queued responses in order.

    Accepts an optional parallel list of `usages`; each call pops one (or None
    if the list is exhausted / shorter than responses). Implements both
    `Client` and `AsyncClient` protocols.
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
                f"FakeClient exhausted after {self._cursor} call(s); "
                f"no canned response for call #{self._cursor + 1} "
                f"(expected {response_model.__name__})"
            )
        resp = self._responses[self._cursor]
        usage = self._usages[self._cursor] if self._cursor < len(self._usages) else None
        self._cursor += 1
        if not isinstance(resp, response_model):
            raise TypeError(
                f"FakeClient response #{self._cursor} is "
                f"{type(resp).__name__}, expected {response_model.__name__}"
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


def _extract_usage(raw: Any) -> Usage | None:
    """Pull a `Usage` out of an OpenAI-shaped raw response. Best-effort."""
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
    """Instructor-backed client; sync + async.

    Both backends are lazily constructed from OpenAI defaults when unset.
    Pass pre-patched instructor clients to swap providers (Anthropic, etc.).
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


@dataclass
class _DefaultClient:
    client: Any = None
    _lazy: Any = field(default=None, repr=False)


_default = _DefaultClient()


def set_default_client(client: Any) -> None:
    """Install a process-wide default client. `None` resets to lazy InstructorClient."""
    _default.client = client
    _default._lazy = None


def get_default_client() -> Any:
    """Resolve the current default client, lazily constructing InstructorClient."""
    if _default.client is not None:
        return _default.client
    if _default._lazy is None:
        _default._lazy = InstructorClient()
    return _default._lazy
