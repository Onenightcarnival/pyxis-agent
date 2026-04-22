"""异步支持的测试 —— 规格 004。"""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from pyxis import FakeClient, flow, step
from pyxis.flow import AsyncFlow, Flow
from pyxis.step import AsyncStep, Step


class Analysis(BaseModel):
    observation: str
    conclusion: str


class Plan(BaseModel):
    action: str


def _fake(*analyses: str) -> FakeClient:
    return FakeClient([Analysis(observation=o, conclusion="c") for o in analyses])


async def test_async_step_returns_schema_instance():
    fake = _fake("async-o")

    @step(output=Analysis, client=fake)
    async def analyze(t: str) -> str:
        """Async planner."""
        return t

    assert isinstance(analyze, AsyncStep)
    result = await analyze("x")
    assert isinstance(result, Analysis)
    assert result.observation == "async-o"


async def test_async_step_builds_messages_like_sync():
    fake = _fake("o")

    @step(output=Analysis, client=fake)
    async def analyze(t: str) -> str:
        """Sys prompt."""
        return t

    await analyze("hello")
    call = fake.calls[0]
    assert call.messages == [
        {"role": "system", "content": "Sys prompt."},
        {"role": "user", "content": "hello"},
    ]
    assert call.response_model is Analysis


async def test_fake_client_acomplete_returns_response_directly():
    fake = _fake("x")
    result = await fake.acomplete(
        messages=[{"role": "user", "content": "hi"}],
        response_model=Analysis,
        model="gpt-4o-mini",
    )
    assert isinstance(result, Analysis)
    assert result.observation == "x"
    assert len(fake.calls) == 1


async def test_sync_step_still_works_after_async_added():
    fake = _fake("sync-o")

    @step(output=Analysis, client=fake)
    def analyze(t: str) -> str:
        return t

    assert isinstance(analyze, Step)
    assert not isinstance(analyze, AsyncStep)
    result = analyze("x")
    assert result.observation == "sync-o"


async def test_async_flow_preserves_metadata_and_calls():
    fake = _fake("o", "p")

    @step(output=Analysis, client=fake)
    async def analyze(t: str) -> str:
        return t

    @flow
    async def research(topic: str) -> Analysis:
        """Async research."""
        a = await analyze(topic)
        return await analyze(a.observation)

    assert isinstance(research, AsyncFlow)
    assert research.__name__ == "research"
    assert research.__doc__ == "Async research."

    result = await research("topic")
    assert isinstance(result, Analysis)


async def test_sync_flow_still_works_after_async_added():
    fake = FakeClient([Analysis(observation="sync", conclusion="c")])

    @step(output=Analysis, client=fake)
    def analyze(t: str) -> str:
        return t

    @flow
    def research(topic: str) -> Analysis:
        return analyze(topic)

    assert isinstance(research, Flow)
    assert not isinstance(research, AsyncFlow)
    assert research("x").observation == "sync"


async def test_async_gather_runs_in_parallel():
    fake = FakeClient([Analysis(observation=f"o{i}", conclusion="c") for i in range(5)])

    @step(output=Analysis, client=fake)
    async def analyze(t: str) -> str:
        return t

    results = await asyncio.gather(*(analyze(f"task-{i}") for i in range(5)))
    assert len(results) == 5
    assert len(fake.calls) == 5


async def test_async_step_with_tool_output():
    """End-to-end: async agent decision step emitting a Tool."""
    from typing import Annotated, Literal

    from pydantic import Field

    from pyxis import Tool

    class Calc(Tool):
        kind: Literal["calc"] = "calc"
        expression: str

        def run(self) -> str:
            return "42"

    class Done(Tool):
        kind: Literal["done"] = "done"

        def run(self) -> str:
            return "stopped"

    Action = Annotated[Calc | Done, Field(discriminator="kind")]

    class Decision(BaseModel):
        action: Action

    fake = FakeClient([Decision(action=Calc(expression="6*7"))])

    @step(output=Decision, client=fake)
    async def decide(q: str) -> str:
        return q

    d = await decide("math")
    assert isinstance(d.action, Calc)
    assert d.action.run() == "42"


async def test_fake_client_exhausted_raises_on_async_path():
    fake = FakeClient([])

    @step(output=Analysis, client=fake)
    async def analyze(t: str) -> str:
        return t

    with pytest.raises(RuntimeError, match="耗尽"):
        await analyze("x")
