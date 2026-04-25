"""Interrupt review：LLM 生成计划，外部审阅后执行或驳回。

- `@flow` 写成生成器函数，中间 `yield ask_interrupt(...)` 挂起等外部输入。
- `run_flow(gen, on_interrupt=...)` 负责驱动：把请求交给回调，把答案 send
  回生成器。

渲染给人看的部分由应用层 `_render_plan` 负责。换 Web UI、Slack bot 或
微信机器人时，通常只需要改这个函数。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/interrupt_review.py
"""

from __future__ import annotations

import os

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import ask_interrupt, flow, run_flow, step

MODEL = "openai/gpt-5.4-nano"

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


class Plan(BaseModel):
    goal: str = Field(description="一行复述用户目标")
    steps: list[str] = Field(description="3-5 个具体可执行步骤")


class ReviewDecision(BaseModel):
    approve: bool = Field(description="是否批准这个计划")
    comments: str | None = Field(default=None, description="不批准时的改进建议")


@step(output=Plan, model=MODEL, client=openrouter)
def make_plan(question: str) -> str:
    """你是严谨的规划者。先复述目标，再列 3-5 个具体可执行步骤。"""
    return f"问题：{question}"


@step(output=Plan, model=MODEL, client=openrouter)
def refine_plan(question: str, prev: Plan, comments: str) -> str:
    """你是规划者。上一个计划被审阅者打回，请根据意见改好。"""
    return (
        f"问题：{question}\n\n上一个计划：{prev.model_dump_json(indent=2)}\n\n审阅意见：{comments}"
    )


@flow
def plan_with_review(question: str, max_rounds: int = 3):
    """LLM 写计划，人工审阅后根据意见迭代。最多三轮。"""
    plan = make_plan(question)
    for _ in range(max_rounds):
        decision: ReviewDecision = yield ask_interrupt(
            "请审阅这个计划",
            schema=ReviewDecision,
            plan=plan,  # 直接把 Plan 实例放进 context，怎么渲染留给回调决定
        )
        if decision.approve:
            return {"status": "approved", "plan": plan}
        plan = refine_plan(question, plan, decision.comments or "请更加具体")
    return {"status": "max_rounds_reached", "last_plan": plan}


# ---- 展示层：拿 Pydantic 字段拼自然语言。这段属于"应用代码"，不属于框架。 ----


def render_plan(plan: Plan) -> str:
    """把 Plan 渲染成给人看的自然语言。

    换 Web UI 就是换这一段；换 Slack 就把换行改成 Markdown；加"纯文本
    机器人"就写成一段连贯的话。schema 字段是你自己定义的，怎么拼你说
    了算。
    """
    lines = [f"目标：{plan.goal}", "", "步骤："]
    for i, step_text in enumerate(plan.steps, 1):
        lines.append(f"  {i}. {step_text}")
    return "\n".join(lines)


def terminal_on_interrupt(q) -> ReviewDecision:
    """终端前端：渲染自然语言，接收 y/N + 意见。

    on_interrupt 拿到 InterruptRequest 之后怎么展示、怎么收答案，完全是这一层
    的自由。框架管的只是"把问题交给你、把你的答案送回生成器"。
    """
    print("\n=======  人工审核点  =======")
    print(q.question)
    print()
    plan: Plan = q.context["plan"]
    print(render_plan(plan))
    approve = input("\n批准？[y/N] ").strip().lower() == "y"
    comments = None
    if not approve:
        comments = input("改进意见：").strip() or None
    return ReviewDecision(approve=approve, comments=comments)


def main() -> None:
    result = run_flow(
        plan_with_review("如何用 30 分钟做一个 agent 框架的演示？"),
        on_interrupt=terminal_on_interrupt,
    )

    print("\n=======  结果  =======")
    status = result["status"]
    if status == "approved":
        print("[已批准] 最终计划：\n")
        print(render_plan(result["plan"]))
    elif status == "rejected":
        print(f"[被驳回] 意见：{result.get('comments', '无')}")
    else:
        print("[达到轮数上限] 最后一版：\n")
        print(render_plan(result["last_plan"]))


if __name__ == "__main__":
    main()
