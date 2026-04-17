"""Plan-then-execute 示例：先让 LLM 产出计划，再让另一个 Step 执行每一步。

展示两件事：
1. 两个 Step 用不同的 schema，各自承担隐式思维链——规划时先想目标再拆步骤；
   执行时先想要做什么、再给结果。
2. 显式编排是一个普通 for 循环，想中断、想跳步、想加日志，直接改 Python。
  没有 DSL、没有 graph。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/plan_then_execute.py
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

from pyxis import StepHook, add_hook, flow, set_default_client, step, trace
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"


# ---- 规划阶段：schema 直接声明"先目标再拆步骤"的隐式思维链 ----


class Plan(BaseModel):
    goal: str = Field(description="一行复述用户目标")
    steps: list[str] = Field(description="3-5 个具体可执行的步骤")


@step(output=Plan, model=MODEL)
def make_plan(question: str) -> str:
    """你是严谨的规划者。先复述目标，再列 3-5 个具体可执行步骤。"""
    return f"问题：{question}"


# ---- 执行阶段：每一步都产一段简短的执行结果 ----


class StepResult(BaseModel):
    analysis: str = Field(description="对这一步的理解")
    outcome: str = Field(description="这一步的产出或结论，一两句话")


@step(output=StepResult, model=MODEL)
def execute_step(step_text: str, context: str) -> str:
    """你在执行一个被规划好的步骤。先分析你要做什么，再给结果。"""
    return f"上下文：{context}\n\n当前步骤：{step_text}"


# ---- 显式编排：就是一个 @flow 循环 ----


@flow
def solve(question: str) -> list[StepResult]:
    """先规划，再顺序执行每一步。"""
    plan = make_plan(question)
    context = f"目标：{plan.goal}"
    results: list[StepResult] = []
    for i, step_text in enumerate(plan.steps, 1):
        r = execute_step(step_text, context)
        results.append(r)
        context += f"\n步骤 {i} 产出：{r.outcome}"
    return results


# ---- 演示一下 hook：打点每一步的 token 消耗 ----


class TokenPrinter(StepHook):
    def on_end(self, record):
        usage = record.usage
        tokens = usage.total_tokens if usage else 0
        print(f"  [{record.step}] tokens={tokens}")


def main() -> None:
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))
    add_hook(TokenPrinter())

    question = "如何用 30 分钟搭一个演示用的 agent demo？"
    print(f"问题：{question}\n")
    with trace() as t:
        results = solve(question)

    print("\n=== 计划 ===")
    plan_record = t.records[0]
    plan = plan_record.output
    print(f"目标：{plan.goal}")
    for i, s in enumerate(plan.steps, 1):
        print(f"  {i}. {s}")

    print("\n=== 执行 ===")
    for i, r in enumerate(results, 1):
        print(f"步骤 {i}：{r.outcome}")

    print(f"\n=== 汇总 ===\n调用 {len(t.records)} 次；总计 {t.total_usage().total_tokens} tokens")


if __name__ == "__main__":
    main()
