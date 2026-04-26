"""把 FastMCP server 工具和本地 pyxis 工具放进同一个判别式联合。

- server 端用 `mcp.server.fastmcp.FastMCP` 写（见 `_mcp_demo_server.py`），
  也可以直接连接已有 FastMCP server（`uvx mcp-server-filesystem
  /tmp` 之类）。
- pyxis 端 `MCPServer + StdioMCP(command=..., args=[...])` 起子进程，
  或 `HttpMCP(url=...)` 连远端；`async with mcp_toolset(server) as tools:`
  拿到 `list[type[Tool]]`。
- 把远端 tools 放进判别式联合，`@step(output=Decision)` 的 `action` 字段
  就能统一分派，`d.action.run()` 一行调用不区分来源。

换生产 MCP server：`StdioMCP(...)` 指到真 server 的启动命令
（`StdioMCP(command="uvx", args=["mcp-server-filesystem", "/tmp"])`），
或 `HttpMCP(url="https://your.host/mcp", headers={"Authorization": "..."})`。
本文件其他代码不用动。

跑起来（demo 会自动 Popen `_mcp_demo_server.py` 做 stdio 子进程）：

    OPENROUTER_API_KEY=... uv run --env-file .env \\
        python examples/mcp_tool_use.py
"""

from __future__ import annotations

import os
import sys
from functools import reduce
from inspect import cleandoc
from operator import or_
from pathlib import Path
from typing import Annotated, Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from pyxis import Tool, step
from pyxis.mcp import MCPServer, StdioMCP, mcp_toolset

MODEL = "openai/gpt-5.4-nano"
DEMO_SERVER = Path(__file__).parent / "_mcp_demo_server.py"
openrouter = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


# ---- native 工具：一个用 @tool 都嫌重的就手写 ----
class Finish(Tool):
    """停止并给出最终答案。"""

    kind: Literal["finish"] = "finish"
    answer: str = Field(description="给用户的最终答案")

    def run(self) -> str:
        return self.answer


# ---- agent loop：和 agent_tool_use.py 如出一辙，只是 tool_classes 是动态拼的 ----
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
            """先判断下一步动作，再发一次工具调用。"""

            thought: str = Field(description="先推理接下来要做什么")
            action: Action = Field(description="这一步要调用的工具")  # type: ignore[valid-type]

        @step(output=Decision, model=MODEL, max_retries=2, client=openrouter)
        async def decide(question: str, scratch: str) -> str:
            return cleandoc(
                """
                规则：
                1. 先仔细读草稿板。草稿板里已经出现过的工具调用和结果，
                   是过去的事实。不要重复调用，要基于它推进下一步。
                2. 每一轮返回一个 Decision：`thought` 写你基于草稿板的新推理
                   （不要复述任务），`action` 是接下来要做的一次工具调用。
                3. `action` 必须是叶子工具（例如 `{{"kind": "reverse", "text": "..."}}`），
                   不要嵌套 Decision。
                4. 当你已经能从草稿板上的结果回答问题时，立刻用
                   `{{"kind": "finish", "answer": "..."}}` 停止。

                问题：{question}

                草稿板（到目前为止）：
                {scratch}
                """
            ).format(question=question, scratch=scratch or "（空）")

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


async def main() -> None:
    answer = await agent("把 'pyxis is declarative' 这句话反转，然后数一下它的单词数。")
    print("=" * 60)
    print("答案：", answer)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
