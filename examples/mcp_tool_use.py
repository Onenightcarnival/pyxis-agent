"""MCP 适配层示例：把远端 MCP 工具和 native pyxis 工具**拼进同一个判别式联合**。

关键点：
- `MCPServer` 是声明式数据（Pydantic）；`mcp_toolset(server)` 是异步
  上下文管理器，入口连接 + `tools/list` + 翻译，退出时清理子进程。
- 返回的 `list[type[Tool]]` 就是普通 `Tool` 子类，可以和 `Calculate` /
  `Finish` 这些 native 工具**直接拼进一个 `Annotated[... | ..., Field(
  discriminator="kind")]`**。
- agent loop 里只调 `d.action.run()` 一行——它根本不知道工具从哪来。

跑起来（用内置的 demo MCP server，零外部依赖）：

    OPENROUTER_API_KEY=... uv run --env-file .env \\
        python examples/mcp_tool_use.py

替换成真 MCP server：把下面 `StdioMCP(command=..., args=[...])` 改成
例如 `StdioMCP(command="uvx", args=["mcp-server-filesystem", "/tmp"])`。
"""

from __future__ import annotations

import os
import sys
from functools import reduce
from operator import or_
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from pyxis import Tool, flow, set_default_client, step, trace
from pyxis.mcp import MCPServer, StdioMCP, mcp_toolset
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"
DEMO_SERVER = Path(__file__).parent / "_mcp_demo_server.py"


# ---- native 工具：一个用 @tool 都嫌重的就手写 ----


class Finish(Tool):
    """停止并给出最终答案。"""

    kind: Literal["finish"] = "finish"
    answer: str = Field(description="给用户的最终答案")

    def run(self) -> str:
        return self.answer


# ---- agent loop：和 agent_tool_use.py 如出一辙，只是 tool_classes 是动态拼的 ----


@flow
async def agent(question: str, max_steps: int = 10) -> str:
    # 声明 MCP server：这里指向同目录的 demo server；换成任何 stdio MCP 都行
    server = MCPServer(
        name="demo",
        transport=StdioMCP(command=sys.executable, args=[str(DEMO_SERVER)]),
    )

    async with mcp_toolset(server) as mcp_tools:
        # 混合注册 = 拼 list。MCP 生成的和 native 的，都是 type[Tool]
        tool_classes: list[type[Tool]] = [*mcp_tools, Finish]

        # 动态判别式联合：`reduce(or_, tool_classes)` 相当于 T1 | T2 | T3 ...
        Action = Annotated[reduce(or_, tool_classes), Field(discriminator="kind")]

        class Decision(BaseModel):
            """schema-as-CoT：先思考，再发一次工具调用。"""

            thought: str = Field(description="先推理接下来要做什么")
            action: Action = Field(description="这一步要调用的工具")  # type: ignore[valid-type]

        @step(output=Decision, model=MODEL, max_retries=2)
        async def decide(question: str, scratch: str) -> str:
            """你是一个会推理的 agent。规则：

            1. **先仔细读"草稿板"。** 草稿板里已经出现过的工具调用和结果，是
               过去的事实。**不要重复调用**——要基于它推进下一步。
            2. 每一轮返回一个 Decision：`thought` 写你基于草稿板的**新推理**
               （不要复述任务），`action` 是接下来要做的**一次**工具调用。
            3. `action` 必须是叶子工具（例如 `{"kind": "reverse", "text": "..."}`），
               不要嵌套 Decision。
            4. 当你已经能从草稿板上的结果回答问题时，立刻用
               `{"kind": "finish", "answer": "..."}` 停止。"""
            return f"问题：{question}\n\n草稿板（到目前为止）：\n{scratch or '（空）'}"

        scratch: list[str] = []
        for i in range(max_steps):
            d = await decide(question, "\n".join(scratch))
            obs = d.action.run()  # ← 唯一的调用点；不 isinstance 分派 native / MCP
            print(f"[step {i}] {d.action.kind}({d.action.model_dump_json()}) -> {obs}")
            scratch.append(f"thought: {d.thought}")
            scratch.append(f"{d.action.kind}({d.action.model_dump_json()}) -> {obs}")
            if isinstance(d.action, Finish):
                return obs
        raise RuntimeError(f"达到 max_steps={max_steps} 仍未结束\n草稿板：\n" + "\n".join(scratch))


def _configure() -> None:
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))


async def main() -> None:
    _configure()
    with trace() as t:
        answer = await agent("把 'pyxis is declarative' 这句话反转，然后数一下它的单词数。")
    print("=" * 60, "TRACE", "=" * 60, sep="\n")
    for i, rec in enumerate(t.records, 1):
        print(f"\n[{i}] step={rec.step}")
        print(rec.output.model_dump_json(indent=2))
    print("=" * 60, "ANSWER", "=" * 60, sep="\n")
    print(answer)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
