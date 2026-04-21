"""RAG 的最小版本——pyxis 视角下没有"RAG 抽象"。

行业里 RAG（retrieval-augmented generation）往往被包成一个专门的 pipeline
对象，吃 vector store、retriever、reranker 一堆组件。但拆开看骨架就三步：

1. **Retrieve**：拿 query 去某处取回相关片段——**这是普通 Python 函数**。
2. **Augment**：把取回的片段拼进 prompt——**这是字符串拼接**。
3. **Generate**：让 LLM 基于片段回答——**这是一个 `@step`**。

所以在 pyxis 里：一个 `@step`，加一个 Python 函数做检索。就是这样。没有
`RAGPipeline` 类、没有 `Retriever` 接口、没有隐藏的魔法。想换成真 vector
DB？把 `_retrieve` 的实现换成 `qdrant_client.search(...)` 就行，step 不动。
想让 LLM 自己决定要不要检索？把 `_retrieve` 包成 `Tool`，塞进判别式联合，
和 `examples/agent_tool_use.py` 一个样子——依然没有新原语。

本示例用最原始的关键词匹配做检索，这样没有额外依赖，聚焦讲结构。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/rag_minimal.py
"""

from __future__ import annotations

import os
import re

from pydantic import BaseModel, Field

from pyxis import flow, set_default_client, step, trace
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"


# ---- "知识库"：几条关于 pyxis 的事实。真场景换成 vector DB / 文档库 ----

KB: list[str] = [
    "pyxis 是一个声明式思维链的 Python agent 框架，核心哲学是 code as prompt + schema as workflow。",
    "pyxis 里一次 LLM 调用叫 Step：docstring 是 system prompt，函数字符串返回是 user message。",
    "pyxis 里 Pydantic 模型的字段顺序就是思维链，LLM 必须自上而下把字段填完。",
    "pyxis 的多轮编排直接用普通 Python 写 if/for/函数组合，不提供 DSL 或 graph。",
    "pyxis 的 Tool 是 BaseModel 子类，带 run() 方法，动作即 schema、run() 即代码。",
    "pyxis 的 trace() 是基于 ContextVar 的观测器，跨 asyncio task 自动传播。",
    "pyxis 用 instructor 库调用 OpenAI 兼容的 provider，生产推荐接 Langfuse 做可观测。",
    "Claude Desktop 追求丝滑 chat 体感，pyxis 对标的是 agent-for-machine——LLM 产结构化数据喂下一段 Python。",
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


@step(output=Answer, model=MODEL)
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
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))

    question = "pyxis 里的 schema-as-workflow 是什么意思？"
    print(f"问题：{question}\n")

    with trace() as t:
        ans = rag(question)

    print("=== 检索到的片段 ===")
    for c in _retrieve(question):
        print(f"  - {c}")
    print("\n=== 引用 ===")
    for c in ans.citations:
        print(f"  - {c}")
    print(f"\n=== 推理 ===\n{ans.reasoning}")
    print(f"\n=== 回答 ===\n{ans.answer}")
    print(f"\n=== 成本 ===\n调用 {len(t.records)} 次；{t.total_usage().total_tokens} tokens")


if __name__ == "__main__":
    main()
