"""流式输出的测试 —— 规格 010。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from pyxis import FakeClient, step, trace


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


def test_step_stream_records_trace_after_full_consumption():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        frames = list(plan.stream("hello"))

    assert len(frames) == 1
    assert len(t.records) == 1
    rec = t.records[0]
    assert rec.step == "plan"
    assert rec.output == Plan(goal="g", next_action="a")
    assert rec.usage is None
    assert rec.error is None


def test_step_stream_outside_trace_does_nothing_to_trace():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    # 不在 trace() 里也能正常 stream
    frames = list(plan.stream("x"))
    assert frames[0].goal == "g"


def test_step_stream_exhaustion_records_error_and_reraises():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t, pytest.raises(RuntimeError, match="耗尽"):
        list(plan.stream("x"))

    (rec,) = t.records
    assert rec.output is None
    assert rec.error is not None
    assert "耗尽" in rec.error


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


async def test_async_step_astream_records_trace():
    fake = FakeClient([Plan(goal="async", next_action="a")])

    @step(output=Plan, client=fake)
    async def aplan(x: str) -> str:
        return x

    with trace() as t:
        async for _ in aplan.astream("x"):
            pass

    assert len(t.records) == 1
    assert t.records[0].output == Plan(goal="async", next_action="a")
    assert t.records[0].error is None


async def test_async_step_astream_exhaustion_records_error_and_reraises():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    async def aplan(x: str) -> str:
        return x

    with trace() as t, pytest.raises(RuntimeError, match="耗尽"):
        async for _ in aplan.astream("x"):
            pass

    (rec,) = t.records
    assert rec.error is not None
    assert rec.output is None


def test_fake_client_stream_records_call():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        """Sys."""
        return x

    list(plan.stream("hello"))
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call.messages == [
        {"role": "system", "content": "Sys."},
        {"role": "user", "content": "hello"},
    ]


def test_plain_call_still_works_alongside_stream():
    fake = FakeClient([Plan(goal="a", next_action="x"), Plan(goal="b", next_action="y")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    r1 = plan("1")  # 普通阻塞式
    frames = list(plan.stream("2"))  # 流式
    assert r1.goal == "a"
    assert frames[0].goal == "b"
