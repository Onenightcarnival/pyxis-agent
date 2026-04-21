"""接入 langfuse 做托管级可观测性。

运行前需要：
    uv add langfuse      # 把 langfuse 加进项目依赖
    export LANGFUSE_PUBLIC_KEY=pk-lf-...
    export LANGFUSE_SECRET_KEY=sk-lf-...
    export LANGFUSE_HOST=https://cloud.langfuse.com   # 或自托管

跑起来：
    uv run --env-file .env python examples/with_langfuse.py

一跑完去 langfuse dashboard 就能看到 trace，里面含每次 @step 的
prompt / response / token / Pydantic schema。同时 pyxis 本地 trace 也在
跑，打印到 stdout —— 两层可观测性各司其职。

详见 [docs/concepts/observability.md](../docs/concepts/observability.md)。
"""

from __future__ import annotations

import os
import sys

from pydantic import BaseModel, Field

from pyxis import InstructorClient, flow, set_default_client, step, trace

MODEL = "openai/gpt-5.4-nano"


def _configure_with_langfuse() -> None:
    try:
        from langfuse.openai import AsyncOpenAI, OpenAI
    except ImportError:
        print(
            "需要先装 langfuse：uv add langfuse；"
            "并设好 LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST",
            file=sys.stderr,
        )
        sys.exit(1)

    import instructor

    key = os.environ["OPENROUTER_API_KEY"]
    base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    sync = instructor.from_openai(OpenAI(api_key=key, base_url=base))
    async_ = instructor.from_openai(AsyncOpenAI(api_key=key, base_url=base))
    set_default_client(InstructorClient(sync, async_))


class Analysis(BaseModel):
    observation: str = Field(description="你注意到什么")
    reasoning: str = Field(description="为什么重要")
    conclusion: str = Field(description="一句话结论")


class Plan(BaseModel):
    goal: str
    steps: list[str]


@step(output=Analysis, model=MODEL)
def analyze(topic: str) -> str:
    """你是严谨的分析师。观察、推理、结论。"""
    return f"主题：{topic}"


@step(output=Plan, model=MODEL)
def plan_from(a: Analysis) -> str:
    """你把分析转成行动计划。"""
    return a.model_dump_json()


@flow
def research(topic: str) -> Plan:
    return plan_from(analyze(topic))


def main() -> None:
    _configure_with_langfuse()
    with trace() as t:
        result = research("声明式思维链的 agent 框架")

    print("=== pyxis 本地 trace ===")
    print(t.to_json(indent=2, ensure_ascii=False)[:600] + " ...")
    print("\n=== 最终计划 ===")
    print(result.model_dump_json(indent=2))
    print("\n=== langfuse ===")
    print("现在去 langfuse dashboard 看 trace；本进程退出时 SDK 会自动 flush。")


if __name__ == "__main__":
    main()
