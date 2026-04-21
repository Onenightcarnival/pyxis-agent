"""MCP（Model Context Protocol）适配层：把一个 MCP server 变成一批 Tool 子类。

职责范围（见 [specs/013-mcp.md](../../specs/013-mcp.md)）：

- `MCPServer` / `StdioMCP` / `HttpMCP`：声明式连接配置（Pydantic 数据）。
- `mcp_toolset(server)`：异步上下文管理器；入口建立连接、发 `tools/list`、
  把每个远端工具翻成一个 pyxis `Tool` 子类（`run()` 同步调 `tools/call`）。
- 传输复杂度全部吸收在本模块：HTTP 用 `httpx.Client`（无状态请求/响应）；
  stdio 用持久子进程 + `id → response` 关联 + 锁。
- **`Tool.run()` 契约保持同步**——调用方（agent loop）完全不知道工具从哪来。

故意不做：arun / SSE / resources / prompts / sampling / 全局 registry /
自动断线重连 / 并发调用 / tool schema 动态刷新 / 跨 server 自动去重。
"""

from __future__ import annotations

import itertools
import json
import subprocess
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

import httpx
from pydantic import BaseModel, Field, create_model

from .tool import Tool


class StdioMCP(BaseModel):
    """以子进程方式启动的 MCP server（本地场景最常见）。"""

    kind: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class HttpMCP(BaseModel):
    """Streamable HTTP 传输的 MCP server。"""

    kind: Literal["http"] = "http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)


Transport = Annotated[StdioMCP | HttpMCP, Field(discriminator="kind")]


class MCPServer(BaseModel):
    """一个 MCP server 的声明式描述——数据，不是行为。

    `include` / `exclude` 用**精确名**筛选工具；`include` 指定的名字必须
    真的出现在 server 的 `tools/list` 返回里，否则抛 `ValueError`。
    """

    name: str
    transport: Transport
    include: list[str] | None = None
    exclude: list[str] = Field(default_factory=list)
    timeout_s: float = 30.0


# ============================ JSON Schema → Pydantic ============================

_PRIMITIVE: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def jsonschema_to_field(spec: dict[str, Any], *, required: bool) -> tuple[Any, Any]:
    """把单个 JSON Schema 属性翻成 `(python_type, default)`。

    支持：`string / integer / number / boolean / array / object`。`array` 的 `items`
    递归翻译；`object` 不展开（用 `dict[str, object]`）。可选字段（`required` 为假）
    的类型加 `| None`，默认值为 `None`；必选默认 `...`（Pydantic 的"必填"哨兵）。
    遇到未支持的 type 抛 `TypeError`，点明 type 值——不兜底、不猜。
    """
    ty = _jsonschema_type(spec)
    default = ... if required else None
    if not required:
        ty = ty | None
    return ty, default


def _jsonschema_type(spec: dict[str, Any]) -> Any:
    t = spec.get("type")
    if t in _PRIMITIVE:
        return _PRIMITIVE[t]
    if t == "array":
        items = spec.get("items", {"type": "string"})
        return list[_jsonschema_type(items)]  # type: ignore[misc]
    if t == "object":
        return dict[str, object]
    raise TypeError(f"JSON Schema type 不支持：{t!r}（spec={spec!r}）")


# ============================ 传输连接（sync I/O） ============================


class _JsonRpcError(RuntimeError):
    """把 JSON-RPC error 字段包进 Python 异常。"""


