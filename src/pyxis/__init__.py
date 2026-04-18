"""pyxis：声明式思维链的 Python agent 框架。

核心哲学：`code as prompt + schema as workflow`。

- 函数的 docstring 就是 system prompt，字符串返回就是 user message
  （**code-as-prompt**）。
- Pydantic 输出模型的字段顺序就是思维链——LLM 必须自上而下把字段填完，
  schema 直接声明了推理步骤（**schema-as-CoT**）。
- 多轮编排直接写普通 Python：`if`、`for`、函数组合已经足够好，框架
  刻意不引入 DSL。

公共 API 分四类：
- `@step` / `Step` / `AsyncStep`：一次 LLM 调用，按 Pydantic 字段顺序
  进行结构化推理。
- `@flow` / `Flow` / `AsyncFlow`：多次调用的编排，`.run_traced()` 一键
  观测。
- `Tool`：动作即 schema，`run()` 即代码；搭配判别式联合完成工具调用。
- `trace()` / `Trace` / `TraceRecord` / `Usage` / `CompletionResult`：
  结构化的可观测性，支持 JSON 导出与 token 成本汇总。

生产用 `InstructorClient`（instructor 背后的 OpenAI 兼容接口），测试
用 `FakeClient`（按队列返回预置响应，零网络）。
"""

from .client import (
    AsyncClient,
    Client,
    CompletionResult,
    FakeCall,
    FakeClient,
    InstructorClient,
    Usage,
    get_default_client,
    set_default_client,
)
from .flow import AsyncFlow, Flow, flow
from .hooks import StepHook, add_hook, clear_hooks, remove_hook
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
from .trace import Trace, TraceRecord, trace

__version__ = "1.0.0"

__all__ = [
    "AsyncClient",
    "AsyncFlow",
    "AsyncStep",
    "Client",
    "CompletionResult",
    "FakeCall",
    "FakeClient",
    "Flow",
    "FlowResult",
    "HumanQuestion",
    "InstructorClient",
    "Step",
    "StepHook",
    "Tool",
    "Trace",
    "TraceRecord",
    "Usage",
    "add_hook",
    "ask_human",
    "clear_hooks",
    "finish",
    "flow",
    "get_default_client",
    "remove_hook",
    "run_aflow",
    "run_flow",
    "set_default_client",
    "step",
    "tool",
    "trace",
]
