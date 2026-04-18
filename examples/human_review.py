"""Human-in-the-loop 示例：LLM 产计划 → 人审 → 执行或驳回。

两件事：
1. `@flow` 写成生成器函数，中间 `yield ask_human(...)` 挂起等人拍板。
2. `run_flow(gen, on_ask=...)` 驱动：把问题丢给回调，把答案 send 回生成器。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/human_review.py
"""

from __future__ import annotations

import json
import os

from pydantic import BaseModel, Field

from pyxis import ask_human, flow, run_flow, set_default_client, step
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"


class Plan(BaseModel):
    goal: str = Field(description="一行复述用户目标")
    steps: list[str] = Field(description="3-5 个具体可执行步骤")


class ReviewDecision(BaseModel):
    approve: bool = Field(description="是否批准这个计划")
    comments: str | None = Field(default=None, description="不批准时的改进建议")


@step(output=Plan, model=MODEL)
def make_plan(question: str) -> str:
    """你是严谨的规划者。先复述目标，再列 3-5 个具体可执行步骤。"""
    return f"问题：{question}"


@step(output=Plan, model=MODEL)
def refine_plan(question: str, prev: Plan, comments: str) -> str:
    """你是规划者。上一个计划被审阅者打回，请根据意见改好。"""
    return (
        f"问题：{question}\n\n上一个计划：{prev.model_dump_json(indent=2)}\n\n审阅意见：{comments}"
    )


@flow
def plan_with_review(question: str, max_rounds: int = 3):
    """LLM 写计划 → 人审 → 根据意见迭代。最多三轮。"""
    plan = make_plan(question)
    for _ in range(max_rounds):
        decision: ReviewDecision = yield ask_human(
            "请审阅这个计划",
            schema=ReviewDecision,
            plan=plan.model_dump(),
        )
        if decision.approve:
            return {"status": "approved", "plan": plan.model_dump()}
        plan = refine_plan(question, plan, decision.comments or "请更加具体")
    return {"status": "max_rounds_reached", "last_plan": plan.model_dump()}


def terminal_on_ask(q) -> ReviewDecision:
    """一个最朴素的命令行前端。真实场景可以换成 Web UI / Slack bot。"""
    print("\n======  人工审核点  ======")
    print(q.question)
    print("\n上下文：")
    print(json.dumps(q.context, indent=2, ensure_ascii=False))
    approve = input("\n批准？[y/N] ").strip().lower() == "y"
    comments = None
    if not approve:
        comments = input("改进意见：").strip() or None
    return ReviewDecision(approve=approve, comments=comments)


def main() -> None:
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))

    result = run_flow(
        plan_with_review("如何用 30 分钟做一个 agent 框架的演示？"),
        on_ask=terminal_on_ask,
    )

    print("\n======  结果  ======")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
