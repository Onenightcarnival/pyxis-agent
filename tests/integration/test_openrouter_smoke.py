"""对 OpenRouter 的端到端烟雾测试。

没有设置 `OPENROUTER_API_KEY` 时整体跳过。
通过 `uv run --env-file .env pytest tests/integration/` 加载环境变量运行。
"""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

import pytest
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, Field

from pyxis import flow, step, tool


@pytest.fixture(scope="module")
def openrouter_sync() -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set; skipping integration test")
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return OpenAI(api_key=key, base_url=base_url)


@pytest.fixture(scope="module")
def openrouter_async() -> AsyncOpenAI:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set; skipping integration test")
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return AsyncOpenAI(api_key=key, base_url=base_url)


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


def test_step_round_trip_produces_valid_schema(openrouter_sync: OpenAI, model: str) -> None:
    @step(output=Classification, model=model, client=openrouter_sync)
    def classify(text: str) -> str:
        """You classify text. Observe first, then categorize, then score confidence."""
        return f"Text: {text}"

    result = classify("Define the Big-O complexity of quicksort.")
    assert isinstance(result, Classification)
    assert result.observation
    assert result.category
    assert 0.0 <= result.confidence <= 1.0


def test_flow_multi_step(openrouter_sync: OpenAI, model: str) -> None:
    @step(output=Classification, model=model, client=openrouter_sync)
    def classify(text: str) -> str:
        """You classify text. Observe, categorize, score."""
        return text

    @step(output=Summary, model=model, client=openrouter_sync)
    def summarize(c: Classification) -> str:
        """You summarize classified text into a topic and 3 bullets."""
        return f"Classified as {c.category} (conf={c.confidence}). Note: {c.observation}"

    @flow
    def digest(text: str) -> Summary:
        return summarize(classify(text))

    s = digest("Claude Opus 4.7 supports a 1M token context window.")

    assert isinstance(s, Summary)
    assert len(s.bullets) >= 1


def test_async_parallel_steps(openrouter_async: AsyncOpenAI, model: str) -> None:
    @step(output=Classification, model=model, client=openrouter_async)
    async def classify(text: str) -> str:
        """You classify text. Observe, categorize, score."""
        return text

    async def fan_out():
        return await asyncio.gather(
            classify("Python 3.12 supports PEP 695 type parameters."),
            classify("Claude supports long context windows."),
            classify("The capital of France is Paris."),
        )

    results = asyncio.run(fan_out())
    assert len(results) == 3
    assert all(isinstance(r, Classification) for r in results)


def test_live_tool_decorator_agent(openrouter_sync: OpenAI, model: str) -> None:
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

    @step(output=Decision, model=model, max_retries=3, client=openrouter_sync)
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

    answer = agent("7 * 6 等于多少？")
    assert "42" in answer


def test_live_stream_yields_progressively(openrouter_sync: OpenAI, model: str) -> None:
    """真实 partial streaming：字段逐步出现，最后一帧所有必选字段都齐了。"""

    class Analysis(BaseModel):
        observation: str = Field(description="你注意到什么")
        reasoning: str = Field(description="为什么这重要")
        conclusion: str = Field(description="一句话结论")

    @step(output=Analysis, model=model, client=openrouter_sync)
    def analyze(topic: str) -> str:
        """你是严谨的分析师。观察，推理，结论。"""
        return f"主题：{topic}"

    frames: list[Analysis] = []
    for partial in analyze.stream("为什么雨是咸的"):
        frames.append(partial)

    assert len(frames) >= 1
    final = frames[-1]
    assert final.observation
    assert final.reasoning
    assert final.conclusion


def test_live_human_in_the_loop_review(openrouter_sync: OpenAI, model: str) -> None:
    """真实 LLM 出计划 → 模拟人工审核后继续。"""
    from pyxis import ask_human, flow, run_flow

    class Plan(BaseModel):
        goal: str = Field(description="一行复述目标")
        steps: list[str] = Field(description="3-5 个具体步骤")

    class Decision(BaseModel):
        approve: bool
        comments: str | None = None

    @step(output=Plan, model=model, client=openrouter_sync)
    def make_plan(q: str) -> str:
        """你是严谨的规划者。先复述目标，再列 3-5 个具体步骤。"""
        return f"问题：{q}"

    @flow
    def plan_then_review(q: str):
        plan = make_plan(q)
        decision: Decision = yield ask_human("审核", schema=Decision, plan=plan.goal)
        if not decision.approve:
            return {"status": "rejected"}
        return {"status": "done", "plan_goal": plan.goal}

    result = run_flow(
        plan_then_review("怎么演示声明式 CoT 框架？"),
        on_ask=lambda q: Decision(approve=True),
    )
    assert result["status"] == "done"
    assert result["plan_goal"]


def test_live_step_with_params(openrouter_sync: OpenAI, model: str) -> None:
    """params 透传：把 temperature=0 发给 provider，不应被 pyxis 拦截。"""

    @step(
        output=Classification,
        model=model,
        client=openrouter_sync,
        params={"temperature": 0},
    )
    def classify(text: str) -> str:
        """You classify text. Observe, categorize, score."""
        return text

    result = classify("What is 2+2?")
    assert isinstance(result, Classification)
