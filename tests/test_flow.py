"""Flow 原语的测试 —— 规格 002。"""

from __future__ import annotations

from pydantic import BaseModel

from pyxis import FakeClient, flow, step, trace


class Observation(BaseModel):
    note: str


class Plan(BaseModel):
    action: str


def _analyze_client(*notes: str) -> FakeClient:
    return FakeClient([Observation(note=n) for n in notes])


def _plan_client(*actions: str) -> FakeClient:
    return FakeClient([Plan(action=a) for a in actions])


def test_flow_preserves_metadata():
    @flow
    def research(topic: str) -> str:
        """Research docstring."""
        return topic

    assert research.__name__ == "research"
    assert research.__doc__ == "Research docstring."


def test_flow_direct_call_works_like_function():
    analyze_fake = _analyze_client("o1")
    plan_fake = _plan_client("a1")

    @step(output=Observation, client=analyze_fake)
    def analyze(t: str) -> str:
        return t

    @step(output=Plan, client=plan_fake)
    def plan(obs: Observation) -> str:
        return obs.note

    @flow
    def research(topic: str) -> Plan:
        return plan(analyze(topic))

    result = research("AI")
    assert isinstance(result, Plan)
    assert result.action == "a1"


def test_run_traced_captures_records_in_order():
    analyze_fake = _analyze_client("obs")
    plan_fake = _plan_client("act")

    @step(output=Observation, client=analyze_fake)
    def analyze(t: str) -> str:
        return t

    @step(output=Plan, client=plan_fake)
    def plan(obs: Observation) -> str:
        return obs.note

    @flow
    def research(topic: str) -> Plan:
        return plan(analyze(topic))

    result, t = research.run_traced("AI")
    assert isinstance(result, Plan)
    assert len(t.records) == 2
    assert [r.step for r in t.records] == ["analyze", "plan"]

    first, second = t.records
    assert isinstance(first.output, Observation)
    assert first.output.note == "obs"
    assert second.output.action == "act"
    assert first.messages[-1] == {"role": "user", "content": "AI"}
    assert second.messages[-1] == {"role": "user", "content": "obs"}


def test_trace_context_captures_across_multiple_flow_calls():
    analyze_fake = _analyze_client("o1", "o2")
    plan_fake = _plan_client("a1", "a2")

    @step(output=Observation, client=analyze_fake)
    def analyze(t: str) -> str:
        return t

    @step(output=Plan, client=plan_fake)
    def plan(obs: Observation) -> str:
        return obs.note

    @flow
    def research(topic: str) -> Plan:
        return plan(analyze(topic))

    with trace() as t:
        research("one")
        research("two")

    assert len(t.records) == 4
    assert [r.step for r in t.records] == ["analyze", "plan", "analyze", "plan"]


def test_step_outside_trace_records_nothing():
    fake = _analyze_client("o1")

    @step(output=Observation, client=fake)
    def analyze(t: str) -> str:
        return t

    result = analyze("x")
    assert result.note == "o1"


def test_trace_captures_raw_step_calls_without_flow():
    fake = _analyze_client("o1", "o2")

    @step(output=Observation, client=fake)
    def analyze(t: str) -> str:
        return t

    with trace() as t:
        analyze("a")
        analyze("b")

    assert len(t.records) == 2
    assert [r.step for r in t.records] == ["analyze", "analyze"]


def test_nested_trace_inner_captures_outer_does_not():
    fake = _analyze_client("o1", "o2", "o3")

    @step(output=Observation, client=fake)
    def analyze(t: str) -> str:
        return t

    with trace() as outer:
        analyze("before")
        with trace() as inner:
            analyze("inside")
        analyze("after")

    assert [r.messages[-1]["content"] for r in outer.records] == ["before", "after"]
    assert [r.messages[-1]["content"] for r in inner.records] == ["inside"]


def test_trace_record_fields():
    fake = _analyze_client("captured")

    @step(output=Observation, model="gpt-4o", client=fake)
    def analyze(t: str) -> str:
        """Analyzer."""
        return t

    with trace() as t:
        analyze("x")

    (rec,) = t.records
    assert rec.step == "analyze"
    assert rec.model == "gpt-4o"
    assert isinstance(rec.output, Observation)
    assert rec.output.note == "captured"
    assert {"role": "system", "content": "Analyzer."} in rec.messages
    assert {"role": "user", "content": "x"} in rec.messages


def test_run_traced_does_not_leak_to_outer_trace():
    fake = _analyze_client("inner", "outer")

    @step(output=Observation, client=fake)
    def analyze(t: str) -> str:
        return t

    @flow
    def do_it(x: str) -> Observation:
        return analyze(x)

    with trace() as outer:
        do_it.run_traced("inner")
        analyze("outer")

    # run_traced has its own scope; only the raw `analyze("outer")` reaches outer.
    assert len(outer.records) == 1
    assert outer.records[0].messages[-1]["content"] == "outer"
