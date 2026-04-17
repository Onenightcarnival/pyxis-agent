"""Tool 原语的测试 —— 规格 003。"""

from __future__ import annotations

from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field

from pyxis import FakeClient, Tool, flow, step, trace


class SearchWeb(Tool):
    """Search the web."""

    kind: Literal["search"] = "search"
    query: str

    def run(self) -> str:
        return f"RESULTS({self.query})"


class Finish(Tool):
    """Return the final answer and stop."""

    kind: Literal["finish"] = "finish"
    answer: str

    def run(self) -> str:
        return self.answer


Action = Annotated[SearchWeb | Finish, Field(discriminator="kind")]


class Decision(BaseModel):
    thought: str
    action: Action


def test_tool_base_run_raises():
    class Leaky(Tool):
        kind: Literal["leaky"] = "leaky"

    with pytest.raises(NotImplementedError, match="Leaky"):
        Leaky().run()


def test_tool_subclass_executes():
    t = SearchWeb(query="cats")
    assert t.run() == "RESULTS(cats)"


def test_tool_roundtrips_through_step_and_schema():
    fake = FakeClient([Decision(thought="I should search", action=SearchWeb(query="cats"))])

    @step(output=Decision, client=fake)
    def decide(question: str) -> str:
        """Pick a tool."""
        return question

    d = decide("find cats")
    assert isinstance(d.action, SearchWeb)
    assert d.action.query == "cats"
    assert d.action.run() == "RESULTS(cats)"


def test_tool_discriminated_union_dispatch_via_isinstance():
    fake = FakeClient(
        [
            Decision(thought="t1", action=SearchWeb(query="x")),
            Decision(thought="t2", action=Finish(answer="done")),
        ]
    )

    @step(output=Decision, client=fake)
    def decide(q: str) -> str:
        return q

    results: list[str] = []
    for _ in range(3):
        d = decide("q")
        results.append(d.action.run())
        if isinstance(d.action, Finish):
            break

    assert results == ["RESULTS(x)", "done"]


def test_tool_in_agent_loop_traced_correctly():
    fake = FakeClient(
        [
            Decision(thought="search first", action=SearchWeb(query="foo")),
            Decision(thought="now finish", action=Finish(answer="final")),
        ]
    )

    @step(output=Decision, client=fake)
    def decide(scratch: str) -> str:
        """Pick a tool."""
        return scratch

    @flow
    def agent(question: str, max_steps: int = 5) -> str:
        scratch: list[str] = [question]
        for _ in range(max_steps):
            d = decide("\n".join(scratch))
            scratch.append(f"thought: {d.thought}")
            obs = d.action.run()
            scratch.append(f"obs: {obs}")
            if isinstance(d.action, Finish):
                return obs
        raise RuntimeError("max_steps exhausted")

    with trace() as t:
        answer = agent("what is foo?")

    assert answer == "final"
    assert [r.step for r in t.records] == ["decide", "decide"]
    assert isinstance(t.records[0].output.action, SearchWeb)
    assert isinstance(t.records[1].output.action, Finish)
