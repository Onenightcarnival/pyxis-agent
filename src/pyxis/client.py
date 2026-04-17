"""LLM client abstraction.

A `Client` makes one structured LLM call: messages + response model -> instance.
Production uses `InstructorClient` (instructor-patched provider SDK).
Tests use `FakeClient` (canned responses, no network).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

Message = dict[str, str]


@runtime_checkable
class Client(Protocol):
    """Minimal structured-completion interface."""

    def complete[T: BaseModel](
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

    Queued responses are returned sequentially regardless of call site.
    Each call is appended to `.calls` for assertion.

    Raises `RuntimeError` when exhausted; `TypeError` when a queued response
    isn't an instance of the requested `response_model`.
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


class InstructorClient:
    """Instructor-backed client. Default = `instructor.from_openai(OpenAI())`.

    Pass a pre-patched instructor client to swap providers (Anthropic, etc.).
    """

    def __init__(self, instructor_client: Any = None):
        if instructor_client is None:
            import instructor
            from openai import OpenAI

            instructor_client = instructor.from_openai(OpenAI())
        self._client = instructor_client

    def complete[T: BaseModel](
        self,
        messages: list[Message],
        response_model: type[T],
        model: str,
    ) -> T:
        return self._client.chat.completions.create(  # type: ignore[no-any-return]
            messages=messages,
            response_model=response_model,
            model=model,
        )


@dataclass
class _DefaultClient:
    client: Client | None = None
    _lazy: Client | None = field(default=None, repr=False)


_default = _DefaultClient()


def set_default_client(client: Client | None) -> None:
    """Install a process-wide default client. `None` resets to lazy InstructorClient."""
    _default.client = client
    _default._lazy = None


def get_default_client() -> Client:
    """Resolve the current default client, constructing `InstructorClient` lazily."""
    if _default.client is not None:
        return _default.client
    if _default._lazy is None:
        _default._lazy = InstructorClient()
    return _default._lazy
