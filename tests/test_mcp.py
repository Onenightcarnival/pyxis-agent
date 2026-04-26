"""MCP 适配层的测试 —— 规格 013。
测试策略：
- 所有测试零网络、零外部 MCP server。
- HTTP 传输：用 `httpx.MockTransport` 模拟 JSON-RPC 服务器。
- stdio 传输：用 `sys.executable -c <inline-script>` 起一个 10 行的
  真子进程，用 JSON-RPC 通信——测试的是**真**子进程 + 真管道。
"""

from __future__ import annotations

import json
import sys
from typing import Annotated, Literal, Union

import httpx
import pytest
from pydantic import BaseModel, Field, ValidationError

from pyxis import FakeClient, Tool, step
from pyxis.mcp import (
    HttpMCP,
    MCPServer,
    StdioMCP,
    jsonschema_to_field,
    mcp_toolset,
)


# ------------------------- schema models -------------------------
def test_stdio_and_http_transports_are_discriminated_by_kind():
    s = MCPServer(name="fs", transport=StdioMCP(command="echo"))
    assert s.transport.kind == "stdio"
    h = MCPServer(name="web", transport=HttpMCP(url="http://x"))
    assert h.transport.kind == "http"
    # 判别式联合应当能从 dict 反序列化
    s2 = MCPServer.model_validate(
        {"name": "fs", "transport": {"kind": "stdio", "command": "echo", "args": ["-n"]}}
    )
    assert isinstance(s2.transport, StdioMCP)
    assert s2.transport.args == ["-n"]


def test_mcp_server_default_fields():
    s = MCPServer(name="x", transport=HttpMCP(url="http://x"))
    assert s.include is None
    assert s.exclude == []
    assert s.timeout_s == 30.0


def test_transport_without_kind_fails():
    # 判别式联合必须通过 kind 分派
    with pytest.raises(ValidationError):
        MCPServer.model_validate({"name": "x", "transport": {"command": "echo"}})


# ------------------------- JSON Schema → Pydantic field -------------------------
def test_jsonschema_translates_primitive_types():
    ty, default = jsonschema_to_field({"type": "string"}, required=True)
    assert ty is str and default is ...
    ty, default = jsonschema_to_field({"type": "integer"}, required=True)
    assert ty is int
    ty, default = jsonschema_to_field({"type": "number"}, required=True)
    assert ty is float
    ty, default = jsonschema_to_field({"type": "boolean"}, required=True)
    assert ty is bool


def test_jsonschema_translates_list_and_dict():
    ty, _ = jsonschema_to_field({"type": "array", "items": {"type": "string"}}, required=True)
    assert ty == list[str]
    ty, _ = jsonschema_to_field({"type": "object"}, required=True)
    assert ty == dict[str, object]


def test_jsonschema_optional_gets_none_default():
    ty, default = jsonschema_to_field({"type": "string"}, required=False)
    assert ty == (str | None)
    assert default is None


def test_jsonschema_unknown_type_raises():
    with pytest.raises(TypeError, match="不支持"):
        jsonschema_to_field({"type": "bytestring"}, required=True)


# ------------------------- HTTP transport（httpx.MockTransport） -------------------------
SAMPLE_TOOLS = [
    {
        "name": "echo",
        "description": "回显输入。",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "add",
        "description": "两数相加。",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    },
]


def _http_handler(tools: list[dict] | None = None):
    tools = tools if tools is not None else SAMPLE_TOOLS
    state = {"calls": []}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        state["calls"].append(body)
        rid = body.get("id")
        method = body["method"]
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {}}
        elif method == "tools/list":
            result = {"tools": tools}
        elif method == "tools/call":
            name = body["params"]["name"]
            args = body["params"]["arguments"]
            if name == "echo":
                text = args["text"]
                result = {"content": [{"type": "text", "text": f"echoed:{text}"}]}
            elif name == "add":
                result = {"content": [{"type": "text", "text": str(args["a"] + args["b"])}]}
            else:
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": rid,
                        "error": {"code": -32601, "message": f"unknown tool: {name}"},
                    },
                )
        else:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {"code": -32601, "message": f"unknown method: {method}"},
                },
            )
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": rid, "result": result})

    return handler, state


