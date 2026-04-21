"""mcp-demo 的 **Streamable HTTP** MCP server（用 FastMCP 写）。

和 `mcp_server.py`（stdio 传输）并列，证明 pyxis `HttpMCP` 与 `StdioMCP`
在调用面上完全对称——`Tool.run()` 层看不出来传输是管道还是 HTTP。

本 server 由 mcp-demo 后端 `Popen` 为独立 uvicorn 子进程（端口见
`app.py` 的 `HTTP_MCP_PORT`）。真场景里，把同一份 FastMCP 代码部署到
任何服务器，pyxis 端换成 `HttpMCP(url="https://...")` 即可——**client
代码一行都不用改**。

FastMCP 的 Streamable HTTP 默认用 `text/event-stream` 格式回响应体，
pyxis `_HttpConn` 已经兼容这两种响应（SSE 或 application/json）+
`Mcp-Session-Id` 头 + `notifications/initialized` 通知，均按 MCP 2024-11-05
规范处理。
"""

from __future__ import annotations

import base64
import json
import os
import re

from mcp.server.fastmcp import FastMCP

# 允许 app.py 通过环境变量覆写端口——避免 FastMCP 默认的 8000 撞车
mcp = FastMCP("http-demo", port=int(os.environ.get("MCP_HTTP_PORT", "8000")))


@mcp.tool()
def base64_encode(text: str) -> str:
    """把文本做 base64 编码。"""
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


@mcp.tool()
def slugify(text: str) -> str:
    """把一段文本转成 URL slug（小写 + 空白变 '-' + 去标点）。"""
    t = text.lower().strip()
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"[^a-z0-9\-]", "", t)
    return t


@mcp.tool()
def json_pretty(text: str) -> str:
    """把一段 JSON 字符串美化（2 空格缩进）；解析失败时原样返回。"""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(parsed, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
