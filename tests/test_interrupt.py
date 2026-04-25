"""Interrupt 的测试 —— 规格 012。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from pyxis import (
    FakeClient,
    InterruptRequest,
    ask_interrupt,
    finish,
    flow,
    run_aflow,
    run_flow,
    step,
)


class Plan(BaseModel):
    goal: str
    next_action: str


class Decision(BaseModel):
    approve: bool
    comments: str | None = None


def _queued(answers):
    """把一个列表包成顺序发答的 on_interrupt。"""
    it = iter(answers)

    def _on_interrupt(q):
        return next(it)

    return _on_interrupt


def test_ask_interrupt_builds_request_dataclass():
    q = ask_interrupt("批准吗", schema=Decision, plan={"x": 1})
    assert isinstance(q, InterruptRequest)
    assert q.question == "批准吗"
    assert q.schema is Decision
    assert q.context == {"plan": {"x": 1}}


def test_ask_interrupt_without_schema_or_context():
    q = ask_interrupt("继续？")
    assert q.schema is None
    assert q.context == {}


def test_run_flow_drives_generator_with_on_interrupt():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    @step(output=Plan, client=fake)
    def make_plan(topic: str) -> str:
        return topic

    @flow
    def review(topic: str):
        plan = make_plan(topic)
        decision: Decision = yield ask_interrupt("审核", schema=Decision, plan=plan.goal)
        if not decision.approve:
            return {"status": "rejected"}
        return {"status": "done", "goal": plan.goal}

    result = run_flow(review("x"), on_interrupt=_queued([Decision(approve=True)]))
    assert result == {"status": "done", "goal": "g"}


def test_run_flow_schema_validates_plain_dict_answer():
    @flow
    def review(_q):
        ans: Decision = yield ask_interrupt("?", schema=Decision)
        return ans.approve

    result = run_flow(review("q"), on_interrupt=_queued([{"approve": True}]))
    assert result is True


def test_run_flow_passes_non_model_answer_through():
    @flow
    def ask_twice():
        a = yield ask_interrupt("your name?")
        b = yield ask_interrupt("and your team?")
        return f"{a}@{b}"

    result = run_flow(ask_twice(), on_interrupt=_queued(["chao", "pyxis"]))
    assert result == "chao@pyxis"


def test_run_flow_rejects_non_interrupt_request_yield():
    @flow
    def bad():
        yield "不是 InterruptRequest"

    with pytest.raises(TypeError, match="InterruptRequest"):
        run_flow(bad(), on_interrupt=lambda q: None)


def test_run_flow_generator_with_no_yield_works_like_plain_flow():
    @flow
    def trivial():
        yield from ()  # 这里纯粹声明这是生成器，但从不 yield
        return 42

    result = run_flow(trivial(), on_interrupt=lambda q: None)
    assert result == 42


def test_run_flow_exception_in_generator_propagates():
    @flow
    def boom():
        yield ask_interrupt("q")
        raise ValueError("炸了")

    with pytest.raises(ValueError, match="炸了"):
        run_flow(boom(), on_interrupt=_queued(["ok"]))


def test_multi_turn_conversation_via_interrupt():
    @flow
    def chat():
        history: list[tuple[str, str]] = []
        for _ in range(3):
            user = yield ask_interrupt("你说：")
            if user == "exit":
                break
            history.append(("user", user))
        return history

    result = run_flow(
        chat(),
        on_interrupt=_queued(["你好", "再聊聊 schema-as-CoT", "exit"]),
    )
    assert result == [("user", "你好"), ("user", "再聊聊 schema-as-CoT")]


def test_step_calls_across_yields_are_captured_by_fake_client():
    fake = FakeClient(
        [
            Plan(goal="g1", next_action="a"),
            Plan(goal="g2", next_action="a"),
        ]
    )

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    @flow
    def interactive():
        first = plan("1")
        _ = yield ask_interrupt("审第一步", plan=first.goal)
        second = plan("2")
        _ = yield ask_interrupt("审第二步", plan=second.goal)
        return (first.goal, second.goal)

    result = run_flow(interactive(), on_interrupt=_queued([True, True]))

    assert result == ("g1", "g2")
    assert len(fake.calls) == 2


async def test_run_aflow_with_sync_generator_and_sync_on_interrupt():
    @flow
    def review(_q):
        a = yield ask_interrupt("?")
        return a

    result = await run_aflow(review("q"), on_interrupt=_queued(["ok"]))
    assert result == "ok"


async def test_run_aflow_with_async_generator_and_sync_on_interrupt():
    @flow
    async def review(_q):
        a = yield ask_interrupt("?")
        yield finish(a)

    result = await run_aflow(review("q"), on_interrupt=_queued(["ok"]))
    assert result == "ok"


async def test_run_aflow_awaits_async_on_interrupt():
    async def on_interrupt(q):
        return "async-answer"

    @flow
    async def review(_q):
        a = yield ask_interrupt("?")
        yield finish(a)

    result = await run_aflow(review("q"), on_interrupt=on_interrupt)
    assert result == "async-answer"


async def test_run_aflow_schema_validates_answer():
    @flow
    async def review():
        d: Decision = yield ask_interrupt("?", schema=Decision)
        yield finish(d.approve)

    result = await run_aflow(review(), on_interrupt=_queued([{"approve": False}]))
    assert result is False


async def test_run_aflow_propagates_exception_from_generator():
    @flow
    async def boom():
        yield ask_interrupt("?")
        raise RuntimeError("aboom")

    with pytest.raises(RuntimeError, match="aboom"):
        await run_aflow(boom(), on_interrupt=_queued(["x"]))


def test_run_flow_accepts_finish_sentinel_in_sync_gen():
    @flow
    def review():
        a = yield ask_interrupt("?")
        yield finish({"chosen": a})
        raise RuntimeError("不应执行到这里")

    result = run_flow(review(), on_interrupt=_queued(["yes"]))
    assert result == {"chosen": "yes"}


async def test_run_aflow_finish_without_answer_question():
    @flow
    async def immediate():
        yield finish(42)

    result = await run_aflow(immediate(), on_interrupt=_queued([]))
    assert result == 42


def test_generator_flow_preserves_metadata():
    @flow
    def interactive(x: str):
        """互动式的 flow。"""
        yield ask_interrupt("?")
        return x

    assert interactive.__name__ == "interactive"
    assert interactive.__doc__ == "互动式的 flow。"
