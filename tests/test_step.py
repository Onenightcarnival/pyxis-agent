"""Step 原语的测试 —— 规格 001。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from pyxis import FakeClient, set_default_client, step


class Plan(BaseModel):
    goal: str
    next_action: str


class Analysis(BaseModel):
    observation: str
    conclusion: str


def test_step_returns_schema_instance():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        """You are a planner."""
        return f"Request: {req}"

    result = plan("build x")
    assert isinstance(result, Plan)
    assert result.goal == "g"
    assert result.next_action == "a"


def test_step_builds_system_and_user_messages():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        """You are a planner."""
        return f"Request: {req}"

    plan("build x")
    call = fake.calls[0]
    assert call.messages == [
        {"role": "system", "content": "You are a planner."},
        {"role": "user", "content": "Request: build x"},
    ]
    assert call.response_model is Plan


def test_step_strips_docstring_whitespace():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        """
        You are a planner.
        """
        return req

    plan("x")
    assert fake.calls[0].messages[0]["content"] == "You are a planner."


def test_step_omits_system_when_no_docstring():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        return req

    plan("hi")
    assert fake.calls[0].messages == [{"role": "user", "content": "hi"}]


def test_step_preserves_function_metadata():
    @step(output=Plan, client=FakeClient([]))
    def plan(req: str) -> str:
        """Planner docstring."""
        return req

    assert plan.__name__ == "plan"
    assert plan.__doc__ == "Planner docstring."


def test_fake_client_exhausted_raises():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        return req

    with pytest.raises(RuntimeError, match="耗尽"):
        plan("x")


def test_fake_client_type_mismatch_raises():
    fake = FakeClient([Analysis(observation="o", conclusion="c")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        return req

    with pytest.raises(TypeError, match="Plan"):
        plan("x")


def test_global_default_client():
    fake = FakeClient([Plan(goal="global", next_action="a")])
    set_default_client(fake)
    try:

        @step(output=Plan)
        def plan(req: str) -> str:
            return req

        result = plan("x")
        assert result.goal == "global"
    finally:
        set_default_client(None)


def test_explicit_client_beats_global_default():
    global_fake = FakeClient([Plan(goal="global", next_action="a")])
    explicit_fake = FakeClient([Plan(goal="explicit", next_action="a")])
    set_default_client(global_fake)
    try:

        @step(output=Plan, client=explicit_fake)
        def plan(req: str) -> str:
            return req

        result = plan("x")
        assert result.goal == "explicit"
        assert len(global_fake.calls) == 0
        assert len(explicit_fake.calls) == 1
    finally:
        set_default_client(None)


def test_step_forwards_model_param():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, model="gpt-4o", client=fake)
    def plan(req: str) -> str:
        return req

    plan("x")
    assert fake.calls[0].model == "gpt-4o"


def test_step_default_model_is_gpt4o_mini():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        return req

    plan("x")
    assert fake.calls[0].model == "gpt-4o-mini"


def test_fake_client_sequential_responses():
    fake = FakeClient(
        [
            Plan(goal="first", next_action="a"),
            Plan(goal="second", next_action="b"),
        ]
    )

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        return req

    r1 = plan("1")
    r2 = plan("2")
    assert r1.goal == "first"
    assert r2.goal == "second"
    assert len(fake.calls) == 2
