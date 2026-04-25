"""RAG 最小版：检索 + 作答各一份代码。

- 检索：一个普通 Python 函数 `_retrieve`，关键词重叠度排序。换 vector DB
  就把函数体换成 `qdrant.search(...)`。
- 作答：一个 `@step`，schema 字段顺序为 citations、reasoning、answer。
- 编排：一个 `@flow` 把前两者串起来。

想让 LLM 自己决定要不要检索，可以把 `_retrieve` 包成 `Tool` 放进判别式联合
即可（参考 `examples/agent_tool_use.py`）。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/rag_minimal.py
"""

from __future__ import annotations

import os
import re

from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import flow, step

MODEL = "openai/gpt-5.4-nano"

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


# ---- "知识库"：几条关于 pyxis 的事实。真场景换成 vector DB / 文档库 ----

KB: list[str] = [
    "pyxis 是一个声明式思维链的 Python agent 框架，核心哲学是 code as prompt + schema as workflow。",
    "pyxis 里一次 LLM 调用叫 Step：docstring 是 system prompt，函数字符串返回是 user message。",
    "pyxis 里 Pydantic 模型的字段顺序就是思维链，LLM 必须自上而下把字段填完。",
    "pyxis 的多轮编排直接用普通 Python 写 if/for/函数组合，不提供 DSL 或 graph。",
    "pyxis 的 Tool 是 BaseModel 子类，带 run() 方法，动作即 schema、run() 即代码。",
    "pyxis 本体不做观测；生产用 Langfuse / OpenTelemetry / APM 直接适配 OpenAI SDK 调用。",
    "pyxis 用 instructor 库调用 OpenAI 兼容的 provider；client 直接传 OpenAI SDK 实例。",
    "Claude Desktop 面向聊天体验，pyxis 面向结构化输出和后续 Python 处理。",
]


def _retrieve(query: str, k: int = 3) -> list[str]:
    """最原始的检索：按关键词重叠度排序。真场景换成 vector search / BM25。"""
    tokens = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 1}
    scored = [(sum(1 for t in tokens if t in chunk.lower()), chunk) for chunk in KB]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in scored[:k] if score > 0]


# ---- Generation：字段顺序 = 先引用再作答，防止"先编后找"的幻觉 ----


class Answer(BaseModel):
    citations: list[str] = Field(description="你用到了哪几条上下文（原文复制）")
    reasoning: str = Field(description="基于引用的推理过程")
    answer: str = Field(description="给用户的最终答案，一两句话")


@step(output=Answer, model=MODEL, client=openrouter)
def answer_with_context(question: str, context: str) -> str:
    """你是严谨的问答助手。只能基于提供的上下文作答；
    上下文没说的就承认不知道，不要编。先列引用，再推理，最后给答案。"""
    return f"上下文：\n{context}\n\n问题：{question}"


# ---- Flow：retrieve -> augment -> generate，就是一个普通 Python 函数 ----


@flow
def rag(question: str) -> Answer:
    chunks = _retrieve(question)
    context = "\n".join(f"- {c}" for c in chunks) if chunks else "（无相关资料）"
    return answer_with_context(question, context)


def main() -> None:
    question = "pyxis 里的 schema-as-workflow 是什么意思？"
    print(f"问题：{question}\n")

    ans = rag(question)

    print("=== 检索到的片段 ===")
    for c in _retrieve(question):
        print(f"  - {c}")
    print("\n=== 引用 ===")
    for c in ans.citations:
        print(f"  - {c}")
    print(f"\n=== 推理 ===\n{ans.reasoning}")
    print(f"\n=== 回答 ===\n{ans.answer}")


if __name__ == "__main__":
    main()
