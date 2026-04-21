# pyxis 与其他 agent 框架的对比

对标 **LangGraph** 与 **DSPy**——当前 Python agent 生态里定位差异最明显
的两家。一张横向表 + 几个维度的细对比，帮你挑。

## TL;DR

| 维度           | pyxis                      | LangGraph                  | DSPy                      |
|----------------|----------------------------|----------------------------|---------------------------|
| 核心抽象       | schema 即思维链 + 纯 Python | 状态机 + 节点图 DSL        | 声明式 program + teleprompter |
| 多轮编排       | `@flow`（普通函数）         | `StateGraph.add_node/edge` | 类里的 `forward(...)`     |
| Prompt 形态    | 函数 docstring             | 字符串 + PromptTemplate    | `Signature` 声明式字段    |
| 工具调用       | schema 判别式联合 + `.run()`| `ToolNode`、function calling| function calling 协议适配 |
| 优化目标       | 开发者体验与代码可读性      | 生产级状态机 + 可视化        | prompt 自动调优（核心卖点）|
| 学习门槛       | 低（就是写函数）           | 中（要学 graph 语义）       | 中（要学 signature + optimizer）|

## 同一个例子的三套写法：简单的"分析+规划"

### pyxis

```python
from pydantic import BaseModel, Field
from pyxis import flow, step

class Analysis(BaseModel):
    observation: str = Field(description="你注意到什么")
    reasoning: str = Field(description="为什么重要")
    conclusion: str = Field(description="一句话结论")

class Plan(BaseModel):
    goal: str
    steps: list[str]

@step(output=Analysis)
def analyze(topic: str) -> str:
    """你是严谨的分析师。"""
    return f"主题：{topic}"

@step(output=Plan)
def plan_from(a: Analysis) -> str:
    """你把分析转成计划。"""
    return a.model_dump_json()

@flow
def research(topic: str) -> Plan:
    return plan_from(analyze(topic))

result, t = research.run_traced("AI agents")
```

**特点**

- 思维链在字段顺序里（`observation → reasoning → conclusion`）
- 多步编排就是普通 Python 函数组合

### LangGraph 的典型写法

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    topic: str
    analysis: str | None
    plan: str | None

def analyze_node(state: State) -> State:
    response = llm.invoke(f"分析主题：{state['topic']}")
    return {"analysis": response.content}

def plan_node(state: State) -> State:
    response = llm.invoke(f"基于分析：{state['analysis']}\n做计划")
    return {"plan": response.content}

workflow = StateGraph(State)
workflow.add_node("analyze", analyze_node)
workflow.add_node("plan", plan_node)
workflow.add_edge("analyze", "plan")
workflow.add_edge("plan", END)
workflow.set_entry_point("analyze")
graph = workflow.compile()
result = graph.invoke({"topic": "AI agents"})
```

**特点**

- State 对象在节点之间传递，图"编译"成可执行对象
- 结构化输出得自己用 Pydantic + parser 再拼一层

### DSPy 的典型写法

```python
import dspy

class Analyze(dspy.Signature):
    """你是严谨的分析师。"""
    topic: str = dspy.InputField()
    observation: str = dspy.OutputField(desc="你注意到什么")
    reasoning: str = dspy.OutputField(desc="为什么重要")
    conclusion: str = dspy.OutputField(desc="一句话结论")

class PlanFrom(dspy.Signature):
    """你把分析转成计划。"""
    analysis: str = dspy.InputField()
    goal: str = dspy.OutputField()
    steps: list[str] = dspy.OutputField()

class Research(dspy.Module):
    def __init__(self):
        self.analyze = dspy.ChainOfThought(Analyze)
        self.plan = dspy.ChainOfThought(PlanFrom)

    def forward(self, topic):
        a = self.analyze(topic=topic)
        return self.plan(analysis=str(a))

result = Research()(topic="AI agents")
```

**特点**

- `Signature` 类似 pyxis 的 Pydantic schema，但走自己的字段系统
- 多步编排在 `forward` 里
- 核心卖点是 `teleprompter`（prompt 当可训练参数）——pyxis 完全不做

## 几个维度的细对比

### 1. 编排层：DSL 还是 Python？

- **LangGraph** — 图 DSL。能可视化状态机；要学"边 + 条件边 + 状态字段"一整套语义
- **DSPy** — `Module.forward(...)` 是 Python 函数；但 `Signature` 走自己的字段系统
- **pyxis** — `@flow` 是普通 Python 函数。`for` / `if` / `asyncio.gather`，没有第二层语义

### 2. 结构化输出

- **LangGraph** — 不是一等公民，要 `with_structured_output(...)` 或手动解析
- **DSPy** — `Signature` 输出字段是结构化的，但走自己的字段系统
- **pyxis** — Pydantic 是**唯一**的数据形状，字段顺序 = 思维链

### 3. 工具调用

- **LangGraph** — `ToolNode` + provider 的 function calling 协议
- **DSPy** — `dspy.Tool` 或 function calling
- **pyxis** — 工具 = `BaseModel + run()`；`Annotated[A | B, Field(discriminator="kind")]` 做判别式联合；LLM 填 JSON 就是"选工具"；Python `isinstance` + `.run()` 派发。不依赖 provider 的 function calling

### 4. 可观测性

- **LangGraph** — 原生跑 LangSmith，上线即送 trace 可视化
- **DSPy** — callback 或 `dspy.inspect_history()`
- **pyxis** — 生产接 [Langfuse](concepts/observability.md)（换 import）· 测试用 `trace()` + `FakeClient` · Prometheus / OTel / Slack 告警写 `StepHook`。框架不做 dashboard

### 5. 测试

- **LangGraph / DSPy** — mock LLM 自己搭；状态机的 assertion 面比函数大
- **pyxis** — `FakeClient([响应, ...])` + `fake.calls` + `TraceRecord` 全路径可断言。单测零网络是设计目标

### 6. 学习成本

从零到第一个能跑的 agent：

- **pyxis** — README 上手段 + Pydantic 知识 → ~15 分钟
- **LangGraph** — 要学 `StateGraph` / 节点 / 边 / 条件边 / checkpointer → 1–2 小时
- **DSPy** — 要学 Signature / Module / Teleprompter → 1–2 小时

## 什么时候选 pyxis？

- 团队已经在用 Pydantic，不想再学一个字段系统
- 想一眼看懂 agent 做了什么、每步调用什么、每个字段代表哪步推理
- 要自己控制可观测性管道（push 到 OpenTelemetry / Prometheus / Slack，而不是上托管平台）
- 希望单测不碰网络
- 项目规模小到中等（几十个 Step、几个 flow），不需要可视化状态机

## 什么时候**不**选 pyxis？

- 要**图可视化**做 PM / 设计评审 → LangGraph
- 核心要**自动优化 prompt**（teleprompter、MIPRO、BootstrapFewShot）→ DSPy
- 要**开箱即用的托管 trace UI** → LangSmith
- 多 agent 协商、复杂多图合并 → LangGraph 更成熟

## 总结

- **LangGraph** — 状态机表达力 + 生态完善度
- **DSPy** — prompt 自动调优
- **pyxis** — 可读性 + 测试友好度

对口了就挑对应的。
