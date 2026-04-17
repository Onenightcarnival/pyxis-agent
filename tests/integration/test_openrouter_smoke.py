"""对 OpenRouter 的端到端烟雾测试。

没有设置 `OPENROUTER_API_KEY` 时整体跳过。
通过 `uv run --env-file .env pytest tests/integration/` 加载环境变量运行。
"""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

import instructor
import pytest
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, Field

from pyxis import InstructorClient, flow, step, tool, trace


@pytest.fixture(scope="module")
def openrouter() -> InstructorClient:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set; skipping integration test")
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return InstructorClient(
        instructor_client=instructor.from_openai(OpenAI(api_key=key, base_url=base_url)),
        async_instructor_client=instructor.from_openai(AsyncOpenAI(api_key=key, base_url=base_url)),
    )


@pytest.fixture(scope="module")
def model() -> str:
    return os.environ.get("OPENROUTER_MODEL", "openai/gpt-5.4-nano")


class Classification(BaseModel):
    observation: str = Field(description="What you notice about the input")
    category: str = Field(description="One of: technical, creative, factual, other")
    confidence: float = Field(description="A value between 0 and 1")


class Summary(BaseModel):
    topic: str = Field(description="Restate the topic in ≤10 words")
    bullets: list[str] = Field(description="3 key bullet points")


def test_step_round_trip_produces_valid_schema(openrouter: InstructorClient, model: str) -> None:
    @step(output=Classification, model=model, client=openrouter)
    def classify(text: str) -> str:
        """You classify text. Observe first, then categorize, then score confidence."""
        return f"Text: {text}"

    result = classify("Define the Big-O complexity of quicksort.")
    assert isinstance(result, Classification)
    assert result.observation
    assert result.category
    assert 0.0 <= result.confidence <= 1.0


def test_flow_multi_step_with_trace(openrouter: InstructorClient, model: str) -> None:
    @step(output=Classification, model=model, client=openrouter)
    def classify(text: str) -> str:
        """You classify text. Observe, categorize, score."""
        return text

    @step(output=Summary, model=model, client=openrouter)
    def summarize(c: Classification) -> str:
        """You summarize classified text into a topic and 3 bullets."""
        return f"Classified as {c.category} (conf={c.confidence}). Note: {c.observation}"

    @flow
    def digest(text: str) -> Summary:
        return summarize(classify(text))

    with trace() as t:
        s = digest("Claude Opus 4.7 supports a 1M token context window.")

    assert isinstance(s, Summary)
    assert len(s.bullets) >= 1
    assert [r.step for r in t.records] == ["classify", "summarize"]
    assert isinstance(t.records[0].output, Classification)
    assert isinstance(t.records[1].output, Summary)


def test_async_parallel_steps_share_trace(openrouter: InstructorClient, model: str) -> None:
    @step(output=Classification, model=model, client=openrouter)
    async def classify(text: str) -> str:
        """You classify text. Observe, categorize, score."""
        return text

    async def fan_out():
        with trace() as t:
            results = await asyncio.gather(
                classify("Python 3.12 supports PEP 695 type parameters."),
                classify("Claude supports long context windows."),
                classify("The capital of France is Paris."),
            )
        return results, t

    results, t = asyncio.run(fan_out())
    assert len(results) == 3
    assert all(isinstance(r, Classification) for r in results)
    assert len(t.records) == 3
    assert all(r.step == "classify" for r in t.records)


def test_live_step_captures_usage(openrouter: InstructorClient, model: str) -> None:
    @step(output=Classification, model=model, client=openrouter)
    def classify(text: str) -> str:
        """You classify text. Observe, categorize, score."""
        return text

    with trace() as t:
        classify("What is 2+2?")

    (rec,) = t.records
    assert rec.usage is not None
    assert rec.usage.prompt_tokens > 0
    assert rec.usage.completion_tokens > 0
    assert rec.usage.total_tokens >= rec.usage.prompt_tokens + rec.usage.completion_tokens - 1
    total = t.total_usage()
    assert total.total_tokens == rec.usage.total_tokens

    exported = t.to_dict()
    assert exported["records"][0]["usage"]["total_tokens"] == rec.usage.total_tokens


def test_live_tool_decorator_agent(openrouter: InstructorClient, model: str) -> None:
    """用 `@tool` 装饰的纯函数在真实 LLM 上完成一个 ReAct 风格小 agent。"""

    @tool
    def calculate(expression: str) -> str:
        """算一个简单的算术表达式。"""
        return str(eval(expression, {"__builtins__": {}}, {}))

    @tool
    def finish(answer: str) -> str:
        """停止并给出最终答案。"""
        return answer

    Action = Annotated[calculate | finish, Field(discriminator="kind")]

    class Decision(BaseModel):
        thought: str
        action: Action

    @step(output=Decision, model=model, max_retries=2, client=openrouter)
    def decide(question: str, scratch: str) -> str:
        """你是一个会推理的 agent。先思考，再恰好发一次工具调用，
        拿到答案用 `finish` 结束。"""
        return f"问题：{question}\n草稿：\n{scratch or '（空）'}"

    @flow
    def agent(q: str, max_steps: int = 4) -> str:
        scratch: list[str] = []
        for _ in range(max_steps):
            d = decide(q, "\n".join(scratch))
            scratch += [f"thought: {d.thought}", f"obs: {d.action.run()}"]
            if isinstance(d.action, finish):
                return d.action.run()
        raise RuntimeError("达到 max_steps 仍未结束")

    with trace() as t:
        answer = agent("7 * 6 等于多少？")

    assert "42" in answer
    steps = [type(r.output.action).__name__ for r in t.records]
    assert "Calculate" in steps
    assert "Finish" in steps


def test_live_stream_yields_progressively(openrouter: InstructorClient, model: str) -> None:
    """真实 partial streaming：字段逐步出现，最后一帧所有必选字段都齐了。"""

    class Analysis(BaseModel):
        observation: str = Field(description="你注意到什么")
        reasoning: str = Field(description="为什么这重要")
        conclusion: str = Field(description="一句话结论")

    @step(output=Analysis, model=model, client=openrouter)
    def analyze(topic: str) -> str:
        """你是严谨的分析师。观察，推理，结论。"""
        return f"主题：{topic}"

    frames: list[Analysis] = []
    with trace() as t:
        for partial in analyze.stream("为什么雨是咸的"):
            frames.append(partial)

    assert len(frames) >= 1
    final = frames[-1]
    assert final.observation
    assert final.reasoning
    assert final.conclusion
    # 只有一条 TraceRecord，output 是最终帧
    (rec,) = t.records
    assert rec.output is not None
    assert rec.output.observation == final.observation
