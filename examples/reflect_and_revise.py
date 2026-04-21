"""Reflection / self-correction / critic-refiner——还是同一个模式的不同名字。

行业里 "reflection"、"self-correction"、"critic-refiner"、"LLM-as-a-judge loop"
讲的都是同一件事：让模型产一版 → 让（同一个或另一个）模型打分挑刺 →
让模型根据反馈改 → 重复，直到达标或超次数。

**pyxis 视角下没有新原语**，就三件老东西拼起来：

- 三个 `@step`：`draft` / `critique` / `revise`，各自 schema 承担隐式 CoT。
- 一个 `while score < 阈值` 的 Python 循环——不是 graph，也不是 DSL。
- 一个 `Trace` 就自动把"第几版拿了几分 / 花了多少 token"记录下来。

关键是 **critique 的 schema 字段顺序**：先列 issues，再标 severity，最后才
给 score。顺序倒过来（先 score 再 justify）就变成"先拍脑袋再自圆其说"。
这是 schema-as-CoT 在质量评审场景的直接应用。

### 坦白一件事

reflection **不保证单调收敛**——跑完下面 demo 你会看到分数来回跳。这不是
pyxis 的缺陷，是 LLM-as-judge 这个模式本身的特性；弱模型尤其如此（本 demo
跑在 gpt-5.4-nano 上，够讲结构但压缩能力有限）。pyxis 做的只是**不替你
隐藏这个真相**——trace 里每一版的分数都看得见，要不要加轮次、换模型、
换任务表述，由你根据真相决定。生产用更强模型通常能稳住单调下降。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/reflect_and_revise.py
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from pyxis import flow, set_default_client, step, trace
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"
MAX_CHARS = 100
TARGET_SCORE = 8
MAX_ROUNDS = 4

SOURCE = (
    "pyxis-agent 是一个 Python 语言实现的 agent 开发框架，它的核心理念是"
    "把原本用自然语言描述的多步推理过程改写成 Pydantic schema 定义的字段"
    "顺序，并让多次 LLM 调用之间的编排回归到最普通的 Python 控制流（if、"
    "for、函数组合），从而绕开专用 DSL 带来的学习成本。"
)


# ---- 三个 schema，三段隐式思维链 ----


class Draft(BaseModel):
    keywords: list[str] = Field(description="原文里不能丢的 3-5 个关键信息点")
    text: str = Field(description="信息完整的第一版 tagline，允许偏长（60-90 字）")


class Critique(BaseModel):
    issues: list[str] = Field(description="列出具体问题（例如超字数多少、漏了哪个关键词、有歧义）")
    severity: Literal["low", "medium", "high"] = Field(
        description="high：超字数或漏核心关键词；medium：表达不畅；low：鸡蛋里挑骨头"
    )
    score: int = Field(ge=0, le=10, description="综合打分 0-10")
    must_fix: list[str] = Field(description="下一轮必须解决的点，写成可执行的改写建议")


class Revision(BaseModel):
    changes: list[str] = Field(description="针对 must_fix 的每一条，说清你改了什么")
    text: str = Field(description=f"改进后的 tagline，≤{MAX_CHARS} 个字")


# ---- 三个 step：docstring 是 prompt，字符串返回是 user message ----


@step(output=Draft, model=MODEL)
def draft(source: str) -> str:
    """你在为一段技术描述写首页 tagline 的第一版。先列出原文不能丢的
    3-5 个关键词；然后写一版**信息完整的初稿，长度可以偏长（60-90 字）**——
    别急着压缩，后续会有编辑环节负责精简。"""
    return f"原文：\n{source}"


@step(output=Critique, model=MODEL)
def critique(source: str, text: str) -> str:
    """你是严格但务实的编辑，按硬标准评判：
    - 长度：严格 **≤ 100 个字**；超过即 high severity。
    - 核心信息：不能漏 Pydantic schema 字段顺序、普通 Python 编排、
      避开 DSL 这三点里至少两点。
    - 可读：不能出现语病或歧义。
    **先挑具体问题，再判断严重度，最后才打分**——顺序别倒。"""
    return f"原文：\n{source}\n\n当前 tagline（实际字数 {len(text)}）：\n{text}"


@step(output=Revision, model=MODEL)
def revise(source: str, text: str, must_fix: list[str]) -> str:
    """你是压缩文案的高手。**≤ 100 字是硬约束**，超一字都算失败。
    核心策略——优先压缩：**比上一版至少短 10 个字**，宁可只保留 1-2 个最核心
    关键词也要卡死 100 字内。先逐条说明你怎么砍的，再给新文案。"""
    fixes = "\n".join(f"- {x}" for x in must_fix)
    return f"原文：\n{source}\n\n上一版（{len(text)} 字）：\n{text}\n\n必改：\n{fixes}"


# ---- 显式编排：while 循环就是 reflection loop ----


@flow
def compress_with_reflection(source: str) -> tuple[str, list[int]]:
    """先写一版，然后 critique → revise 循环。通过条件：score≥目标 且
    severity 不是 high（即没有超字数/漏关键词这类硬问题）。跑满 MAX_ROUNDS
    仍不通过时，对最后一版再 critique 一次，让分数轨迹覆盖终稿。"""
    text = draft(source).text
    scores: list[int] = []
    for r in range(1, MAX_ROUNDS + 1):
        c = critique(source, text)
        scores.append(c.score)
        print(f"[轮 {r}] 字数={len(text)} score={c.score} severity={c.severity}")
        for issue in c.issues[:3]:
            print(f"    - {issue}")
        print(f"    → {text}")
        if c.score >= TARGET_SCORE and c.severity != "high":
            return text, scores
        text = revise(source, text, c.must_fix).text
    final_c = critique(source, text)
    scores.append(final_c.score)
    print(f"[终评] 字数={len(text)} score={final_c.score} severity={final_c.severity}")
    return text, scores


def main() -> None:
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))

    print(f"原文（{len(SOURCE)} 字）：\n{SOURCE}\n")

    with trace() as t:
        final_text, scores = compress_with_reflection(SOURCE)

    print(f"\n=== 分数轨迹 ===\n{' → '.join(str(s) for s in scores)}    (目标 ≥ {TARGET_SCORE})")
    print(f"\n=== 终稿（{len(final_text)} 字）===\n{final_text}")
    print(f"\n=== 成本 ===\n{len(t.records)} 次调用；{t.total_usage().total_tokens} tokens")


if __name__ == "__main__":
    main()
