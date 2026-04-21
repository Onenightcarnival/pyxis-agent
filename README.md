# pyxis-agent

**声明式思维链的 Python agent 框架 —— agent-for-machine 阵营。**

> **`声明式思维链 = code as prompt + schema as workflow`**

## 定位一句话

**pyxis 把 LLM 当"带自然语言理解能力的结构化数据生成器"，不是"对话伙伴"。**
LLM 的直接输出喂给下一段 Python 代码消费；给人看的东西是应用层用 schema
字段拼出来的（CLI / Web UI / Slack 各自渲染，schema 一份）。

| | Claude Desktop 风 | pyxis |
|---|---|---|
| LLM 直出 | 给人看的自然语言 | 给机器解析的 Pydantic |
| 对话丝滑度 | 高 | 低（先填 schema） |
| 可测、可审计、可回放 | 低 | 高 |

要和 Claude Desktop / ChatGPT 比聊天丝滑度，pyxis 会输。它的战场在别处：
**把 LLM 嵌进 pipeline、业务 agent、多 agent 机器对机器协作**——那些需要
每一轮 LLM 输出都**能被代码消费、能写断言、能回归测试**的场景。

## 为什么不是另一个 LangChain

市面上的 agent 框架，要么给你一个节点图 DSL（"LLM 版 Airflow"），要么
把推理藏进不透明的 `chain.run()` 里。pyxis 换一条路：

- Python 函数的 **docstring** 就是 system prompt。
- 函数的**字符串返回**就是 user message。
- Pydantic 输出 schema 的**字段顺序**就是思维链——LLM 必须自上而下把它们
  填完，于是 schema 直接声明了推理步骤。
- 多轮编排就写**普通 Python**。没有 DSL。`if`、`for`、函数组合已经是
  最好的编排语言。

## 两层编排

| 范围                | 机制                                    |
|---------------------|-----------------------------------------|
| 隐式（单次 LLM 调用）| `instructor` + 输出 schema 的字段顺序   |
| 显式（多次 LLM 调用）| 普通 Python                             |

## 盒子里有什么

| 原语                 | 做什么                                                                |
|----------------------|-----------------------------------------------------------------------|
| `@step(output=M)`    | 把 prompt 函数变成类型化的 LLM 调用。同步或 `async def` 都行。         |
| `@flow`              | 多步函数的薄包装，附带 `.run_traced()` 一键观测。                     |
| `Tool`               | `BaseModel` + `run()`。动作即 schema，`run()` 即代码。                |
| `@tool`              | 把普通函数直接变成 Tool 子类；不用手写样板。                          |
| `pyxis.mcp`          | MCP server → `list[type[Tool]]` 适配层；stdio / Streamable HTTP 都能混进判别式联合。 |
| `trace()`            | 基于 `ContextVar` 的抓取器，穿透 `asyncio.gather`。                   |
| `Trace.to_json()`    | 结构化导出 + `total_usage()` 汇总。                                   |
| `FakeClient`         | 给测试用的预置响应 + call 日志（零网络）。                            |
| `InstructorClient`   | 生产用 client；OpenAI 兼容；异步与同步双路。                          |

## 安装

```bash
uv add pyxis-agent
```

## 上手

```python
from pydantic import BaseModel, Field
from pyxis import flow, step, trace

class Analysis(BaseModel):
    observation: str = Field(description="你注意到什么")
    reasoning: str = Field(description="为什么这重要")
    conclusion: str = Field(description="一句话结论")

class Plan(BaseModel):
    goal: str
    steps: list[str]
    next_action: str

@step(output=Analysis)
def analyze(topic: str) -> str:
    """你是严谨的分析师。观察，推理，再下结论。"""
    return f"主题：{topic}"

@step(output=Plan, max_retries=2)
def plan_from(a: Analysis) -> str:
    """你把分析转成计划。"""
    return a.model_dump_json()

@flow
def research(topic: str) -> Plan:
    return plan_from(analyze(topic))

result, t = research.run_traced("声明式思维链的 agent 框架")
print(t.total_usage())          # Usage(prompt_tokens=..., ...)
print(t.to_json(indent=2))      # 结构化日志
```

