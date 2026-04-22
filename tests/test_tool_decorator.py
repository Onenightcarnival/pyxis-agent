"""`@tool` 装饰器的测试 —— 规格 007。"""

from __future__ import annotations

from typing import Annotated, Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, Field, TypeAdapter

from pyxis import FakeClient, Tool, step, tool


def test_tool_decorator_produces_tool_subclass():
    @tool
    def search_web(query: str) -> str:
        """在网上搜索。"""
        return f"R:{query}"

    assert issubclass(search_web, Tool)
    assert search_web.__name__ == "SearchWeb"
    assert search_web.__doc__ == "在网上搜索。"


def test_tool_decorator_auto_kind_literal():
    @tool
    def search_web(query: str) -> str:
        return f"R:{query}"

    t = search_web(query="猫")
    assert t.kind == "search_web"

    # kind 字段是 Literal["search_web"]
    field = search_web.model_fields["kind"]
    origin = get_origin(field.annotation)
    args = get_args(field.annotation)
    assert origin is Literal
    assert args == ("search_web",)


def test_tool_decorator_required_and_default_fields():
    @tool
    def fetch(url: str, timeout: int = 30) -> str:
        return url

    required = fetch(url="https://x")
    assert required.url == "https://x"
    assert required.timeout == 30

    with_override = fetch(url="https://y", timeout=5)
    assert with_override.timeout == 5

    # 缺必选字段应失败
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        fetch()


def test_tool_decorator_run_invokes_original_function():
    captured: list[dict[str, object]] = []

    @tool
    def echo(msg: str, times: int = 1) -> str:
        captured.append({"msg": msg, "times": times})
        return msg * times

    inst = echo(msg="hi", times=3)
    assert inst.run() == "hihihi"
    assert captured == [{"msg": "hi", "times": 3}]


def test_tool_decorator_run_coerces_non_string_to_str():
    @tool
    def add(a: int, b: int) -> int:  # 返回 int，run 应当 str() 转
        return a + b

    assert add(a=2, b=3).run() == "5"


def test_tool_decorator_unannotated_param_defaults_to_str():
    @tool
    def greet(name) -> str:
        return f"hi {name}"

    ann = greet.model_fields["name"].annotation
    assert ann is str
    assert greet(name="世界").run() == "hi 世界"


def test_tool_decorator_participates_in_discriminated_union():
    @tool
    def search_web(query: str) -> str:
        return f"R:{query}"

    @tool
    def finish(answer: str) -> str:
        return answer

    Action = Annotated[search_web | finish, Field(discriminator="kind")]
    adapter = TypeAdapter(Action)

    a = adapter.validate_python({"kind": "search_web", "query": "猫"})
    assert isinstance(a, search_web)
    assert a.run() == "R:猫"

    b = adapter.validate_python({"kind": "finish", "answer": "完成"})
    assert isinstance(b, finish)
    assert b.run() == "完成"


def test_tool_decorator_end_to_end_with_step():
    @tool
    def calc(expression: str) -> str:
        return str(eval(expression, {"__builtins__": {}}, {}))

    @tool
    def finish(answer: str) -> str:
        return answer

    Action = Annotated[calc | finish, Field(discriminator="kind")]

    class Decision(BaseModel):
        thought: str
        action: Action

    fake = FakeClient(
        [
            Decision(thought="先算", action=calc(expression="6*7")),
            Decision(thought="完毕", action=finish(answer="42")),
        ]
    )

    @step(output=Decision, client=fake)
    def decide(q: str) -> str:
        return q

    d1 = decide("算 6*7")
    d2 = decide("下一步")

    assert d1.action.run() == "42"
    assert d2.action.run() == "42"
    assert len(fake.calls) == 2


def test_tool_decorator_rejects_varargs():
    with pytest.raises(TypeError, match="不支持"):

        @tool
        def bad(*args: str) -> str:
            return " ".join(args)


def test_tool_decorator_rejects_varkwargs():
    with pytest.raises(TypeError, match="不支持"):

        @tool
        def bad(**kwargs: str) -> str:
            return ""
