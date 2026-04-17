"""端到端示例：声明式思维链。

两条轴同时展示：
- 隐式 CoT：单次 LLM 调用里由 schema 字段顺序驱动推理；
- 显式 CoT：多步由普通 Python 编排。

跑起来：
    OPENROUTER_API_KEY=sk-or-... uv run --env-file .env python examples/research.py
"""

from __future__ import annotations

import os

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import InstructorClient, flow, set_default_client, step

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


# ---- Step：docstring = system prompt，返回 = user message ----


@step(output=Analysis, model=MODEL)
def analyze(topic: str) -> str:
    """你是严谨的分析师。先观察，再推理，最后下结论。"""
    return f"主题：{topic}"


@step(output=Plan, model=MODEL)
def plan_from_analysis(a: Analysis) -> str:
    """你是一丝不苟的规划者。把分析转成行动计划。"""
    return f"分析：\n{a.model_dump_json(indent=2)}"


# ---- Flow：显式编排 = 普通 Python ----


@flow
def research(topic: str) -> Plan:
    """研究一个主题：先分析，再基于分析产出计划。"""
    a = analyze(topic)
    return plan_from_analysis(a)


def _configure_openrouter() -> None:
    key = os.environ["OPENROUTER_API_KEY"]
    openai = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    set_default_client(InstructorClient(instructor.from_openai(openai)))


def main() -> None:
    _configure_openrouter()
    result, t = research.run_traced("用声明式思维链搭一个 agent 框架")

    print("=" * 60)
    print("TRACE")
    print("=" * 60)
    for i, rec in enumerate(t.records, 1):
        print(f"\n[{i}] step={rec.step}  model={rec.model}")
        print(rec.output.model_dump_json(indent=2))

    print("\n" + "=" * 60)
    print("FINAL")
    print("=" * 60)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
