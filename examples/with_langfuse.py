"""接入 Langfuse：换一行 import 就开始收集 trace。

把 `from openai import OpenAI` 换成 `from langfuse.openai import OpenAI`，
其他代码都不变。跑完去 Langfuse dashboard 看每次 LLM 调用的 prompt /
response / token / latency。

运行前需要：
    uv add langfuse
    export LANGFUSE_PUBLIC_KEY=pk-lf-...
    export LANGFUSE_SECRET_KEY=sk-lf-...
    export LANGFUSE_HOST=https://cloud.langfuse.com   # 或自托管

跑起来：
    uv run --env-file .env python examples/with_langfuse.py

详见 [docs/concepts/observability.md](../docs/concepts/observability.md)。
"""

from __future__ import annotations

import os
import sys

from pydantic import BaseModel, Field

from pyxis import flow, step

MODEL = "openai/gpt-5.4-nano"


def _make_langfuse_client():
    try:
        from langfuse.openai import OpenAI  # 就这一行换掉
    except ImportError:
        print(
            "需要先装 langfuse：uv add langfuse；"
            "并设好 LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST",
            file=sys.stderr,
        )
        sys.exit(1)

    return OpenAI(
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ["OPENROUTER_API_KEY"],
    )


class Analysis(BaseModel):
    observation: str = Field(description="你注意到什么")
    reasoning: str = Field(description="为什么重要")
    conclusion: str = Field(description="一句话结论")


class Plan(BaseModel):
    goal: str
    steps: list[str]


def _build_flow(client):
    @step(output=Analysis, model=MODEL, client=client)
    def analyze(topic: str) -> str:
        """你是严谨的分析师。观察、推理、结论。"""
        return f"主题：{topic}"

    @step(output=Plan, model=MODEL, client=client)
    def plan_from(a: Analysis) -> str:
        """你把分析转成行动计划。"""
        return a.model_dump_json()

    @flow
    def research(topic: str) -> Plan:
        return plan_from(analyze(topic))

    return research


def main() -> None:
    client = _make_langfuse_client()
    research = _build_flow(client)
    result = research("声明式思维链的 agent 框架")

    print("=== 最终计划 ===")
    print(result.model_dump_json(indent=2))
    print("\n=== Langfuse ===")
    print("现在去 Langfuse dashboard 看 trace；本进程退出时 SDK 会自动 flush。")


if __name__ == "__main__":
    main()
