"""两个 agent 协作：Researcher 生成素材，Editor 改成成稿。
每个 agent 是一个普通 Python 函数，内部有自己的 step、schema 和输入说明。协作方式是一个
函数调用另一个函数。
拓扑：
    research_agent(topic) -> ResearchBrief
                        \\
    editor_agent(topic, brief) -> PublishDraft
并行多份 research 可以用 `asyncio.gather`。需要补充素材时，可以再调用一次
`research_agent`，或在外层加 while 循环。
跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/multi_agent.py
"""

from __future__ import annotations

import os
from inspect import cleandoc

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import step

MODEL = "openai/gpt-5.4-nano"
openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


# ---- Agent 1：Researcher（内部两步：找要点 + 找风险）----
class Angles(BaseModel):
    angles: list[str] = Field(description="这个话题值得展开的 3-5 个角度，短句")


class ResearchBrief(BaseModel):
    key_points: list[str] = Field(description="3-5 条事实/主张，每条一行，中立口吻")
    caveats: list[str] = Field(description="这个话题容易被误解 / 有争议的 2-3 个点")


@step(output=Angles, model=MODEL, client=openrouter)
def find_angles(topic: str) -> str:
    return cleandoc(
        f"""
        你是资深分析师。为下面的话题列 3-5 个值得展开的切入角度，不用长句。

        话题：{topic}
        """
    )


@step(output=ResearchBrief, model=MODEL, client=openrouter)
def write_brief(topic: str, angles: list[str]) -> str:
    lines = "\n".join(f"- {a}" for a in angles)
    return cleandoc(
        """
        你是研究员。基于给你的角度，先列 3-5 条具体事实 / 主张做成要点，
        再列 2-3 条容易被误解或有争议的地方（caveats）。中立口吻、不带营销腔。

        话题：{topic}

        参考角度：
        {lines}
        """
    ).format(topic=topic, lines=lines)


def research_agent(topic: str) -> ResearchBrief:
    """Researcher agent：先想切入角度，再写 brief。"""
    angles = find_angles(topic).angles
    return write_brief(topic, angles)


# ---- Agent 2：Editor（单步：把 brief 改成适合发布的段落）----
class PublishDraft(BaseModel):
    headline: str = Field(description="一句抓人的标题，不要 clickbait")
    body: str = Field(description="一段 150-220 字的正文，有起承转合")
    tone_notes: str = Field(description="一句话说你用了什么基调，供主编人工抽查")


@step(output=PublishDraft, model=MODEL, client=openrouter)
def polish(topic: str, brief: ResearchBrief) -> str:
    key_points = "\n".join(f"- {p}" for p in brief.key_points)
    caveats = "\n".join(f"- {c}" for c in brief.caveats)
    return cleandoc(
        """
        你是严格的主编。把研究员的 brief 改成一段发得出去的正文：
        保留 brief 里的事实，去掉重复，照顾 caveats（至少带到一条），
        节奏自然不像机翻。最后写一句你用了什么基调。

        话题：{topic}

        研究员 brief：
        要点：
        {key_points}

        容易被误解的地方：
        {caveats}
        """
    ).format(topic=topic, key_points=key_points, caveats=caveats)


def editor_agent(topic: str, brief: ResearchBrief) -> PublishDraft:
    """Editor agent：把 brief 加工成发布稿。"""
    return polish(topic, brief)


# ---- 顶层函数：两个 agent 串联；就是函数调函数 ----
def pipeline(topic: str) -> PublishDraft:
    brief = research_agent(topic)
    return editor_agent(topic, brief)


def main() -> None:
    topic = "schema-as-CoT：用结构化字段顺序把 LLM 的推理步骤声明出来"
    print(f"话题：{topic}\n")
    draft = pipeline(topic)
    print(f"=== 标题 ===\n{draft.headline}")
    print(f"\n=== 正文 ===\n{draft.body}")
    print(f"\n=== 主编基调说明 ===\n{draft.tone_notes}")


if __name__ == "__main__":
    main()
