"""批量把非结构化文本抽成 Pydantic 实例。
- 一个 `@step`：字段顺序为 summary、sentiment、topic、severity。
- 一个普通函数裹 for 循环，try/except 兜单条失败，整批不中断。
- 聚合就是 `Counter`。
LLM 输出可以直接交给 Counter、DataFrame 或数据库。
跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/batch_extraction.py
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import step

MODEL = "openai/gpt-5.4-nano"
openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)
# ---- 一批模拟的客户反馈 ----
FEEDBACKS: list[str] = [
    "下单后一周还没发货，客服也联系不上，非常失望。",
    "包装非常精美，质量也超出预期，给朋友做礼物很合适。",
    "APP 登录老是闪退，iPhone 15 上必现，希望尽快修。",
    "价格比隔壁贵 20%，但用起来确实顺手，值。",
    "物流超快当天就到了，但鞋码偏小一码，要换货。",
    "推荐系统好像完全不 personalize，首页一直推同几个商品。",
    "客服小姐姐态度特别好，秒回还主动帮我改地址，五星。",
    "账户被莫名封禁，申诉三天没人处理，已经在小红书吐槽了。",
]


# ---- Schema：字段顺序 = 先还原意思再下判断，不让 LLM 跳到标签 ----
class Feedback(BaseModel):
    summary: str = Field(description="一句话还原用户说的是什么")
    sentiment: Literal["positive", "neutral", "negative"] = Field(description="用户的情感倾向")
    topic: Literal["shipping", "quality", "app_bug", "price", "service", "other"] = Field(
        description="反馈集中在哪个话题"
    )
    severity: Literal["low", "medium", "high"] = Field(
        description="对业务影响的严重度：阻塞下单/封号 high；体验抱怨 medium；一般吐槽 low"
    )


@step(output=Feedback, model=MODEL, client=openrouter)
def extract(text: str) -> str:
    return (
        "你是一位客户反馈分析师。把每条反馈抽成结构化字段。"
        f"先用一句话还原用户说的是什么，再判断情感、话题与严重度。\n反馈：{text}"
    )


# ---- 批量跑：就是一个 for 循环；失败也不中断 ----
def extract_many(texts: list[str]) -> list[Feedback | None]:
    out: list[Feedback | None] = []
    for t in texts:
        try:
            out.append(extract(t))
        except Exception as e:
            print(f"  [抽取失败] {e.__class__.__name__}: {str(e)[:80]}")
            out.append(None)
    return out


def main() -> None:
    print(f"共 {len(FEEDBACKS)} 条反馈待抽取...\n")
    results = extract_many(FEEDBACKS)
    # ---- 聚合：就是普通 Python 统计 ----
    ok = [r for r in results if r is not None]
    print("\n=== 明细 ===")
    for raw, r in zip(FEEDBACKS, results, strict=True):
        if r is None:
            print(f"  [失败] {raw[:40]}...")
            continue
        print(f"  [{r.sentiment:8} / {r.topic:8} / {r.severity:6}] {r.summary}")
    sentiments = Counter(r.sentiment for r in ok)
    topics = Counter(r.topic for r in ok)
    high_severity = [r for r in ok if r.severity == "high"]
    print("\n=== 聚合 ===")
    print(f"成功率：{len(ok)}/{len(FEEDBACKS)}")
    print(f"情感分布：{dict(sentiments)}")
    print(f"话题分布：{dict(topics)}")
    print(f"高严重度条数：{len(high_severity)}")
    for r in high_severity:
        print(f"  - {r.summary}")


if __name__ == "__main__":
    main()
