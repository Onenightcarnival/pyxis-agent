"""长期记忆：用 dict 做 KV store，一个 step 抽事实，一个 step 作答。

- 每次回答只读取长期记忆快照。
- 长期记忆是一个进程内 dict `_MEM`，换 Redis / SQLite / vec DB 就只改
  这部分。
- 两个 `@step` 各管一件事：
  - `extract_facts`：从用户这句话抽出值得记的键值对（如果有）。
  - `answer`：基于 `_MEM` 快照作答；需要查的键列在 `recall_keys`。
- Python 负责写入和查询，LLM 只生成 schema。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/memory_kv.py
"""

from __future__ import annotations

import os

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import flow, step

MODEL = "openai/gpt-5.4-nano"

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


# ---- 长期记忆 = 一个 dict，换存储只动这里 ----

_MEM: dict[str, str] = {}


# ---- Step 1：抽事实。字段就一个 dict，任务单一，nano 能稳定给 ----


class Fact(BaseModel):
    key: str = Field(description="snake_case，如 user_name / user_project / user_favorite_design")
    value: str = Field(description="事实内容，尽量短")


class Facts(BaseModel):
    facts: list[Fact] = Field(description="抽到的事实条目；没有就给空列表 []")


@step(output=Facts, model=MODEL, max_retries=3, client=openrouter)
def extract_facts(user: str) -> str:
    return (
        "你是信息抽取器。只抽关于用户自身的事实（姓名、项目、偏好、"
        "角色、居住地等）并放进 facts 列表。用户提问或闲聊时给空列表。\n"
        '例子：用户说"我叫张三"，facts=[{"key":"user_name","value":"张三"}]。\n'
        f'例子：用户问"我是谁"，facts=[]。\n用户原话：{user}'
    )


# ---- Step 2：作答。字段顺序：先列要查的键，再给 reply ----


class Answer(BaseModel):
    recall_keys: list[str] = Field(
        description="你需要从记忆快照取哪些键来回答？只列快照里实际存在的键。"
    )
    reply: str = Field(description="给用户的一句话回答")


@step(output=Answer, model=MODEL, max_retries=2, client=openrouter)
def answer(mem_snapshot: str, user: str) -> str:
    return (
        "你是只靠长期记忆作答的助手。没有对话历史，只有记忆快照。"
        "用户问到你之前该记住的东西时，从快照里选择相关键填 recall_keys，"
        "再在 reply 里引用那些键对应的值。快照里没有就诚实说不知道。\n"
        f"=== 记忆快照 ===\n{mem_snapshot or '（空）'}\n\n=== 用户这一轮 ===\n{user}"
    )


# ---- Flow：抽事实、写入、作答、可选读取。都是普通 Python ----


@flow
def chat(turns: list[str]) -> list[str]:
    replies: list[str] = []
    for user_msg in turns:
        print(f"\n用户：{user_msg}")

        new = extract_facts(user_msg).facts
        for f in new:
            _MEM[f.key] = f.value
            print(f"  [mem_write] {f.key} = {f.value}")

        snapshot = "\n".join(f"  {k} = {v}" for k, v in _MEM.items())
        a = answer(snapshot, user_msg)
        if a.recall_keys:
            recalled = {k: _MEM.get(k, "(not found)") for k in a.recall_keys}
            print(f"  [mem_read] {recalled}")
        print(f"  助手：{a.reply}")
        replies.append(a.reply)
    return replies


TURNS: list[str] = [
    "我叫 Chao，在做一个叫 pyxis 的 agent 框架。",
    "我最欣赏的设计是 schema-as-CoT。",
    "对了，我刚才说我在做啥来着？",
    "那我最欣赏什么设计？",
]


def main() -> None:
    chat(TURNS)
    print(f"\n=== 最终记忆快照 ===\n{_MEM}")


if __name__ == "__main__":
    main()
