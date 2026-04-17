"""Trace.to_jsonl 落盘的测试 —— 规格 008。"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from pyxis import FakeClient, Usage, step, trace


class Plan(BaseModel):
    goal: str
    next_action: str


def test_to_jsonl_writes_one_line_per_record(tmp_path: Path):
    fake = FakeClient(
        responses=[
            Plan(goal="a", next_action="x"),
            Plan(goal="b", next_action="y"),
        ],
        usages=[
            Usage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            Usage(prompt_tokens=4, completion_tokens=5, total_tokens=9),
        ],
    )

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        """规划中文场景。"""
        return req

    with trace() as t:
        plan("先干这个")
        plan("再干那个")

    path = tmp_path / "runs.jsonl"
    t.to_jsonl(path)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec0 = json.loads(lines[0])
    rec1 = json.loads(lines[1])
    assert rec0["step"] == "plan"
    assert rec0["output"] == {"goal": "a", "next_action": "x"}
    assert rec0["usage"]["total_tokens"] == 3
    assert rec1["output"] == {"goal": "b", "next_action": "y"}


def test_to_jsonl_preserves_chinese_without_escape(tmp_path: Path):
    fake = FakeClient([Plan(goal="中文目标", next_action="动手")])

    @step(output=Plan, client=fake)
    def plan(req: str) -> str:
        return req

    with trace() as t:
        plan("先干这个")

    path = tmp_path / "cn.jsonl"
    t.to_jsonl(path)
    text = path.read_text(encoding="utf-8")
    assert "中文目标" in text
    assert "动手" in text
    assert "\\u" not in text  # ensure_ascii=False 生效


def test_to_jsonl_appends_not_overwrites(tmp_path: Path):
    path = tmp_path / "roll.jsonl"
    path.write_text('{"step": "previous"}\n', encoding="utf-8")

    fake = FakeClient([Plan(goal="a", next_action="x")])

    @step(output=Plan, client=fake)
    def plan(r: str) -> str:
        return r

    with trace() as t:
        plan("x")
    t.to_jsonl(path)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"step": "previous"}
    assert json.loads(lines[1])["step"] == "plan"


def test_to_jsonl_empty_trace_writes_empty_file(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    with trace() as t:
        pass
    t.to_jsonl(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_to_jsonl_accepts_str_path(tmp_path: Path):
    fake = FakeClient([Plan(goal="a", next_action="x")])

    @step(output=Plan, client=fake)
    def plan(r: str) -> str:
        return r

    with trace() as t:
        plan("x")

    path = tmp_path / "str-path.jsonl"
    t.to_jsonl(str(path))
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8").splitlines()[0])["step"] == "plan"
