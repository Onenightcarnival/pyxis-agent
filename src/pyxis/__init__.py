"""pyxis：声明式思维链的 Python agent 框架。

核心哲学：`code as prompt + schema as workflow`。

- 函数的 docstring 就是 system prompt，字符串返回就是 user message
  （**code-as-prompt**）。
- Pydantic 输出模型的字段顺序就是思维链——LLM 必须自上而下把字段填完，
  schema 直接声明了推理步骤（**schema-as-CoT**）。
- 多轮编排直接写普通 Python：`if`、`for`、函数组合已经足够好，框架
  刻意不引入 DSL。
- **pyxis 不造配套生态**：provider、观测、hooks 都由现成工具承担——
  直接用 `openai.OpenAI` / `instructor.from_openai(...)` 实例；接
  Langfuse / OpenTelemetry / APM 请通过标准姿势（换 `import` / SDK
  instrumentation）。

公共 API：

- `@step` / `Step` / `AsyncStep`：一次类型化的 LLM 调用。
- `@flow` / `Flow` / `AsyncFlow`：多步 flow 的语义标记。
- `Tool` / `@tool`：动作即 schema，`run()` 即代码。
- `FakeClient` / `FakeCall`：测试用的确定性后端，零网络。
- `ask_human` / `finish` / `run_flow` / `run_aflow` / `HumanQuestion` /
  `FlowResult`：人工介入的生成器驱动。
- `mcp.*`：MCP 适配层。
"""

from .client import FakeCall, FakeClient
from .flow import AsyncFlow, Flow, flow
from .human import (
    FlowResult,
    HumanQuestion,
    ask_human,
    finish,
    run_aflow,
    run_flow,
)
from .step import AsyncStep, Step, step
from .tool import Tool, tool

__version__ = "2.0.0"

__all__ = [
    "AsyncFlow",
    "AsyncStep",
    "FakeCall",
    "FakeClient",
    "Flow",
    "FlowResult",
    "HumanQuestion",
    "Step",
    "Tool",
    "ask_human",
    "finish",
    "flow",
    "run_aflow",
    "run_flow",
    "step",
    "tool",
]
