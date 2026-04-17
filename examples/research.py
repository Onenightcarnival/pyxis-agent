"""End-to-end demo of declarative chain-of-thought.

Shows both axes:
- implicit CoT: schema field order drives a single LLM call's reasoning
- explicit CoT: plain Python orchestrates multiple steps

Run against OpenRouter:
    OPENROUTER_API_KEY=sk-or-... uv run python examples/research.py
"""

from __future__ import annotations

import os

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import InstructorClient, flow, set_default_client, step

MODEL = "openai/gpt-5.4-nano"


# --- Schemas: the chain of thought IS the field order ---


class Analysis(BaseModel):
    """observe -> reason -> conclude, in that order."""

    observation: str = Field(description="What you notice about the topic")
    reasoning: str = Field(description="Why that observation matters")
    conclusion: str = Field(description="A one-sentence takeaway")


class Plan(BaseModel):
    """goal -> steps -> next action, in that order."""

    goal: str = Field(description="Restate the user's goal in one line")
    steps: list[str] = Field(description="Break it into 3-5 concrete steps")
    next_action: str = Field(description="The first concrete step to execute")


# --- Steps: docstring = system prompt, return = user message ---


@step(output=Analysis, model=MODEL)
def analyze(topic: str) -> str:
    """You are a careful analyst. Observe, then reason, then conclude."""
    return f"Topic: {topic}"


@step(output=Plan, model=MODEL)
def plan_from_analysis(a: Analysis) -> str:
    """You are a meticulous planner. Turn the analysis into an action plan."""
    return f"Analysis:\n{a.model_dump_json(indent=2)}"


# --- Flow: explicit orchestration = plain Python ---


@flow
def research(topic: str) -> Plan:
    """Research: first analyze, then plan from the analysis."""
    a = analyze(topic)
    return plan_from_analysis(a)


def _configure_openrouter() -> None:
    key = os.environ["OPENROUTER_API_KEY"]
    openai = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    set_default_client(InstructorClient(instructor.from_openai(openai)))


def main() -> None:
    _configure_openrouter()
    result, t = research.run_traced("building an agent framework with declarative CoT")

    print("=" * 60)
    print("TRACE")
    print("=" * 60)
    for i, rec in enumerate(t.records, 1):
        print(f"\n[{i}] step={rec.step}  model={rec.model}")
        print(rec.output.model_dump_json(indent=2))

    print("\n" + "=" * 60)
    print("FINAL")
    print("=" * 60)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
