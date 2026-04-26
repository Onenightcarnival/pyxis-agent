"""pyxis：声明式思维链的 Python agent 框架。

核心哲学：`schema as workflow`。

- Pydantic 输出模型、字段说明、函数签名和函数体返回的输入文本共同构成
  代码化契约。
- Pydantic 输出模型的字段顺序就是思维链——LLM 必须自上而下把字段
  填完（schema-as-CoT）。
- 函数 docstring 只用于 Python 文档，不进入 LLM 上下文。
- 多轮编排直接写普通 Python：`if`、`for`、函数组合。

公共 API：

- `@step` / `Step` / `AsyncStep`：一次类型化的 LLM 调用。
- `Tool` / `@tool`：动作即 schema，`run()` 即代码。
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
