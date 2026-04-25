"""按用户意图分派到不同 handler。

- `@step route`：输出 `{reasoning, intent}`，`intent` 是 `Literal[...]`。
- 四个 handler 各是一个 `@step`，专门输入说明 + 专门 schema。
- `@flow` 里就是 `match intent:` 四个分支，想加分类、想加预处理、想
  fan-out 多个 handler，都是改这段 Python。
- router 用 `params={"temperature": 0}` 降低随机性；handler 不强制。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/router_dispatch.py
"""

from __future__ import annotations

import os
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import flow, step

MODEL = "openai/gpt-5.4-nano"

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


# ---- Router：Literal 标签即分派键 ----


class Route(BaseModel):
    reasoning: str = Field(description="为什么选这个意图，一两句")
    intent: Literal["sql", "code_debug", "creative", "other"] = Field(
        description="sql=查询数据；code_debug=排查代码；creative=写作/创意；other=兜底"
    )


@step(output=Route, model=MODEL, client=openrouter, params={"temperature": 0})
def route(user_input: str) -> str:
    return (
        "你是意图分类器。先解释一两句再给标签。\n"
        "sql：涉及表、查询、报表、统计；\n"
        "code_debug：贴了报错或代码片段问题；\n"
        "creative：写文案、写诗、起名等开放创作；\n"
        f"other：以上都不像的兜底。\n用户输入：{user_input}"
    )


# ---- 四个 handler：各有自己的 schema 和输入说明 ----


class SqlAnswer(BaseModel):
    sql: str = Field(description="一句可执行的 SQL")
    note: str = Field(description="一句话解释这段 SQL 做了什么")


@step(output=SqlAnswer, model=MODEL, client=openrouter)
def handle_sql(user_input: str) -> str:
    return f"你是数据分析师。为用户需求写一句可执行的 PostgreSQL。未知表就合理假设名字，写完后一句话说明。\n需求：{user_input}"


class DebugAnswer(BaseModel):
    likely_cause: str = Field(description="最可能的原因")
    fix: str = Field(description="建议怎么改")


@step(output=DebugAnswer, model=MODEL, client=openrouter)
def handle_debug(user_input: str) -> str:
    return f"你是代码 reviewer。只给最可能的原因和具体修法，不要泛泛而谈。\n问题：{user_input}"


class CreativeAnswer(BaseModel):
    idea: str = Field(description="核心创意点")
    text: str = Field(description="具体产出（文案 / 诗 / 名字 等）")


@step(output=CreativeAnswer, model=MODEL, client=openrouter)
def handle_creative(user_input: str) -> str:
    return f"你是有品味的文案。先点一句核心创意再给成品，不废话。\n需求：{user_input}"


class FallbackAnswer(BaseModel):
    reply: str = Field(description="礼貌而简短的回应")


@step(output=FallbackAnswer, model=MODEL, client=openrouter)
def handle_other(user_input: str) -> str:
    return (
        "你是礼貌的助手。用户问题不属于 SQL / 调试 / 创意任何一类，"
        f"给一句短回应引导他说得更具体。\n用户：{user_input}"
    )


# ---- 分派：普通 Python match/case ----


@flow
def dispatch(user_input: str) -> tuple[str, BaseModel]:
    r = route(user_input)
    match r.intent:
        case "sql":
            return r.intent, handle_sql(user_input)
        case "code_debug":
            return r.intent, handle_debug(user_input)
        case "creative":
            return r.intent, handle_creative(user_input)
        case "other":
            return r.intent, handle_other(user_input)


INPUTS: list[str] = [
    "帮我查最近 7 天每个用户的订单总额 Top 10",
    "这段 Python：`sum([1,2,3], start='x')` 为啥报 TypeError？",
    "给一个做声明式 agent 框架的创业项目起个中文名",
    "今天广州天气怎么样？",
]


def main() -> None:
    for inp in INPUTS:
        print(f"\n输入：{inp}")
        intent, ans = dispatch(inp)
        print(f"  [分派到 {intent}]")
        print(f"  {ans.model_dump_json(indent=2)}")


if __name__ == "__main__":
    main()
