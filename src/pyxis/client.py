"""LLM client abstraction.

A `Client` makes one structured LLM call: messages + response model -> instance.
Production uses `InstructorClient` (instructor-patched provider SDK).
Tests use `FakeClient` (canned responses, no network).
Both ship sync and async variants.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

Message = dict[str, str]


@runtime_checkable
class Client(Protocol):
    """Minimal structured-completion interface (sync)."""

    def complete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
    ) -> T: ...


@runtime_checkable
class AsyncClient(Protocol):
    """Async sibling of `Client`."""

    async def acomplete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
    ) -> T: ...


@dataclass
class FakeCall:
    """One call recorded by `FakeClient`."""

    messages: list[Message]
    response_model: type[BaseModel]
    model: str


class FakeClient:
    """Deterministic client for tests — returns queued responses in order.

    Implements both `Client` and `AsyncClient` protocols. The async path
    delegates to the sync path (same queue, same call log, same errors).
    """

    def __init__(self, responses: Iterable[BaseModel]):
        self._responses: list[BaseModel] = list(responses)
        self._cursor: int = 0
        self.calls: list[FakeCall] = []

    def complete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
    ) -> T:
        self.calls.append(
            FakeCall(messages=list(messages), response_model=response_model, model=model)
        )
        if self._cursor >= len(self._responses):
            raise RuntimeError(
                f"FakeClient exhausted after {self._cursor} call(s); "
                f"no canned response for call #{self._cursor + 1} "
                f"(expected {response_model.__name__})"
            )
        resp = self._responses[self._cursor]
        self._cursor += 1
        if not isinstance(resp, response_model):
            raise TypeError(
                f"FakeClient response #{self._cursor} is "
                f"{type(resp).__name__}, expected {response_model.__name__}"
            )
        return resp

    async def acomplete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
    ) -> T:
        return self.complete(messages, response_model, model)


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
    ) -> T:
        return self._get_sync().chat.completions.create(  # type: ignore[no-any-return]
            messages=messages,
            response_model=response_model,
            model=model,
        )

    async def acomplete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
    ) -> T:
        return await self._get_async().chat.completions.create(
            messages=messages,
            response_model=response_model,
            model=model,
        )


@dataclass
class _DefaultClient:
    client: Any = None
    _lazy: Any = field(default=None, repr=False)


_default = _DefaultClient()


def set_default_client(client: Any) -> None:
    """Install a process-wide default client. `None` resets to lazy InstructorClient.

    The client should implement `Client` and/or `AsyncClient` depending on
    which step flavors you'll use.
    """
    _default.client = client
    _default._lazy = None


def get_default_client() -> Any:
    """Resolve the current default client, lazily constructing InstructorClient."""
    if _default.client is not None:
        return _default.client
    if _default._lazy is None:
        _default._lazy = InstructorClient()
    return _default._lazy
