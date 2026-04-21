"""示例用的 stdio MCP server——**用 FastMCP 写的正经姿势**，和实际工作流对齐。

真场景：你会用 `mcp.server.fastmcp.FastMCP`（或独立包 `fastmcp`）把业务
函数 `@mcp.tool()` 一装饰，schema / JSON-RPC 分派 / 传输全由 FastMCP 包办。
然后 pyxis 端用 `MCPServer + StdioMCP(command=..., args=["path/to/server.py"])`
起一个子进程连上来——这就是你日常的 MCP server ↔ agent 集成方式。

跑起来（由 `examples/mcp_tool_use.py` 自动作为子进程启动；也能独跑调试）：

    uv run python examples/_mcp_demo_server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pyxis-demo")


@mcp.tool()
def word_count(text: str) -> int:
    """数一段文本里的单词数（按空白切分）。"""
    return len(text.split())


@mcp.tool()
def reverse(text: str) -> str:
    """把字符串反转。"""
    return text[::-1]


if __name__ == "__main__":
    mcp.run()  # 默认 stdio 传输
