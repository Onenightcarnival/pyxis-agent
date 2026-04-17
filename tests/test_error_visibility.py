"""错误可见性的测试 —— 规格 009。"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from pyxis import FakeClient, step, trace


class Plan(BaseModel):
    goal: str
    next_action: str


class _BoomClient:
    """永远抛自定义异常的 client，用来触发任意 Exception 路径。"""

    def complete(self, messages, response_model, model, *, max_retries=0):
        raise RuntimeError("外部服务炸了")

    async def acomplete(self, messages, response_model, model, *, max_retries=0):
        raise RuntimeError("外部服务炸了")


def test_fake_client_exhaustion_recorded_as_error():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        """规划。"""
        return x

    with trace() as t, pytest.raises(RuntimeError, match="耗尽"):
        plan("x")

    assert len(t.records) == 1
    (rec,) = t.records
    assert rec.step == "plan"
    assert rec.output is None
    assert rec.error is not None
    assert "耗尽" in rec.error
    assert "RuntimeError" in rec.error
    # messages 仍然被记录，方便重现
    assert rec.messages[-1] == {"role": "user", "content": "x"}


def test_arbitrary_exception_recorded_and_reraised():
    @step(output=Plan, client=_BoomClient())
    def plan(x: str) -> str:
        return x

    with trace() as t, pytest.raises(RuntimeError, match="外部服务炸了"):
        plan("x")

    (rec,) = t.records
    assert rec.output is None
    assert rec.error is not None
    assert "RuntimeError" in rec.error
    assert "外部服务炸了" in rec.error


async def test_async_path_also_records_errors():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    async def plan(x: str) -> str:
        return x

    with trace() as t, pytest.raises(RuntimeError, match="耗尽"):
        await plan("x")

    (rec,) = t.records
    assert rec.output is None
    assert rec.error is not None


def test_errors_helper_filters():
    fake = FakeClient(
        [
            Plan(goal="ok", next_action="a"),
            # 第二次调用会耗尽
        ]
    )

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        plan("first")
        with pytest.raises(RuntimeError):
            plan("second")

    assert len(t.records) == 2
    assert len(t.errors()) == 1
    assert t.errors()[0].messages[-1]["content"] == "second"


def test_successful_record_has_error_none():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        plan("x")

    (rec,) = t.records
    assert rec.error is None
    assert isinstance(rec.output, Plan)


def test_trace_to_dict_serializes_error_and_null_output():
    @step(output=Plan, client=_BoomClient())
    def plan(x: str) -> str:
        return x

    with trace() as t, pytest.raises(RuntimeError):
        plan("x")

    d = t.to_dict()
    rec = d["records"][0]
    assert rec["output"] is None
    assert rec["error"].startswith("RuntimeError")

    # to_json + json.loads 能回到同一个 dict
    round_trip = json.loads(t.to_json())
    assert round_trip["records"][0]["output"] is None
    assert "外部服务炸了" in round_trip["records"][0]["error"]


def test_successful_record_serializes_error_as_null():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        plan("x")

    d = t.to_dict()
    assert "error" in d["records"][0]
    assert d["records"][0]["error"] is None
