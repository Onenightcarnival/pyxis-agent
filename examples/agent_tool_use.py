"""Declarative-CoT agent with tools. Explicit loop in plain Python.

Run with:
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/agent_tool_use.py
"""

from __future__ import annotations

import os
from typing import Annotated, Literal

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from pyxis import InstructorClient, Tool, flow, set_default_client, step, trace

MODEL = "openai/gpt-5.4-nano"


# --- Tools: declared as schemas, implemented via run() ---


class Calculate(Tool):
    """Evaluate a simple arithmetic expression and return the numeric result."""

    kind: Literal["calculate"] = "calculate"
    expression: str = Field(description="a Python math expression, e.g. '2*(3+4)'")

    def run(self) -> str:
        return str(eval(self.expression, {"__builtins__": {}}, {}))


class Finish(Tool):
    """Stop and report the final answer to the user's question."""

    kind: Literal["finish"] = "finish"
    answer: str = Field(description="the final answer phrased for the user")

    def run(self) -> str:
        return self.answer


Action = Annotated[Calculate | Finish, Field(discriminator="kind")]


class Decision(BaseModel):
    """Schema-as-CoT: thought first, then a tool call."""

    thought: str = Field(description="reason about what to do next")
    action: Action = Field(description="the tool to invoke now")


@step(output=Decision, model=MODEL)
def decide(question: str, scratch: str) -> str:
    """You are a reasoning agent. Think, then emit exactly one tool call.
    Stop with the `finish` tool once you have the answer."""
    return f"Question: {question}\n\nScratchpad so far:\n{scratch or '(empty)'}"


# --- Explicit orchestration: the loop is a plain @flow ---


@flow
def agent(question: str, max_steps: int = 6) -> str:
    scratch: list[str] = []
    for _ in range(max_steps):
        d = decide(question, "\n".join(scratch))
        scratch.append(f"thought: {d.thought}")
        obs = d.action.run()
        scratch.append(f"{d.action.kind}({d.action.model_dump_json()}) -> {obs}")
        if isinstance(d.action, Finish):
            return obs
    raise RuntimeError("max_steps exhausted")


def _configure() -> None:
    key = os.environ["OPENROUTER_API_KEY"]
    oai = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    set_default_client(InstructorClient(instructor.from_openai(oai)))


def main() -> None:
    _configure()
    with trace() as t:
        answer = agent("What is (17 * 23) + 41?")
    print("=" * 60, "TRACE", "=" * 60, sep="\n")
    for i, rec in enumerate(t.records, 1):
        print(f"\n[{i}] step={rec.step}")
        print(rec.output.model_dump_json(indent=2))
    print("=" * 60, "ANSWER", "=" * 60, sep="\n")
    print(answer)


if __name__ == "__main__":
    main()
