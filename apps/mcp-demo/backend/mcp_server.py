"""mcp-demo 内置的 stdio MCP server——zero-dep，教学用。

暴露四个工具：`word_count` / `reverse` / `upper` / `now`。真场景里换成
任何真 MCP server（`uvx mcp-server-filesystem` 之类）都是一样的 stdio
协议，只要把 `StdioMCP(command=..., args=[...])` 指过去。
"""

from __future__ import annotations

import datetime as _dt
import json
import sys

TOOLS = [
    {
        "name": "word_count",
        "description": "数一段文本里的单词数（按空白切分）。",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "要统计的文本"}},
            "required": ["text"],
        },
    },
    {
        "name": "reverse",
        "description": "把字符串反转。",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "要反转的文本"}},
            "required": ["text"],
        },
    },
    {
        "name": "upper",
        "description": "把字符串转大写。",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "要转大写的文本"}},
            "required": ["text"],
        },
    },
    {
        "name": "now",
        "description": "返回 server 本地的当前 ISO 时间戳。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def handle(method: str, params: dict) -> dict:
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "capabilities": {}}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name = params["name"]
        args = params.get("arguments", {})
        if name == "word_count":
            return {"content": [{"type": "text", "text": str(len(args["text"].split()))}]}
        if name == "reverse":
            return {"content": [{"type": "text", "text": args["text"][::-1]}]}
        if name == "upper":
            return {"content": [{"type": "text", "text": args["text"].upper()}]}
        if name == "now":
            return {"content": [{"type": "text", "text": _dt.datetime.now().isoformat()}]}
        raise ValueError(f"未知工具：{name!r}")
    raise ValueError(f"未知方法：{method!r}")


def main() -> None:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        req = json.loads(raw)
        rid = req.get("id")
        try:
            result = handle(req["method"], req.get("params", {}))
            resp = {"jsonrpc": "2.0", "id": rid, "result": result}
        except Exception as exc:  # noqa: BLE001
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32603, "message": str(exc)},
            }
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