## 用工具的 Agent（ReAct 风格，纯 Python 循环）

```python
from typing import Annotated
from pydantic import BaseModel, Field
from pyxis import flow, step, tool

@tool
def calculate(expression: str) -> str:
    """算一个数学表达式。"""
    return str(eval(expression, {"__builtins__": {}}, {}))

@tool
def finish(answer: str) -> str:
    """停止并报出答案。"""
    return answer

Action = Annotated[calculate | finish, Field(discriminator="kind")]

class Decision(BaseModel):
    thought: str
    action: Action

@step(output=Decision)
def decide(q: str, scratch: str) -> str:
    """先思考，再恰好发出一次工具调用。"""
    return f"Q: {q}\n{scratch}"

@flow
def agent(q: str, max_steps: int = 6) -> str:
    scratch: list[str] = []
    for _ in range(max_steps):
        d = decide(q, "\n".join(scratch))
        scratch += [f"thought: {d.thought}", f"obs: {d.action.run()}"]
        if isinstance(d.action, finish):
            return d.action.run()
    raise RuntimeError("达到最大步数仍未结束")
```

## 异步

```python
import asyncio
from pyxis import flow, step

@step(output=Analysis)
async def analyze(topic: str) -> str:
    """..."""
    return topic

@flow
async def research(topics: list[str]) -> list[Analysis]:
    return await asyncio.gather(*(analyze(t) for t in topics))

asyncio.run(research(["x", "y", "z"]))
```

## 人在中间（Human-in-the-loop）

把 `@flow` 写成**生成器**，中间 `yield ask_human(...)` 挂起；`run_flow`
驱动生成器、把人类答案 `.send()` 回去。没有 checkpoint、没有状态快照——
生成器本身就是活的状态。

```python
from pydantic import BaseModel
from pyxis import ask_human, flow, run_flow, step

class Decision(BaseModel):
    approve: bool
    comments: str | None = None

@flow
def plan_with_review(q: str):
    plan = make_plan(q)
    d: Decision = yield ask_human("审核计划？", schema=Decision, plan=plan.model_dump())
    if not d.approve:
        return {"status": "rejected", "comments": d.comments}
    return {"status": "done", "plan": plan}

result = run_flow(
    plan_with_review("做一个博客"),
    on_ask=lambda q: Decision(approve=input("y/N: ").lower() == "y"),
)
```

完整跑起来的示例见 [examples/human_review.py](examples/human_review.py)。
多轮对话同一个模板：把 `yield ask_human` 放进 `while True` 就是 chat session。

## MCP（Model Context Protocol）

把任意 MCP server 的工具和 native `Tool` 混进**同一个判别式联合**，
agent loop 对来源无感。`Tool.run()` 契约不扩——传输复杂度（HTTP `httpx`
调用、stdio 持久子进程 + id 关联）都吸收在 adapter 里。

```python
from pyxis.mcp import MCPServer, StdioMCP, mcp_toolset

fs = MCPServer(name="fs", transport=StdioMCP(
    command="uvx", args=["mcp-server-filesystem", "/tmp"]))

@flow
async def agent(q: str) -> str:
    async with mcp_toolset(fs) as mcp_tools:
        tool_classes = [Calculate, Finish, *mcp_tools]   # ← 拼 list 就是注册
        # ... 组判别式联合、跑 agent loop、`d.action.run()` 照常
```

Streamable HTTP 传输同样：换成 `HttpMCP(url="https://...", headers={...})`。
`HttpMCP` 对齐 MCP 2024-11-05 规范——`Accept` 头 / SSE 响应体解析 /
`Mcp-Session-Id` 跨请求追踪 / `notifications/initialized`——可以**直接
对接 FastMCP 写的 server**（`mcp.server.fastmcp.FastMCP`）。

