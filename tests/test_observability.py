"""Tests for observability pack — spec 005."""

from __future__ import annotations

import json

from pydantic import BaseModel

from pyxis import (
    FakeClient,
    Trace,
    TraceRecord,
    Usage,
    step,
    trace,
)
from pyxis.client import CompletionResult


class Plan(BaseModel):
    goal: str
    next_action: str


def test_usage_defaults_to_zero():
    u = Usage()
    assert u.prompt_tokens == 0
    assert u.completion_tokens == 0
    assert u.total_tokens == 0


def test_completion_result_wraps_output_and_usage():
    r = CompletionResult(output=Plan(goal="g", next_action="a"))
    assert r.output.goal == "g"
    assert r.usage is None

    u = Usage(prompt_tokens=5, completion_tokens=3, total_tokens=8)
    r2 = CompletionResult(output=r.output, usage=u)
    assert r2.usage == u


def test_fake_client_without_usages_returns_none_on_record():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        plan("hi")

    assert t.records[0].usage is None


def test_fake_client_with_usages_attaches_to_record():
    u = Usage(prompt_tokens=10, completion_tokens=4, total_tokens=14)
    fake = FakeClient(
        responses=[Plan(goal="g", next_action="a")],
        usages=[u],
    )

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        plan("hi")

    assert t.records[0].usage == u


def test_step_default_max_retries_is_zero():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    plan("x")
    assert fake.calls[0].max_retries == 0


def test_step_max_retries_is_forwarded_to_client():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, max_retries=3, client=fake)
    def plan(x: str) -> str:
        return x

    plan("x")
    assert fake.calls[0].max_retries == 3


def test_trace_to_dict_serializes_records():
    fake = FakeClient(
        responses=[Plan(goal="g", next_action="a")],
        usages=[Usage(prompt_tokens=5, completion_tokens=3, total_tokens=8)],
    )

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        """Planner."""
        return x

    with trace() as t:
        plan("hello")

    d = t.to_dict()
    assert "records" in d
    assert len(d["records"]) == 1
    rec = d["records"][0]
    assert rec["step"] == "plan"
    assert rec["output"] == {"goal": "g", "next_action": "a"}
    assert rec["messages"][-1] == {"role": "user", "content": "hello"}
    assert rec["usage"] == {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
    assert rec["model"] == "gpt-4o-mini"


def test_trace_to_json_produces_valid_json():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        plan("hello")

    s = t.to_json()
    round_trip = json.loads(s)
    assert round_trip["records"][0]["step"] == "plan"


def test_trace_record_to_dict_handles_none_usage():
    rec = TraceRecord(
        step="s",
        messages=[{"role": "user", "content": "hi"}],
        output=Plan(goal="g", next_action="a"),
        model="gpt-4o-mini",
        usage=None,
    )
    d = rec.to_dict()
    assert d["usage"] is None
    assert d["output"] == {"goal": "g", "next_action": "a"}


def test_total_usage_zero_when_no_records():
    t = Trace()
    assert t.total_usage() == Usage()


def test_total_usage_sums_across_records_skipping_none():
    rec1 = TraceRecord(
        step="a",
        messages=[],
        output=Plan(goal="g", next_action="a"),
        model="m",
        usage=Usage(prompt_tokens=5, completion_tokens=3, total_tokens=8),
    )
    rec2 = TraceRecord(
        step="b",
        messages=[],
        output=Plan(goal="g", next_action="a"),
        model="m",
        usage=None,
    )
    rec3 = TraceRecord(
        step="c",
        messages=[],
        output=Plan(goal="g", next_action="a"),
        model="m",
        usage=Usage(prompt_tokens=2, completion_tokens=1, total_tokens=3),
    )
    t = Trace(records=[rec1, rec2, rec3])
    total = t.total_usage()
    assert total == Usage(prompt_tokens=7, completion_tokens=4, total_tokens=11)


async def test_async_step_captures_usage_too():
    u = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    fake = FakeClient(
        responses=[Plan(goal="g", next_action="a")],
        usages=[u],
    )

    @step(output=Plan, client=fake)
    async def plan(x: str) -> str:
        return x

    with trace() as t:
        await plan("x")

    assert t.records[0].usage == u


async def test_async_step_forwards_max_retries():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, max_retries=5, client=fake)
    async def plan(x: str) -> str:
        return x

    await plan("x")
    assert fake.calls[0].max_retries == 5


def test_usages_shorter_than_responses_gives_none():
    fake = FakeClient(
        responses=[
            Plan(goal="a", next_action="a"),
            Plan(goal="b", next_action="b"),
        ],
        usages=[Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2)],
    )

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        plan("1")
        plan("2")

    assert t.records[0].usage is not None
    assert t.records[1].usage is None
