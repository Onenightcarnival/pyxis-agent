"""流式输出的测试 —— 规格 010。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from pyxis import FakeClient, step


class Plan(BaseModel):
    goal: str
    next_action: str


def test_step_stream_yields_final_frame():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        """规划。"""
        return x

    frames = list(plan.stream("hello"))
    assert len(frames) == 1
    assert isinstance(frames[0], Plan)
    assert frames[0].goal == "g"


def test_step_stream_exhaustion_reraises():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with pytest.raises(RuntimeError, match="耗尽"):
        list(plan.stream("x"))


async def test_async_step_astream_yields_final_frame():
    fake = FakeClient([Plan(goal="async", next_action="a")])

    @step(output=Plan, client=fake)
    async def aplan(x: str) -> str:
        return x

    frames = []
    async for f in aplan.astream("x"):
        frames.append(f)
    assert len(frames) == 1
    assert frames[0].goal == "async"


async def test_async_step_astream_exhaustion_reraises():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    async def aplan(x: str) -> str:
        return x

    with pytest.raises(RuntimeError, match="耗尽"):
        async for _ in aplan.astream("x"):
            pass


def test_fake_client_stream_records_call():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        """Sys."""
        return x

    list(plan.stream("hello"))
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call.messages == [{"role": "user", "content": "hello"}]


def test_plain_call_still_works_alongside_stream():
    fake = FakeClient([Plan(goal="a", next_action="x"), Plan(goal="b", next_action="y")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    r1 = plan("1")
    frames = list(plan.stream("2"))
    assert r1.goal == "a"
    assert frames[0].goal == "b"


def test_step_stream_forwards_params():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake, params={"temperature": 0.7})
    def plan(x: str) -> str:
        return x

    list(plan.stream("hi"))
    assert fake.calls[0].params == {"temperature": 0.7}
