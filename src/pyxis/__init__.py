"""pyxis：把 LLM 调用写成 Python 函数，返回 Pydantic 实例。

- Pydantic 输出模型、字段说明、函数签名和函数体返回的输入文本共同构成
  一次调用。
- Pydantic 输出模型的字段顺序，就是模型生成字段的顺序。
- 函数 docstring 只用于 Python 文档，不进入 LLM 上下文。
- 多轮编排直接写普通 Python：`if`、`for`、函数组合。

公共 API：

- `@step` / `Step` / `AsyncStep`：一次类型化的 LLM 调用。
- `Tool` / `@tool`：用 Pydantic 描述参数，用 `run()` 执行动作。
- `FakeClient` / `FakeCall`：测试用的确定性后端，零网络。
- `ask_interrupt` / `finish` / `run_flow` / `run_aflow` / `InterruptRequest` /
  `FlowResult`：外部输入点的生成器驱动。
- `mcp.*`：MCP 适配层。
"""

from .client import FakeCall, FakeClient
from .interrupt import (
    FlowResult,
    InterruptRequest,
    ask_interrupt,
    finish,
    run_aflow,
    run_flow,
)
from .step import AsyncStep, Step, step
from .tool import Tool, tool

__version__ = "2.0.0"

__all__ = [
    "AsyncStep",
    "FakeCall",
    "FakeClient",
    "FlowResult",
    "InterruptRequest",
    "Step",
    "Tool",
    "ask_interrupt",
    "finish",
    "run_aflow",
    "run_flow",
    "step",
    "tool",
]
