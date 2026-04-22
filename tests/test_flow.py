"""Flow 原语的测试 —— 规格 002。

收敛后 `@flow` 只剩"语义标记 + sync/async 分派"。调用断言改用
`FakeClient.calls` 而不是 `trace()`。"""

from __future__ import annotations

from pydantic import BaseModel

from pyxis import FakeClient, flow, step


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


def test_flow_calls_captured_across_fake_clients():
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

    result = research("AI")
    assert isinstance(result, Plan)
    assert result.action == "act"

    assert len(analyze_fake.calls) == 1
    assert analyze_fake.calls[0].messages[-1] == {"role": "user", "content": "AI"}
    assert len(plan_fake.calls) == 1
    assert plan_fake.calls[0].messages[-1] == {"role": "user", "content": "obs"}


def test_multiple_flow_invocations_accumulate_calls():
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

    research("one")
    research("two")

    assert len(analyze_fake.calls) == 2
    assert len(plan_fake.calls) == 2
    topics = [c.messages[-1]["content"] for c in analyze_fake.calls]
    assert topics == ["one", "two"]
