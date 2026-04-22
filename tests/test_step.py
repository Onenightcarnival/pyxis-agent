"""Step 原语的测试 —— 规格 001 / 023。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from pyxis import FakeClient, step


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


def test_step_requires_client():
    """`client` 是必填关键字参数；不传要在装饰时就失败。"""
    with pytest.raises(TypeError):

        @step(output=Plan)  # type: ignore[call-arg]
        def plan(req: str) -> str:
            return req


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


def test_step_default_max_retries_is_zero():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        return req

    plan("x")
    assert fake.calls[0].max_retries == 0


def test_step_max_retries_is_forwarded():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, max_retries=3, client=fake)
    def plan(req: str) -> str:
        return req

    plan("x")
    assert fake.calls[0].max_retries == 3


def test_step_params_forwarded_to_fake_client():
    """`params` 字典哑透传到 `FakeCall.params`——测试可断言采样参数。"""
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake, params={"temperature": 0, "max_tokens": 500})
    def plan(req: str) -> str:
        return req

    plan("x")
    assert fake.calls[0].params == {"temperature": 0, "max_tokens": 500}


def test_step_params_defaults_to_none():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        return req

    plan("x")
    assert fake.calls[0].params is None


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


def test_step_rejects_async_openai_on_sync_def():
    """同步 def 拿到 AsyncOpenAI → 立即 TypeError。"""
    from openai import AsyncOpenAI

    async_client = AsyncOpenAI(api_key="sk-fake", base_url="http://localhost")
    with pytest.raises(TypeError, match="AsyncOpenAI"):

        @step(output=Plan, client=async_client)
        def plan(req: str) -> str:
            return req


def test_async_step_rejects_sync_openai():
    """async def 拿到 OpenAI（同步）→ 立即 TypeError。"""
    from openai import OpenAI

    sync_client = OpenAI(api_key="sk-fake", base_url="http://localhost")
    with pytest.raises(TypeError, match="OpenAI"):

        @step(output=Plan, client=sync_client)
        async def plan(req: str) -> str:
            return req
