"""示例用的 stdio MCP server。
这个文件用 `mcp.server.fastmcp.FastMCP` 定义几个工具。pyxis 端通过
`MCPServer + StdioMCP(command=..., args=["path/to/server.py"])` 启动子进程并连接。
`examples/mcp_tool_use.py` 会自动把它作为子进程启动，也可以单独运行调试：
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
