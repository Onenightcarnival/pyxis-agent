"""批量结构化抽取：pyxis 的 sweet spot。

### 为什么把这个叫"sweet spot"

pyxis 的定位是 **agent-for-machine**：LLM 直接输出的是结构化数据，给下一段
Python 消费，不是给人看。批量抽取就是这个定位最纯的体现——

- 输入：一批非结构化文本（日志、工单、评论、邮件、论文摘要……）。
- 中间：LLM 把每条翻成同一个 Pydantic schema 的实例。
- 输出：一张**可以 group by / agg / 入库**的表，不是一段给人读的自然语言。

这类管线在 ChatGPT / Claude Desktop 风格的聊天 app 里做起来反而很别扭
（要从 markdown 里解析字段、文本可能漂移），在 pyxis 里几乎是 10 行：一个
`@step` 定结构，一个 `for` 跑完，一个 `Trace` 兜底聚合成本与失败。

### 把 extraction 当 pipeline 的两件配套设施

- **Trace 是 eval log**：跑完直接 `to_jsonl(...)` 就能回放、抽检、对比版本。
- **失败可观察**：LLM 抽不到结构时 step 会抛、trace 里 `error` 字段非空；
  本例把 try/except 包在外面，失败也进最终统计。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/batch_extraction.py
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from pyxis import flow, set_default_client, step, trace
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"


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
        description="对业务影响的严重度——阻塞下单/封号 high；体验抱怨 medium；一般吐槽 low"
    )


@step(output=Feedback, model=MODEL)
def extract(text: str) -> str:
    """你是一位客户反馈分析师。把每条反馈抽成结构化字段。
    先用一句话还原用户说的是什么，再判断情感、话题与严重度。"""
    return f"反馈：{text}"


# ---- 批量跑：就是一个 for 循环；失败也不中断 ----


@flow
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
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))

    print(f"共 {len(FEEDBACKS)} 条反馈待抽取...\n")
    with trace() as t:
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

    usage = t.total_usage()
    avg = usage.total_tokens / max(len(t.records), 1)
    print("\n=== 成本 ===")
    print(f"调用 {len(t.records)} 次；{usage.total_tokens} tokens；")
    print(f"平均 {avg:.0f} tokens/次；失败 {len(t.errors())} 次")


if __name__ == "__main__":
    main()
