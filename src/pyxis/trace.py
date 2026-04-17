"""trace 原语：在作用域内捕获 Step 调用。

一个 `Trace` 就是 `TraceRecord` 的集合。当前活跃的 trace 通过 `ContextVar`
传播，因此在继承了 context 的 asyncio task 和普通线程里都能正常工作。
trace 可以整体 `to_dict()` / `to_json()` 导出，方便写日志。
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from .client import Message, Usage


@dataclass
class TraceRecord:
    """被捕获的一次 Step 调用。"""

    step: str
    messages: list[Message]
    output: BaseModel
    model: str
    usage: Usage | None = None

    def to_dict(self) -> dict[str, Any]:
        """把这条记录转成纯 dict，便于 JSON 序列化。"""
        return {
            "step": self.step,
            "messages": list(self.messages),
            "output": self.output.model_dump(mode="json"),
            "model": self.model,
            "usage": (
                None
                if self.usage is None
                else {
                    "prompt_tokens": self.usage.prompt_tokens,
                    "completion_tokens": self.usage.completion_tokens,
                    "total_tokens": self.usage.total_tokens,
                }
            ),
        }


@dataclass
class Trace:
    """`trace()` 作用域内一次运行捕获到的有序记录。"""

    records: list[TraceRecord] = field(default_factory=list)

    def __iter__(self) -> Iterator[TraceRecord]:
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)

    def total_usage(self) -> Usage:
        """把所有非 None 的 usage 累加起来；一条都没有则返回零 Usage。"""
        total = Usage()
        for rec in self.records:
            if rec.usage is not None:
                total = total + rec.usage
        return total

    def to_dict(self) -> dict[str, Any]:
        """整个 trace 转成 dict，形如 `{"records": [...]}`。"""
        return {"records": [rec.to_dict() for rec in self.records]}

    def to_json(self, **json_kwargs: Any) -> str:
        """转成 JSON 字符串，`**json_kwargs` 透传给 `json.dumps`。"""
        return json.dumps(self.to_dict(), **json_kwargs)


_current: ContextVar[Trace | None] = ContextVar("pyxis_trace", default=None)


@contextmanager
def trace() -> Iterator[Trace]:
    """打开一个新的 trace 作用域，捕获其中的所有 Step 调用。

    作用域可以嵌套：内层捕获内层自己的记录，外层在内层期间不重复捕获。
    """
    t = Trace()
    token = _current.set(t)
    try:
        yield t
    finally:
        _current.reset(token)


def record(entry: TraceRecord) -> None:
    """把一条记录压入当前的 trace；当前没有 trace 时为空操作。"""
    current = _current.get()
    if current is not None:
        current.records.append(entry)
