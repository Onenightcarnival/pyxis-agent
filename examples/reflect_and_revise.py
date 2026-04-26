"""draft、critique、revise 循环：写一版，检查问题，再修改。
行业里叫 reflection、self-correction、critic-refiner、LLM-as-a-judge loop，
基本结构都是这三步加一个 while。
- 三个 `@step`：`draft` / `critique` / `revise`。critique 的字段顺序是
  issues、severity、score。
- 一个普通函数里的 while 循环做轮次控制，通过条件是 score≥阈值且
  severity != "high"。
示例会打印每一轮草稿、问题和分数。
跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/reflect_and_revise.py
"""

from __future__ import annotations

import os
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import step

MODEL = "openai/gpt-5.4-nano"
MAX_CHARS = 100
TARGET_SCORE = 8
MAX_ROUNDS = 4
openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)
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
        description="high：超字数或漏核心关键词；medium：表达不畅；low：小问题"
    )
    score: int = Field(ge=0, le=10, description="综合打分 0-10")
    must_fix: list[str] = Field(description="下一轮必须解决的点，写成可执行的改写建议")


class Revision(BaseModel):
    changes: list[str] = Field(description="针对 must_fix 的每一条，说清你改了什么")
    text: str = Field(description=f"改进后的 tagline，≤{MAX_CHARS} 个字")


# ---- 三个 step：schema 是主契约，函数体返回 user message ----
@step(output=Draft, model=MODEL, client=openrouter)
def draft(source: str) -> str:
    return (
        "你在为一段技术描述写首页 tagline 的第一版。先列出原文不能丢的"
        "3-5 个关键词；然后写一版信息完整的初稿，长度可以偏长（60-90 字）。"
        f"别急着压缩，后续会有编辑环节负责精简。\n原文：\n{source}"
    )


@step(output=Critique, model=MODEL, client=openrouter)
def critique(source: str, text: str) -> str:
    return (
        "你是严格但务实的编辑，按硬标准评判：\n"
        "- 长度：严格 ≤ 100 个字；超过即 high severity。\n"
        "- 核心信息：不能漏 Pydantic schema 字段顺序、普通 Python 编排、"
        "避开 DSL 这三点里至少两点。\n"
        "- 可读：不能出现语病或歧义。\n"
        "先列具体问题，再判断严重度，最后打分。\n"
        f"原文：\n{source}\n\n当前 tagline（实际字数 {len(text)}）：\n{text}"
    )


@step(output=Revision, model=MODEL, client=openrouter)
def revise(source: str, text: str, must_fix: list[str]) -> str:
    fixes = "\n".join(f"- {x}" for x in must_fix)
    return (
        "你是压缩文案的高手。≤ 100 字是硬约束，超一字都算失败。"
        "优先压缩：比上一版至少短 10 个字，宁可只保留 1-2 个最核心"
        "关键词也要卡死 100 字内。先逐条说明你怎么砍的，再给新文案。\n"
        f"原文：\n{source}\n\n上一版（{len(text)} 字）：\n{text}\n\n必改：\n{fixes}"
    )


# ---- 显式编排：while 循环就是 reflection loop ----
def compress_with_reflection(source: str) -> tuple[str, list[int]]:
    """先写一版，然后做 critique / revise 循环。通过条件：score≥目标 且
    severity != "high"。跑满 MAX_ROUNDS
    仍不通过时，对最后一版再 critique 一次，让分数轨迹覆盖终稿。"""
    text = draft(source).text
    scores: list[int] = []
    for r in range(1, MAX_ROUNDS + 1):
        c = critique(source, text)
        scores.append(c.score)
        print(f"[轮 {r}] 字数={len(text)} score={c.score} severity={c.severity}")
        for issue in c.issues[:3]:
            print(f"    - {issue}")
        print(f"    {text}")
        if c.score >= TARGET_SCORE and c.severity != "high":
            return text, scores
        text = revise(source, text, c.must_fix).text
    final_c = critique(source, text)
    scores.append(final_c.score)
    print(f"[终评] 字数={len(text)} score={final_c.score} severity={final_c.severity}")
    return text, scores


def main() -> None:
    print(f"原文（{len(SOURCE)} 字）：\n{SOURCE}\n")
    final_text, scores = compress_with_reflection(SOURCE)
    print(f"\n=== 分数轨迹 ===\n{' / '.join(str(s) for s in scores)}    (目标 ≥ {TARGET_SCORE})")
    print(f"\n=== 终稿（{len(final_text)} 字）===\n{final_text}")


if __name__ == "__main__":
    main()
