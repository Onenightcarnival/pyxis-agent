# pyxis-agent

**声明式思维链的 Python agent 框架。**

> **`声明式思维链 = code as prompt + schema as workflow`**

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
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from pyxis import Tool, flow, step

class Calculate(Tool):
    """算一个数学表达式。"""
    kind: Literal["calculate"] = "calculate"
    expression: str
    def run(self) -> str:
        return str(eval(self.expression, {"__builtins__": {}}, {}))

class Finish(Tool):
    """停止并报出答案。"""
    kind: Literal["finish"] = "finish"
    answer: str
    def run(self) -> str:
        return self.answer

Action = Annotated[Calculate | Finish, Field(discriminator="kind")]

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
        if isinstance(d.action, Finish):
            return d.action.answer
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
