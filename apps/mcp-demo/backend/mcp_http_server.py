"""mcp-demo 内置的 **Streamable HTTP** MCP server——独立的 FastAPI 进程。

和 `mcp_server.py`（stdio 传输）并列，证明 pyxis `HttpMCP` 与 `StdioMCP`
在调用面上完全等价。本 demo 由 mcp-demo 后端在启动时 `subprocess.Popen`
起一个独立的 uvicorn 进程托管（端口见 `app.py` 的 HTTP_MCP_PORT）。

协议范围：`initialize` / `tools/list` / `tools/call`——最小可用的 MCP 子集。
请求 / 响应用 JSON-RPC over HTTP（单条 POST 一次请求/响应）。
"""

from __future__ import annotations

import base64
import json
import re

from fastapi import FastAPI, Request

TOOLS = [
    {
        "name": "base64_encode",
        "description": "把文本做 base64 编码。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要编码的文本"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "slugify",
        "description": "把一段文本转成 URL slug（小写 + 空白变 '-' + 去标点）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要转 slug 的文本"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "json_pretty",
        "description": "把一段 JSON 字符串美化（2 空格缩进）；解析失败时原样返回。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "JSON 字符串"},
            },
            "required": ["text"],
        },
    },
]


app = FastAPI(title="pyxis mcp-demo HTTP MCP server")


def _call(name: str, args: dict) -> dict:
    if name == "base64_encode":
        encoded = base64.b64encode(args["text"].encode("utf-8")).decode("ascii")
        return {"content": [{"type": "text", "text": encoded}]}
    if name == "slugify":
        text = args["text"].lower().strip()
        text = re.sub(r"\s+", "-", text)
        text = re.sub(r"[^a-z0-9\-]", "", text)
        return {"content": [{"type": "text", "text": text}]}
    if name == "json_pretty":
        try:
            parsed = json.loads(args["text"])
            pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pretty = args["text"]
        return {"content": [{"type": "text", "text": pretty}]}
    raise ValueError(f"未知工具：{name!r}")


@app.post("/mcp")
async def mcp_endpoint(req: Request) -> dict:
    body = await req.json()
    rid = body.get("id")
    method = body["method"]
    params = body.get("params") or {}
    try:
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {}}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            result = _call(params["name"], params.get("arguments", {}))
        else:
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32601, "message": f"未知方法：{method!r}"},
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "error": {"code": -32603, "message": str(exc)},
        }
    return {"jsonrpc": "2.0", "id": rid, "result": result}


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}
