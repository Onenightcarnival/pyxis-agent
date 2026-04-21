"""一个极简的 stdio MCP server——仅用于 demo，零外部依赖。

暴露两个工具：
- `word_count(text)`：数单词数。
- `reverse(text)`：反转字符串。

协议最低实现：`initialize` / `tools/list` / `tools/call`。拿去喂
`examples/mcp_tool_use.py` 就能跑，不需要安装任何真 MCP server。

真正接生产 MCP server 时，把 `StdioMCP(command=..., args=[...])` 指向
那个 server 的启动命令即可，本 demo server 完全可替换。
"""

from __future__ import annotations

import json
import sys

TOOLS = [
    {
        "name": "word_count",
        "description": "数一段文本里的单词数（按空白切分）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要统计的文本"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "reverse",
        "description": "把字符串反转。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要反转的文本"},
            },
            "required": ["text"],
        },
    },
]


def handle(method: str, params: dict) -> dict:
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "capabilities": {}}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name = params["name"]
        args = params["arguments"]
        if name == "word_count":
            n = len(args["text"].split())
            return {"content": [{"type": "text", "text": str(n)}]}
        if name == "reverse":
            return {"content": [{"type": "text", "text": args["text"][::-1]}]}
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
        except Exception as exc:
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32603, "message": str(exc)},
            }
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
