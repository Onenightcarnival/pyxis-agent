"""流式输出示例：schema 字段逐个被填完的"活"思维链。

每次 LLM 推进一个字段，我们就在终端把到目前为止的状态打印一遍——最直观
展示"schema 就是思维链"。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/streaming_demo.py
"""

from __future__ import annotations

import os
import sys

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import step

MODEL = "openai/gpt-5.4-nano"

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


class Analysis(BaseModel):
    """schema 即思维链：观察 → 推理 → 结论，字段顺序强制推理顺序。"""

    observation: str = Field(description="你注意到什么")
    reasoning: str = Field(description="为什么这重要")
    conclusion: str = Field(description="一句话结论")


@step(output=Analysis, model=MODEL, client=openrouter)
def analyze(topic: str) -> str:
    """你是严谨的分析师。先观察，再推理，最后下一句话的结论。"""
    return f"主题：{topic}"


def _render_frame(a: Analysis) -> str:
    lines = [
        f"  observation: {a.observation or '…'}",
        f"  reasoning:   {a.reasoning or '…'}",
        f"  conclusion:  {a.conclusion or '…'}",
    ]
    return "\n".join(lines)


def main() -> None:
    topic = "为什么海水是咸的？"
    print(f"主题：{topic}\n")
    print("（字段会按 schema 顺序逐个填满；过程是 LLM 推理的真实观察——）\n")

    first = True
    for frame in analyze.stream(topic):
        # 把之前的三行清掉再重绘，像一个简单的"活"面板
        if not first:
            sys.stdout.write("\x1b[3F\x1b[J")
        first = False
        sys.stdout.write(_render_frame(frame) + "\n")
        sys.stdout.flush()

    print("\n——结束——")


if __name__ == "__main__":
    main()
