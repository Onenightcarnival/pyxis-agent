"""StepHook 的测试 —— 规格 011。"""

from __future__ import annotations

import warnings

import pytest
from pydantic import BaseModel

from pyxis import FakeClient, StepHook, add_hook, clear_hooks, remove_hook, step, trace


class Plan(BaseModel):
    goal: str
    next_action: str


@pytest.fixture(autouse=True)
def _clear_hooks_between_tests():
    yield
    clear_hooks()


class _Recorder(StepHook):
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def on_start(self, step, messages, model):
        self.events.append(("start", step))

    def on_end(self, record):
        self.events.append(("end", record.step))

    def on_error(self, step, messages, model, error):
        self.events.append(("error", step))


def test_default_hook_methods_are_noop():
    hook = StepHook()
    # 不崩就算过
    hook.on_start("s", [], "m")
    from pyxis import TraceRecord

    hook.on_end(TraceRecord(step="s", messages=[], output=None, model="m"))
    hook.on_error("s", [], "m", "boom")


def test_on_start_and_on_end_fire_in_order_on_success():
    fake = FakeClient([Plan(goal="g", next_action="a")])
    rec = _Recorder()
    add_hook(rec)

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    plan("x")
    assert rec.events == [("start", "plan"), ("end", "plan")]


def test_on_error_fires_on_exhaustion_and_reraises():
    fake = FakeClient([])
    rec = _Recorder()
    add_hook(rec)

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with pytest.raises(RuntimeError, match="耗尽"):
        plan("x")

    assert rec.events == [("start", "plan"), ("error", "plan")]


def test_multiple_hooks_fire_in_registration_order():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    class _Tag(StepHook):
        def __init__(self, tag: str, log: list[str]):
            self.tag = tag
            self.log = log

        def on_end(self, record):
            self.log.append(self.tag)

    log: list[str] = []
    add_hook(_Tag("first", log))
    add_hook(_Tag("second", log))
    add_hook(_Tag("third", log))

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    plan("x")
    assert log == ["first", "second", "third"]


def test_remove_hook_unregisters():
    fake = FakeClient([Plan(goal="g", next_action="a"), Plan(goal="g", next_action="a")])
    rec = _Recorder()
    add_hook(rec)

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    plan("x")
    assert len(rec.events) == 2  # start + end

    remove_hook(rec)
    plan("x")
    assert len(rec.events) == 2  # 没增加


def test_hook_exception_warns_but_does_not_break_main_flow():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    class _BadHook(StepHook):
        def on_end(self, record):
            raise RuntimeError("hook 自己炸了")

    class _GoodHook(StepHook):
        def __init__(self):
            self.called = False

        def on_end(self, record):
            self.called = True

    add_hook(_BadHook())
    good = _GoodHook()
    add_hook(good)

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = plan("x")

    # 主流程正常
    assert result.goal == "g"
    # 坏 hook 不阻碍好 hook
    assert good.called
    # 有警告
    assert any("hook 自己炸了" in str(w.message) for w in caught)


def test_hook_sees_messages_and_model():
    fake = FakeClient([Plan(goal="g", next_action="a")])

    class _Spy(StepHook):
        def __init__(self):
            self.start_args: tuple = ()

        def on_start(self, step, messages, model):
            self.start_args = (step, list(messages), model)

    spy = _Spy()
    add_hook(spy)

    @step(output=Plan, model="gpt-4o", client=fake)
    def plan(x: str) -> str:
        """Sys."""
        return x

    plan("hi")
    step_name, messages, model = spy.start_args
    assert step_name == "plan"
    assert model == "gpt-4o"
    assert messages == [
        {"role": "system", "content": "Sys."},
        {"role": "user", "content": "hi"},
    ]


async def test_async_step_also_fires_hooks():
    fake = FakeClient([Plan(goal="g", next_action="a")])
    rec = _Recorder()
    add_hook(rec)

    @step(output=Plan, client=fake)
    async def plan(x: str) -> str:
        return x

    await plan("x")
    assert rec.events == [("start", "plan"), ("end", "plan")]


async def test_async_step_error_fires_on_error_hook():
    fake = FakeClient([])
    rec = _Recorder()
    add_hook(rec)

    @step(output=Plan, client=fake)
    async def plan(x: str) -> str:
        return x

    with pytest.raises(RuntimeError, match="耗尽"):
        await plan("x")

    assert rec.events == [("start", "plan"), ("error", "plan")]


def test_stream_path_fires_hooks():
    fake = FakeClient([Plan(goal="g", next_action="a")])
    rec = _Recorder()
    add_hook(rec)

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    list(plan.stream("x"))
    assert rec.events == [("start", "plan"), ("end", "plan")]


async def test_astream_path_fires_hooks():
    fake = FakeClient([Plan(goal="g", next_action="a")])
    rec = _Recorder()
    add_hook(rec)

    @step(output=Plan, client=fake)
    async def plan(x: str) -> str:
        return x

    async for _ in plan.astream("x"):
        pass
    assert rec.events == [("start", "plan"), ("end", "plan")]


def test_hook_end_receives_full_trace_record():
    fake = FakeClient([Plan(goal="found", next_action="act")])

    class _Capture(StepHook):
        def __init__(self):
            self.record = None

        def on_end(self, record):
            self.record = record

    cap = _Capture()
    add_hook(cap)

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        return x

    with trace() as t:
        plan("x")

    assert cap.record is not None
    assert cap.record.step == "plan"
    assert cap.record.output == Plan(goal="found", next_action="act")
    # on_end 在 record 写入 trace 后触发
    assert t.records == [cap.record]