class _HttpConn:
    """无状态 HTTP JSON-RPC：每次 `request()` 一次 POST。"""

    def __init__(self, mcp: HttpMCP, *, timeout_s: float, http_transport: Any = None):
        kwargs: dict[str, Any] = {
            "headers": mcp.headers,
            "timeout": timeout_s,
        }
        if http_transport is not None:
            kwargs["transport"] = http_transport
        self._client = httpx.Client(**kwargs)
        self._url = mcp.url
        self._ids = itertools.count(1)

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        rid = next(self._ids)
        payload = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            payload["params"] = params
        resp = self._client.post(self._url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise _JsonRpcError(f"{method} 失败：{data['error']}")
        return data["result"]

    def close(self) -> None:
        self._client.close()


class _StdioConn:
    """持久子进程 + stdin/stdout 上的 JSON-RPC 管道。

    写锁串行化请求；`id → response` 字典用于关联（理论上只串行，但万一
    server 乱序返回也能自洽）。stderr 透传到父进程 stderr，方便调试。
    """

    def __init__(self, mcp: StdioMCP, *, timeout_s: float):
        self._proc = subprocess.Popen(
            [mcp.command, *mcp.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            bufsize=1,
            env={**mcp.env} if mcp.env else None,
        )
        self._lock = threading.Lock()
        self._ids = itertools.count(1)
        self._timeout_s = timeout_s

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("MCP stdio 子进程 stdin/stdout 不可用")
        rid = next(self._ids)
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            payload["params"] = params
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with self._lock:
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
            # MCP server 可能夹杂 notification（无 id），按 id 对齐直到找到
            while True:
                raw = self._proc.stdout.readline()
                if not raw:
                    raise RuntimeError("MCP stdio 子进程过早关闭 stdout（可能已退出）")
                msg = json.loads(raw)
                if msg.get("id") != rid:
                    continue
                if "error" in msg:
                    raise _JsonRpcError(f"{method} 失败：{msg['error']}")
                return msg.get("result")

    def close(self) -> None:
        if self._proc.poll() is None:
            try:
                if self._proc.stdin is not None:
                    self._proc.stdin.close()
            except OSError:
                pass
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.terminate()
                self._proc.wait(timeout=5)


_Conn = _HttpConn | _StdioConn


def _open_conn(transport: Transport, *, timeout_s: float, http_transport: Any = None) -> _Conn:
    if isinstance(transport, HttpMCP):
        return _HttpConn(transport, timeout_s=timeout_s, http_transport=http_transport)
    return _StdioConn(transport, timeout_s=timeout_s)


# ============================ Tool 子类生成 ============================


def _snake_to_pascal(name: str) -> str:
    # 与 tool.py 保持同样的命名规则
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


def _mcp_tool_to_pyxis(
    tool_spec: dict[str, Any],
    *,
    call_tool: Callable[[str, dict[str, Any]], str],
) -> type[Tool]:
    """把一个 MCP `tools/list` 条目翻成一个 `Tool` 子类。"""
    name = tool_spec["name"]
    schema = tool_spec.get("inputSchema") or {}
    props: dict[str, Any] = schema.get("properties") or {}
    required: set[str] = set(schema.get("required") or [])

    fields: dict[str, Any] = {}
    for prop_name, prop_spec in props.items():
        ty, default = jsonschema_to_field(prop_spec, required=prop_name in required)
        description = prop_spec.get("description", "")
        fields[prop_name] = (ty, Field(default, description=description))

    fields["kind"] = (Literal[name], name)  # type: ignore[valid-type]

    def run(self: Tool) -> str:
        arguments = self.model_dump(exclude={"kind"})
        return call_tool(name, arguments)

    cls = create_model(_snake_to_pascal(name), __base__=Tool, **fields)
    cls.run = run  # type: ignore[method-assign]
    cls.__doc__ = tool_spec.get("description") or ""
    return cls


def _call_tool_result_to_str(result: Any) -> str:
    """MCP `tools/call` 的响应 → str。只取 `type == "text"` 的片段，按换行拼接。"""
    content = (result or {}).get("content") or []
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    return "\n".join(texts)


# ============================ 对外入口：mcp_toolset ============================


@asynccontextmanager
async def mcp_toolset(
    server: MCPServer,
    *,
    _http_transport: Any = None,
) -> AsyncIterator[list[type[Tool]]]:
    """连上 MCP server，发现它的工具，翻成 `list[type[Tool]]` 交给调用者。

    `_http_transport` 仅为测试注入 `httpx.MockTransport` 预留；生产代码不要用。

    生命周期：进入时建立连接 + `initialize` + `tools/list` + 翻译；退出时
    关闭连接（HTTP `Client.close()`，stdio 子进程 `terminate + wait`）。
    `tools/list` **只调用一次**——schema 的动态刷新刻意不做。
    """
    conn = _open_conn(server.transport, timeout_s=server.timeout_s, http_transport=_http_transport)
    try:
        conn.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pyxis-agent", "version": "1.1.0"},
            },
        )
        listing = conn.request("tools/list")
        tool_specs: list[dict[str, Any]] = listing.get("tools", [])

        tool_specs = _filter_tools(tool_specs, server.include, server.exclude)
        _check_no_duplicates(tool_specs)

        def call_tool(name: str, arguments: dict[str, Any]) -> str:
            result = conn.request("tools/call", {"name": name, "arguments": arguments})
            return _call_tool_result_to_str(result)

        classes = [_mcp_tool_to_pyxis(spec, call_tool=call_tool) for spec in tool_specs]
        yield classes
    finally:
        conn.close()


def _filter_tools(
    tools: list[dict[str, Any]],
    include: list[str] | None,
    exclude: list[str],
) -> list[dict[str, Any]]:
    """精确名筛：先 include（白名单收敛），再 exclude（剔除）。"""
    available = {t["name"] for t in tools}
    if include is not None:
        missing = [n for n in include if n not in available]
        if missing:
            raise ValueError(
                f"include 里的工具名在 server 里不存在：{missing}；"
                f"server 实际暴露的是：{sorted(available)}"
            )
        tools = [t for t in tools if t["name"] in include]
    if exclude:
        tools = [t for t in tools if t["name"] not in exclude]
    return tools


def _check_no_duplicates(tools: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for t in tools:
        n = t["name"]
        if n in seen:
            raise ValueError(
                f"MCP server 返回的 tools/list 里有重名：{n!r}；协议不允许，请检查 server 实现。"
            )
        seen.add(n)


__all__ = [
    "HttpMCP",
    "MCPServer",
    "StdioMCP",
    "jsonschema_to_field",
    "mcp_toolset",
]
