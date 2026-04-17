"""End-to-end smoke tests against OpenRouter.

Skipped unless `OPENROUTER_API_KEY` is set in the environment.
Load via `uv run --env-file .env pytest tests/integration/`.
"""

from __future__ import annotations

import asyncio
import os

import instructor
import pytest
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, Field

from pyxis import InstructorClient, flow, step, trace


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
