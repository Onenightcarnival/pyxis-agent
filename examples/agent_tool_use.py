"""声明式思维链 + 工具调用的 agent 示例。显式循环写在普通 Python 里。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/agent_tool_use.py
"""

from __future__ import annotations

import os
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from pyxis import Tool, flow, set_default_client, step, trace
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"


# ---- 工具：用 schema 声明，用 run() 实现 ----


class Calculate(Tool):
    """计算一个简单的算术表达式，返回数值结果。"""

    kind: Literal["calculate"] = "calculate"
    expression: str = Field(description="一个 Python 数学表达式，例如 '2*(3+4)'")

    def run(self) -> str:
        return str(eval(self.expression, {"__builtins__": {}}, {}))


class Finish(Tool):
    """停止并向用户给出最终答案。"""

    kind: Literal["finish"] = "finish"
    answer: str = Field(description="给用户的最终答案")

    def run(self) -> str:
        return self.answer


Action = Annotated[Calculate | Finish, Field(discriminator="kind")]


class Decision(BaseModel):
    """schema-as-CoT：先思考，再发出一次工具调用。"""

    thought: str = Field(description="先推理一下接下来要做什么")
    action: Action = Field(description="这一步要调用的工具")


@step(output=Decision, model=MODEL)
def decide(question: str, scratch: str) -> str:
    """你是一个会推理的 agent。先思考，再**恰好**发一次工具调用。
    拿到答案之后就用 `finish` 工具停止。"""
    return f"问题：{question}\n\n草稿板（到目前为止）：\n{scratch or '（空）'}"


# ---- 显式编排：循环就是一个普通 @flow ----


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
    raise RuntimeError("达到 max_steps 仍未结束")


def _configure() -> None:
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))


def main() -> None:
    _configure()
    with trace() as t:
        answer = agent("(17 * 23) + 41 等于多少？")
    print("=" * 60, "TRACE", "=" * 60, sep="\n")
    for i, rec in enumerate(t.records, 1):
        print(f"\n[{i}] step={rec.step}")
        print(rec.output.model_dump_json(indent=2))
    print("=" * 60, "ANSWER", "=" * 60, sep="\n")
    print(answer)


if __name__ == "__main__":
    main()
