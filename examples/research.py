"""端到端示例：分析主题并生成计划。
示例包含两个 step：先分析主题，再基于分析生成计划。普通函数负责串联这两步。
跑起来：
    OPENROUTER_API_KEY=sk-or-... uv run --env-file .env python examples/research.py
"""

from __future__ import annotations

import os

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import step

MODEL = "openai/gpt-5.4-nano"


# ---- Schema：字段顺序即思维链 ----
class Analysis(BaseModel):
    """观察 -> 推理 -> 结论，按这个顺序。"""

    observation: str = Field(description="你对主题注意到了什么")
    reasoning: str = Field(description="这个观察为什么重要")
    conclusion: str = Field(description="一句话结论")


class Plan(BaseModel):
    """目标 -> 步骤 -> 下一步，按这个顺序。"""

    goal: str = Field(description="用一行复述用户目标")
    steps: list[str] = Field(description="拆成 3-5 个具体步骤")
    next_action: str = Field(description="第一个要做的具体步骤")


# ---- client：原生 OpenAI SDK 指向 OpenRouter ----
openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


# ---- Step：schema 是主契约，函数体返回 user message，调用返回 Pydantic ----
@step(output=Analysis, model=MODEL, client=openrouter)
def analyze(topic: str) -> str:
    return f"你是严谨的分析师。先观察，再推理，最后下结论。\n主题：{topic}"


@step(output=Plan, model=MODEL, client=openrouter)
def plan_from_analysis(a: Analysis) -> str:
    return f"你是一丝不苟的规划者。把分析转成行动计划。\n分析：\n{a.model_dump_json(indent=2)}"


# ---- 显式编排：普通 Python 函数 ----
def research(topic: str) -> Plan:
    """研究一个主题：先分析，再基于分析产出计划。"""
    a = analyze(topic)
    return plan_from_analysis(a)


# ---- 展示层：给人看的时候拿字段拼自然语言。这段属于应用代码。 ----
#
# schema 是给 LLM 的结构化骨架（机器可读）；给用户看的最终产出是按
# schema 字段拼出来的自然语言。字段是业务自己定义的，不同前端（CLI /
# Web / Slack）的渲染方式不一样，所以这段留给应用层写。
def render_plan(p: Plan) -> str:
    lines = [f"目标：{p.goal}", "", "步骤："]
    for i, s in enumerate(p.steps, 1):
        lines.append(f"  {i}. {s}")
    lines.extend(["", f"下一步：{p.next_action}"])
    return "\n".join(lines)


def main() -> None:
    result = research("用声明式思维链搭一个 agent 框架")
    print("=" * 60)
    print("最终计划（给人看）")
    print("=" * 60)
    print(render_plan(result))


if __name__ == "__main__":
    main()
