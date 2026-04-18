"""chat-demo 的 FastAPI 后端：POST /chat 返回 SSE 流，逐帧推 partial Pydantic。

设计要点：
- 一个 @step 负责每一轮 LLM 调用，输出 `ChatReply(thought, response)`。
- 历史由前端维护并随请求一起发来；后端不存 session。
- SSE 每一帧是一个 JSON dict：{"kind": "partial", ...} 逐字段填满，
  最后一帧 {"kind": "done", "final": {...}} 携带完整实例。

前端拿到这些帧后怎么渲染，是前端自由——这正是 pyxis 的哲学。
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pyxis import set_default_client, step
from pyxis.providers import openrouter_client

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-5.4-nano")


class ChatReply(BaseModel):
    """Schema-as-CoT：先思考再回复，字段顺序就是推理顺序。"""

    thought: str = Field(description="你对用户问题的内部思考；用户看不见")
    response: str = Field(description="给用户看的最终回复，自然语言")


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Turn] = Field(default_factory=list)


def _format_history(history: list[Turn]) -> str:
    """历史拉成字符串塞进 user content；保持 pyxis 当前 API（@step 接 str）。"""
    if not history:
        return ""
    lines = ["以下是本次对话的历史："]
    for t in history:
        role_zh = "用户" if t.role == "user" else "助手"
        lines.append(f"[{role_zh}] {t.content}")
    lines.append("")
    return "\n".join(lines)


@step(output=ChatReply, model=MODEL)
def respond(history_text: str, user_message: str) -> str:
    """你是一个友好、严谨的中文对话助手。先在 `thought` 里梳理思路
    （不会展示给用户），再在 `response` 里给出最终回复。"""
    return f"{history_text}\n本轮用户输入：\n{user_message}".strip()


app = FastAPI(title="pyxis chat-demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _configure() -> None:
    if "OPENROUTER_API_KEY" in os.environ:
        set_default_client(openrouter_client())


def _sse(data: dict) -> bytes:
    """组一行 SSE：`data: {...}\\n\\n`。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


async def _stream_reply(req: ChatRequest) -> AsyncIterator[bytes]:
    history_text = _format_history(req.history)
    last: ChatReply | None = None

    # pyxis 的 stream()：每一帧是 partial ChatReply（字段可能为空串/None）。
    # 我们把它序列化后推到前端，前端再按 view 选择怎么渲染。
    try:
        for partial in respond.stream(history_text, req.message):
            last = partial  # type: ignore[assignment]
            yield _sse(
                {
                    "kind": "partial",
                    "thought": getattr(partial, "thought", None),
                    "response": getattr(partial, "response", None),
                }
            )
            # 让出一下事件循环，前端 SSE 能流畅接收
            await asyncio.sleep(0)
    except Exception as exc:  # noqa: BLE001
        yield _sse({"kind": "error", "message": f"{type(exc).__name__}: {exc}"})
        return

    if last is not None:
        yield _sse({"kind": "done", "final": last.model_dump()})


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(_stream_reply(req), media_type="text/event-stream")


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "model": MODEL, "has_key": "OPENROUTER_API_KEY" in os.environ}