async def test_http_toolset_discovers_and_invokes_tools():
    handler, state = _http_handler()
    transport = httpx.MockTransport(handler)
    server = MCPServer(name="web", transport=HttpMCP(url="http://fake/mcp"))
    async with mcp_toolset(server, _http_transport=transport) as tools:
        assert len(tools) == 2
        names = [t.model_fields["kind"].default for t in tools]
        assert set(names) == {"echo", "add"}
        echo_cls = next(t for t in tools if t.model_fields["kind"].default == "echo")
        assert echo_cls.__name__ == "Echo"
        assert "text" in echo_cls.model_fields
        echo = echo_cls(text="你好")  # type: ignore[call-arg]
        assert echo.run() == "echoed:你好"
        add_cls = next(t for t in tools if t.model_fields["kind"].default == "add")
        add = add_cls(a=2, b=3)  # type: ignore[call-arg]
        assert add.run() == "5"
    methods = [c["method"] for c in state["calls"]]
    assert methods[:3] == ["initialize", "notifications/initialized", "tools/list"]
    assert "tools/call" in methods


async def test_http_toolset_filters_with_include_exclude():
    handler, _ = _http_handler()
    transport = httpx.MockTransport(handler)
    server = MCPServer(
        name="web",
        transport=HttpMCP(url="http://fake/mcp"),
        include=["echo", "add"],
        exclude=["add"],
    )
    async with mcp_toolset(server, _http_transport=transport) as tools:
        names = [t.model_fields["kind"].default for t in tools]
        assert names == ["echo"]


async def test_http_toolset_include_unknown_name_raises():
    handler, _ = _http_handler()
    transport = httpx.MockTransport(handler)
    server = MCPServer(
        name="web",
        transport=HttpMCP(url="http://fake/mcp"),
        include=["nonexistent"],
    )
    with pytest.raises(ValueError, match="nonexistent"):
        async with mcp_toolset(server, _http_transport=transport):
            pass


async def test_http_toolset_handles_sse_response_and_session_id():
    """FastMCP 等真实 server 默认用 text/event-stream 回响应；pyxis 必须能解析。
    同时验证 `Mcp-Session-Id` 头在 initialize 里分配、后续请求回写。
    """
    SESSION_ID = "sess-abcd"
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(
            {
                "method": body.get("method"),
                "id": body.get("id"),
                "sid": request.headers.get("mcp-session-id"),
                "accept": request.headers.get("accept"),
            }
        )
        method = body["method"]
        rid = body.get("id")
        # notification 按规范返回 202 空响应
        if rid is None:
            return httpx.Response(202)
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {}}
            sse_body = f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'id': rid, 'result': result})}\n\n"
            return httpx.Response(
                200,
                content=sse_body,
                headers={
                    "content-type": "text/event-stream",
                    "mcp-session-id": SESSION_ID,
                },
            )
        if method == "tools/list":
            # 响应前面先夹一条无关的事件（server 可能这么干），确保解析器
            # 正确跳过不匹配 id 的消息
            result = {"tools": SAMPLE_TOOLS}
            sse_body = (
                "event: message\n"
                'data: {"jsonrpc":"2.0","method":"notifications/progress","params":{}}\n'
                "\n"
                f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'id': rid, 'result': result})}\n\n"
            )
            return httpx.Response(
                200, content=sse_body, headers={"content-type": "text/event-stream"}
            )
        if method == "tools/call":
            result = {"content": [{"type": "text", "text": "sse-ok"}]}
            sse_body = f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'id': rid, 'result': result})}\n\n"
            return httpx.Response(
                200, content=sse_body, headers={"content-type": "text/event-stream"}
            )
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32601, "message": f"unknown: {method}"},
            },
        )

    transport = httpx.MockTransport(handler)
    server = MCPServer(name="web", transport=HttpMCP(url="http://fake/mcp"))
    async with mcp_toolset(server, _http_transport=transport) as tools:
        echo_cls = next(t for t in tools if t.model_fields["kind"].default == "echo")
        assert echo_cls(text="x").run() == "sse-ok"  # type: ignore[call-arg]
    # 第一条请求无 session id；initialize 之后所有请求必须带上 SESSION_ID
    assert calls[0]["method"] == "initialize"
    assert calls[0]["sid"] is None
    assert calls[0]["accept"] == "application/json, text/event-stream"
    for c in calls[1:]:
        assert c["sid"] == SESSION_ID, f"{c['method']} 没带 session id"
    # notifications/initialized 应当在 initialize 之后、tools/list 之前
    methods = [c["method"] for c in calls]
    assert methods[:3] == ["initialize", "notifications/initialized", "tools/list"]


