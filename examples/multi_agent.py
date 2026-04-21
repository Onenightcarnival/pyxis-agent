"""两个 agent 协作：Researcher 产原料，Editor 改成成稿。

每个 agent 是一个 `@flow`——内部有自己的 step（甚至多步）、自己的 schema、
自己的 prompt 风格。"协作"就是一个 flow 直接调另一个 flow，和 Python 里
函数调函数没区别。没有 graph、没有 bus、没有 orchestrator。

拓扑：

    research_agent(topic) -> ResearchBrief
                        \\
    editor_agent(topic, brief) -> PublishDraft

想并行拉多份 research 再合并？用 `asyncio.gather`。想让 editor 看完后
让 researcher 补充？再调一次 `research_agent`，加 while 循环即可——
仍然是 Python。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/multi_agent.py
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

from pyxis import flow, set_default_client, step, trace
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"


# ---- Agent 1：Researcher（内部两步——找要点 + 挑槽点）----


class Angles(BaseModel):
    angles: list[str] = Field(description="这个话题值得展开的 3-5 个角度，短句")


class ResearchBrief(BaseModel):
    key_points: list[str] = Field(description="3-5 条事实/主张，每条一行，中立口吻")
    caveats: list[str] = Field(description="这个话题容易被误解 / 有争议的 2-3 个点")


@step(output=Angles, model=MODEL)
def find_angles(topic: str) -> str:
    """你是资深分析师。为下面的话题列 3-5 个值得展开的切入角度，
    不用长句。"""
    return f"话题：{topic}"


@step(output=ResearchBrief, model=MODEL)
def write_brief(topic: str, angles: list[str]) -> str:
    """你是研究员。基于给你的角度，先列 3-5 条具体事实 / 主张做成要点，
    再列 2-3 条容易被误解或有争议的地方（caveats）。中立口吻、不带营销腔。"""
    lines = "\n".join(f"- {a}" for a in angles)
    return f"话题：{topic}\n\n参考角度：\n{lines}"


@flow
def research_agent(topic: str) -> ResearchBrief:
    """Researcher agent：先想切入角度，再写 brief。"""
    angles = find_angles(topic).angles
    return write_brief(topic, angles)


# ---- Agent 2：Editor（单步——把 brief 改成适合发布的段落）----


class PublishDraft(BaseModel):
    headline: str = Field(description="一句抓人的标题，不要 clickbait")
    body: str = Field(description="一段 150-220 字的正文，有起承转合")
    tone_notes: str = Field(description="一句话说你用了什么基调，供主编人工抽查")


@step(output=PublishDraft, model=MODEL)
def polish(topic: str, brief: ResearchBrief) -> str:
    """你是严格的主编。把研究员的 brief 改成一段发得出去的正文：
    保留 brief 里的事实，去掉重复，照顾 caveats（至少带到一条），
    节奏自然不像机翻。最后写一句你用了什么基调。"""
    return (
        f"话题：{topic}\n\n"
        f"研究员 brief：\n"
        f"要点：\n{chr(10).join('- ' + p for p in brief.key_points)}\n\n"
        f"容易被误解的地方：\n{chr(10).join('- ' + c for c in brief.caveats)}"
    )


@flow
def editor_agent(topic: str, brief: ResearchBrief) -> PublishDraft:
    """Editor agent：把 brief 加工成发布稿。"""
    return polish(topic, brief)


# ---- 顶层 flow：两个 agent 串联；就是函数调函数 ----


@flow
def pipeline(topic: str) -> PublishDraft:
    brief = research_agent(topic)
    return editor_agent(topic, brief)


def main() -> None:
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))

    topic = "schema-as-CoT：用结构化字段顺序把 LLM 的推理步骤声明出来"
    print(f"话题：{topic}\n")

    with trace() as t:
        draft = pipeline(topic)

    # trace 把两个 agent 的内部步骤都记下来了，顺序就是调用顺序
    print("=== 调用轨迹 ===")
    for i, rec in enumerate(t.records, 1):
        print(f"[{i}] {rec.step}")

    print(f"\n=== 标题 ===\n{draft.headline}")
    print(f"\n=== 正文 ===\n{draft.body}")
    print(f"\n=== 主编基调说明 ===\n{draft.tone_notes}")
    print(f"\n=== 成本 ===\n{len(t.records)} 次调用；{t.total_usage().total_tokens} tokens")


if __name__ == "__main__":
    main()
