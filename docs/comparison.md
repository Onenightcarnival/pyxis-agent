# pyxis 与其他 agent 框架的对比

对象是 **LangGraph** 和 **DSPy**，这两个是当前 Python agent 生态里定位差异
最明显的两家。本文给一张横向表，加几个典型维度的对比，帮你判断什么场景
该选哪个。

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

**特点**：思维链在字段顺序里（`observation → reasoning → conclusion`），
多步编排就是普通 Python 函数组合。

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

**特点**：State 对象在节点之间传递，图被"编译"成一个可执行对象。
结构化输出得自己用 Pydantic + parser 再拼一层。

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

**特点**：`Signature` 很像 pyxis 的 Pydantic schema，但走自己的字段系统；
多步编排在 `forward` 里。真正的卖点是 `teleprompter`（把 prompt 本身当成
可训练参数），这在 pyxis 里完全不做。

## 几个维度的细对比

### 1. 编排层：DSL 还是 Python？

- **LangGraph**：图 DSL。优点是能直接可视化状态机、适合复杂的条件分支
  和回环；缺点是要理解"边 + 条件边 + 状态字段"的一整套语义。
- **DSPy**：`Module.forward(...)` 就是 Python 函数，这一点和 pyxis 一样；
  但 Signature 走自己的字段系统，不是纯 Pydantic。
- **pyxis**：`@flow` 就是一个普通 Python 函数。循环用 `for`，分支用
  `if`，并行用 `asyncio.gather`——没有第二层语义。

### 2. 结构化输出

- **LangGraph**：不是一等公民。需要 `with_structured_output(SchemaClass)`
  或手动解析。
- **DSPy**：`Signature` 的输出字段就是结构化的，类似 pyxis，但是 DSPy
  自己的字段系统。
- **pyxis**：Pydantic 是**唯一**的数据形状。输入是函数参数；输出是一个
  Pydantic model。字段顺序直接被 LLM 当成思维链。

### 3. 工具调用

- **LangGraph**：`ToolNode` + provider 的 function calling 协议。
- **DSPy**：通过 `dspy.Tool` 或者直接用 function calling。
- **pyxis**：工具是 `BaseModel + run()`；用 `Annotated[A | B, Field(discriminator="kind")]`
  组成判别式联合作为 Step 输出 schema 的一个字段。LLM"选工具"就是
  在填写 JSON；Python 用 `isinstance` + `.run()` 派发。不依赖 provider
  的 function calling 协议。

### 4. 可观测性

- **LangGraph**：原生能跑 LangSmith，上线即送 trace 可视化。
- **DSPy**：通过 callback 或 `dspy.inspect_history()`。
- **pyxis**：生产直接接 [Langfuse](concepts/observability.md)（换个 import 即可）；
  测试 / 本地 debug 用内置 `trace()` + `TraceRecord` + `FakeClient`；要接
  Prometheus / OTel / Slack 告警就写 `StepHook`。框架本身不做 dashboard。

### 5. 测试

- **LangGraph**：mock LLM 得自己搭。状态机的 assertion 面比函数大。
- **DSPy**：类似。
- **pyxis**：`FakeClient([响应, ...])` + `fake.calls` 调用日志 +
  `TraceRecord` 对错误路径完整可断言。单测零网络是设计目标。

### 6. 学习成本

上手一个新框架要多久？粗略的"从零到写出第一个能跑的 agent"：

- pyxis：读 README 的上手段（~5 分钟）+ Pydantic 已有知识 → **15 分钟**。
- LangGraph：要读 `StateGraph` / 节点 / 边 / 条件边 / checkpointer →
  **1–2 小时**。
- DSPy：要读 Signature / Module / Teleprompter → **1–2 小时**。

## 什么时候选 pyxis？

- 团队已经在用 Pydantic，不想多学一个字段系统。
- 想一眼能看懂 agent 做了什么、每一步调用了什么、每个字段代表哪步推理。
- 需要自己控制可观测性管道（push 到 OpenTelemetry/Prometheus/Slack
  而不是上托管平台）。
- 希望单测不碰网络。
- 项目规模小到中等（几十个 Step、几个 flow），不需要可视化状态机。

## 什么时候**不**选 pyxis？

- 需要**图可视化**做 PM / 设计评审 → LangGraph。
- 核心诉求是**自动优化 prompt**（teleprompter、MIPRO、BootstrapFewShot）
  → DSPy。
- 需要**长期托管的 trace UI** 开箱即用（不想自己搭）→ LangSmith 系。
- 多 agent 协商、复杂的多图合并 → LangGraph 更成熟。

## 总结

三家定位不一样：LangGraph 赢在状态机表达力和生态完善度，DSPy 赢在 prompt
自动调优，pyxis 赢在可读性和测试友好度。对口了就挑对应的。