完整示例见 [examples/mcp_tool_use.py](examples/mcp_tool_use.py)：配一个
用 FastMCP 写的 20 行 stdio server（[examples/_mcp_demo_server.py](examples/_mcp_demo_server.py)），
展示你日常写自己业务 MCP server + 用 pyxis 连进 agent 的完整闭环。

带前端的可视化见 [apps/mcp-demo/](apps/mcp-demo/)：左栏扁平展开"LLM
眼里的工具清单"（native 蓝、MCP 绿），右栏流式显示 agent 每一步的
`thought → action → observation`——同一套卡片形态，只在 badge 上区分
来源，呼应"agent loop 对来源无感"。

## 没 API key 也能测

`FakeClient` 本身就在库里。它按队列顺序返回预置的 Pydantic 实例，记录
所有调用，也支持异步路径：

```python
from pyxis import FakeClient, Usage, step

fake = FakeClient(
    responses=[Analysis(observation="o", reasoning="r", conclusion="c")],
    usages=[Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)],
)

@step(output=Analysis, client=fake)
def analyze(t: str) -> str:
    """..."""
    return t

analyze("x")
assert fake.calls[0].messages[-1]["content"] == "x"
```

## 用 OpenRouter 跑 example

```bash
cp .env.example .env      # 把自己的 key 写进去
uv run --env-file .env python examples/research.py
uv run --env-file .env python examples/agent_tool_use.py
```

## 带前端的聊天应用示例

`apps/chat-demo/` 是一个完整的 **FastAPI + Vite+React+TS** 聊天应用，
展示同一份后端流式数据下、前端**一键切换**两种渲染风格：

- **Chat view**：`{role, content}` 气泡流（用户熟悉心智）
- **Inspect view**：Pydantic schema 字段逐个亮起（pyxis 独特的可视化）

这是"展示层归应用代码"的活证据——schema 是结构化骨架，怎么渲染由前端
自由决定。跑起来见 [apps/chat-demo/README.md](apps/chat-demo/README.md)。

## 开发

```bash
uv sync
uv run ruff format && uv run ruff check
uv run pytest                                        # 单元测试，零网络
uv run --env-file .env pytest tests/integration/     # 真实 LLM 烟雾测试
```

每次迭代都有对应的规格：[specs/](specs/)（SDD）+ 先写失败测试（TDD）。
[CHANGELOG.md](CHANGELOG.md) 记录版本历史；[ROADMAP.md](ROADMAP.md) 列出
待办项以及那些**故意不做**的事（违反核心哲学的都在这一段）。设计
依据见 [CLAUDE.md](CLAUDE.md)。

## 可观测性

两层分工：

| 层 | 工具 | 场景 |
|----|------|------|
| 框架层 | pyxis `trace()` / `TraceRecord` / `to_jsonl` / `StepHook` | 单测、本地 debug、自家日志 |
| LLM 层 | Langfuse、OpenTelemetry 等 | 生产 dashboard、告警、回归分析 |

pyxis 不在框架里造第二个 dashboard——世上已经有 Langfuse。接入方式是
**零侵入**：换一个 `OpenAI` 的 import，其他代码完全不动。两层可以同时
开。完整接入指南：[docs/langfuse.md](docs/langfuse.md)；可跑示例：
[examples/with_langfuse.py](examples/with_langfuse.py)。

## 和 LangGraph / DSPy 的关系

一句话：pyxis 不和它们抢"功能最全"或"自动调优"。pyxis 赌的是**可读性
与哲学一致性**——一个项目里的每个 LLM 调用都长得像一个普通 Python 函数，
每条思维链都是一段 Pydantic schema。诚实的三框架对比见
[docs/对比.md](docs/对比.md)（含"分析 + 规划"这个同一例子在三种框架下
的代码放一起看）。