async def test_http_toolset_duplicate_tool_names_raise():
    # MCP 协议本不允许同一 server 内重名，但万一 server 错了我们要抛
    dup = [SAMPLE_TOOLS[0], SAMPLE_TOOLS[0]]
    handler, _ = _http_handler(dup)
    transport = httpx.MockTransport(handler)
    server = MCPServer(name="web", transport=HttpMCP(url="http://fake/mcp"))
    with pytest.raises(ValueError, match=r"重名|duplicate|echo"):
        async with mcp_toolset(server, _http_transport=transport):
            pass


# ------------------------- stdio transport（真子进程） -------------------------
STDIO_SERVER_SCRIPT = r"""
import sys, json
def reply(mid, result):
    sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":mid,"result":result}) + "\n")
    sys.stdout.flush()
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    req = json.loads(line)
    mid = req.get("id")
    m = req["method"]
    if m == "initialize":
        reply(mid, {"protocolVersion": "2024-11-05", "capabilities": {}})
    elif m == "tools/list":
        reply(mid, {"tools": [{
            "name": "echo", "description": "echo",
            "inputSchema": {"type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"]}
        }]})
    elif m == "tools/call":
        t = req["params"]["arguments"]["text"]
        reply(mid, {"content": [{"type": "text", "text": "stdio:" + t}]})
"""


async def test_stdio_toolset_discovers_and_invokes_tools():
    server = MCPServer(
        name="local",
        transport=StdioMCP(command=sys.executable, args=["-c", STDIO_SERVER_SCRIPT]),
    )
    async with mcp_toolset(server) as tools:
        assert len(tools) == 1
        echo_cls = tools[0]
        assert echo_cls.model_fields["kind"].default == "echo"
        obs = echo_cls(text="你好").run()  # type: ignore[call-arg]
        assert obs == "stdio:你好"


# ------------------------- 混合注册：native + MCP 共进一个判别式联合 -------------------------
class Finish(Tool):
    kind: Literal["finish"] = "finish"
    answer: str

    def run(self) -> str:
        return self.answer


async def test_mcp_tools_mix_with_native_tools_in_union():
    handler, _ = _http_handler()
    transport = httpx.MockTransport(handler)
    server = MCPServer(
        name="web",
        transport=HttpMCP(url="http://fake/mcp"),
        include=["echo"],
    )
    async with mcp_toolset(server, _http_transport=transport) as mcp_tools:
        Action = Annotated[Union[tuple([*mcp_tools, Finish])], Field(discriminator="kind")]  # type: ignore  # noqa: UP007

        class Decision(BaseModel):
            thought: str
            action: Action  # type: ignore

        echo_cls = mcp_tools[0]
        fake = FakeClient(
            [
                Decision(thought="先 echo 一下", action=echo_cls(text="喵")),  # type: ignore[call-arg]
                Decision(thought="结束", action=Finish(answer="done")),
            ]
        )

        @step(output=Decision, client=fake)
        def decide(q: str) -> str:
            """选一个动作。"""
            return q

        d1 = decide("go")
        assert d1.action.run() == "echoed:喵"
        d2 = decide("go")
        assert isinstance(d2.action, Finish)
