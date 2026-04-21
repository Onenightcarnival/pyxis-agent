"""mcp-demo 的 stdio MCP server（用 FastMCP 写）。

`FastMCP` 把 schema 推断 / JSON-RPC 分派 / 传输选择全包了——这是**你自己
写业务 MCP server 时的正经姿势**。本文件由 `app.py` 通过
`StdioMCP(command=..., args=[str(MCP_STDIO_SCRIPT)])` 作为子进程启动。

真场景里把下面这些 `@mcp.tool()` 换成你的业务函数就行；其他都一样。
"""

from __future__ import annotations

import datetime as _dt

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("stdio-demo")


@mcp.tool()
def word_count(text: str) -> int:
    """数一段文本里的单词数（按空白切分）。"""
    return len(text.split())


@mcp.tool()
def reverse(text: str) -> str:
    """把字符串反转。"""
    return text[::-1]


@mcp.tool()
def upper(text: str) -> str:
    """把字符串转大写。"""
    return text.upper()


@mcp.tool()
def now() -> str:
    """返回 server 本地的当前 ISO 时间戳。"""
    return _dt.datetime.now().isoformat()


if __name__ == "__main__":
    mcp.run()  # 默认 stdio 传输
