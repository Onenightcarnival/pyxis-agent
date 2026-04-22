"""mcp-demo 的 FastAPI 后端：一次 POST /run 流式吐出 agent 的每一步。

设计要点：
- 后端在启动时**同时**连两个 MCP server：
  - `mcp:stdio-demo`——本地子进程（`mcp_server.py`）走 stdio JSON-RPC。
  - `mcp:http-demo`——本地 uvicorn 子进程（`mcp_http_server.py`）走
    Streamable HTTP JSON-RPC。
  两条传输在 pyxis `Tool.run()` 层面完全对称，agent loop 对此无感。
- 和 native 工具（`Calculate` / `Finish`）拼成一个判别式联合跑 agent loop。
- 每一步 SSE 帧携带**工具来源标签**（`native` / `mcp:<server-name>`），
  前端据此上色，可视化"多源工具 + 统一调用面"这件事。
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import reduce
from operator import or_
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from pyxis import Tool, step
from pyxis.mcp import HttpMCP, MCPServer, StdioMCP, mcp_toolset

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-5.4-nano")
MCP_STDIO_SCRIPT = Path(__file__).parent / "mcp_server.py"
HTTP_MCP_PORT = int(os.environ.get("MCP_HTTP_PORT", "3003"))
HTTP_MCP_URL = f"http://127.0.0.1:{HTTP_MCP_PORT}/mcp"

openrouter = AsyncOpenAI(
    base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


# ---- native 工具 ----


class Calculate(Tool):
    """计算一个简单的算术表达式，返回数值结果。"""

    kind: Literal["calculate"] = "calculate"
    expression: str = Field(description="一个 Python 数学表达式，例如 '2*(3+4)'")

    def run(self) -> str:
        return str(eval(self.expression, {"__builtins__": {}}, {}))


class Finish(Tool):
    """停止并给出最终答案。"""

    kind: Literal["finish"] = "finish"
    answer: str = Field(description="给用户的最终答案")

    def run(self) -> str:
        return self.answer


NATIVE_TOOLS: list[type[Tool]] = [Calculate, Finish]
NATIVE_NAMES = {t.model_fields["kind"].default for t in NATIVE_TOOLS}


# ---- 请求 / SSE 帧的形状（前端共用） ----


class RunRequest(BaseModel):
    question: str
    max_steps: int = 6


# ---- 应用状态：启动时连 MCP，关闭时释放 ----


async def _wait_for_port(host: str, port: int, timeout_s: float = 10.0) -> None:
    """等 TCP 端口可以 connect——不发 HTTP 请求，避开各 MCP server 的协议
    前置要求（比如 FastMCP 强制要求 Accept: text/event-stream，否则 406）。"""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError:
            await asyncio.sleep(0.15)
    raise RuntimeError(f"HTTP MCP server 在 {timeout_s}s 内未监听 {host}:{port}")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动独立进程：`python mcp_http_server.py` → FastMCP 自己管 uvicorn，
    # 端口通过 MCP_HTTP_PORT 环境变量传递（与 mcp_http_server.py 里读法一致）。
    http_proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / "mcp_http_server.py")],
        env={**os.environ, "MCP_HTTP_PORT": str(HTTP_MCP_PORT)},
    )
    try:
        await _wait_for_port("127.0.0.1", HTTP_MCP_PORT)

        stdio_server = MCPServer(
            name="stdio-demo",
            transport=StdioMCP(command=sys.executable, args=[str(MCP_STDIO_SCRIPT)]),
        )
        http_server = MCPServer(
            name="http-demo",
            transport=HttpMCP(url=HTTP_MCP_URL),
        )
        async with (
            mcp_toolset(stdio_server) as stdio_tools,
            mcp_toolset(http_server) as http_tools,
        ):
            # 保留来源信息：前端 / agent loop 都要靠它区分 native vs mcp:<name>
            app.state.mcp_sources = [
                (stdio_server.name, stdio_tools),
                (http_server.name, http_tools),
            ]
            app.state.mcp_names_by_source = {
                name: {t.model_fields["kind"].default for t in tools}
                for name, tools in app.state.mcp_sources
            }
            yield
    finally:
        http_proc.terminate()
        try:
            http_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            http_proc.kill()


app = FastAPI(title="pyxis mcp-demo", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(data: dict) -> bytes:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


def _describe(tool_cls: type[Tool], *, source: str) -> dict:
    """把一个 Tool 子类描述成前端能直接渲染的 card 数据。"""
    fields = []
    for name, info in tool_cls.model_fields.items():
        if name == "kind":
            continue
        fields.append(
            {
                "name": name,
                "type": _type_label(info.annotation),
                "description": info.description or "",
                "required": info.is_required(),
            }
        )
    return {
        "name": tool_cls.model_fields["kind"].default,
        "source": source,
        "description": (tool_cls.__doc__ or "").strip(),
        "fields": fields,
    }


def _type_label(annotation: Any) -> str:
    return getattr(annotation, "__name__", None) or str(annotation)


def _source_of(action_kind: str, mcp_names_by_source: dict[str, set[str]]) -> str:
    if action_kind in NATIVE_NAMES:
        return "native"
    for name, names in mcp_names_by_source.items():
        if action_kind in names:
            return f"mcp:{name}"
    return "unknown"


def _build_inventory(
    mcp_sources: list[tuple[str, list[type[Tool]]]],
) -> list[dict]:
    """native + 所有 MCP 来源的工具描述 flatten 成一个列表。"""
    inv = [_describe(t, source="native") for t in NATIVE_TOOLS]
    for name, tools in mcp_sources:
        inv.extend(_describe(t, source=f"mcp:{name}") for t in tools)
    return inv


async def _stream_run(req: RunRequest) -> AsyncIterator[bytes]:
    mcp_sources: list[tuple[str, list[type[Tool]]]] = app.state.mcp_sources
    mcp_names_by_source: dict[str, set[str]] = app.state.mcp_names_by_source

    # 1) inventory 帧：把所有工具（native + 每个 MCP source）打包推给前端
    yield _sse({"kind": "inventory", "tools": _build_inventory(mcp_sources)})

    # 2) 拼判别式联合：native + 所有 MCP 来源的工具全部 flatten
    tool_classes: list[type[Tool]] = [*NATIVE_TOOLS]
    for _, tools in mcp_sources:
        tool_classes.extend(tools)
    Action = Annotated[reduce(or_, tool_classes), Field(discriminator="kind")]

    class Decision(BaseModel):
        thought: str = Field(description="先推理接下来要做什么")
        action: Action = Field(description="这一步要调用的工具")  # type: ignore[valid-type]

    @step(output=Decision, model=MODEL, max_retries=2, client=openrouter)
    async def decide(question: str, scratch: str) -> str:
        """你是一个会推理的中文 agent。**严格**按下列规则产出 Decision：

        1. **先读"草稿板"**。草稿板里已经调用过的工具和它们的结果是**事实**，
           不要重复调用相同参数——要基于它推进下一步。
        2. `thought`：写你**基于草稿板**的新推理。不要复述任务。
        3. `action`：**叶子工具**调用，例如 `{"kind":"reverse","text":"..."}`；
           绝不嵌套 Decision。
        4. **何时调 finish**：当且仅当草稿板上已经**有足够的观测结果**让你
           能写出具体答案时。`finish.answer` **必须非空**，且要明确引用草稿板
           上的观测值（例如"反转后='xxx'，单词数=3"）。
        5. 如果草稿板为空或还没跑过需要的工具，**不要**调 finish——先跑工具。"""
        return f"问题：{question}\n\n草稿板：\n{scratch or '（空）'}"

    scratch: list[str] = []
    try:
        for i in range(req.max_steps):
            d = await decide(req.question, "\n".join(scratch))
            action_kind = d.action.kind
            # 同步调用 run()——tools 的 I/O 策略（HTTP / 子进程）被 adapter 吸收；
            # 这里加 run_in_executor 是防止 MCP 调用时阻塞 event loop。
            obs = await asyncio.get_running_loop().run_in_executor(None, d.action.run)
            source = _source_of(action_kind, mcp_names_by_source)
            yield _sse(
                {
                    "kind": "step",
                    "index": i,
                    "thought": d.thought,
                    "action": {
                        "name": action_kind,
                        "args": d.action.model_dump(exclude={"kind"}),
                        "source": source,
                    },
                    "observation": obs,
                }
            )
            scratch.append(f"thought: {d.thought}")
            scratch.append(f"{action_kind}({d.action.model_dump_json()}) -> {obs}")
            await asyncio.sleep(0)
            if isinstance(d.action, Finish):
                yield _sse({"kind": "done", "answer": obs})
                return
        yield _sse({"kind": "error", "message": f"达到 max_steps={req.max_steps} 仍未结束"})
    except Exception as exc:  # noqa: BLE001
        yield _sse({"kind": "error", "message": f"{type(exc).__name__}: {exc}"})


@app.post("/run")
async def run(req: RunRequest) -> StreamingResponse:
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(_stream_run(req), media_type="text/event-stream", headers=headers)


@app.get("/inventory")
async def inventory() -> dict:
    """静态拉一次工具清单——前端可以在空闲时就渲染它。"""
    return {"tools": _build_inventory(app.state.mcp_sources)}


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "model": MODEL, "has_key": "OPENROUTER_API_KEY" in os.environ}
