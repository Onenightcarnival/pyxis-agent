# pyxis 与其他 agent 框架的对比

这里对比 **LangGraph** 和 **DSPy**。三者都能写 agent，但抽象层不同。

## TL;DR

| 维度           | pyxis                      | LangGraph                  | DSPy                      |
|----------------|----------------------------|----------------------------|---------------------------|
| 核心抽象       | Pydantic schema + Python 函数 | 状态机 + 节点图 DSL        | 声明式 program + teleprompter |
| 多轮编排       | `@flow`（普通函数）         | `StateGraph.add_node/edge` | 类里的 `forward(...)`     |
| Prompt 形态    | Pydantic schema + user input | 字符串 + PromptTemplate    | `Signature` 声明式字段    |
| 工具调用       | schema 判别式联合 + `.run()`| `ToolNode`、function calling| function calling 协议适配 |
| 优化目标       | 结构化输出、测试、代码可读性 | 生产级状态机 + 可视化        | prompt 自动调优 |
| 学习门槛       | 低                         | 中                         | 中                         |

## 同一个例子：分析后生成计划

### pyxis

```python
from openai import OpenAI
from pydantic import BaseModel, Field
from pyxis import flow, step

client = OpenAI(api_key="...")

class Analysis(BaseModel):
    observation: str = Field(description="你注意到什么")
    reasoning: str = Field(description="为什么重要")
    conclusion: str = Field(description="一句话结论")

class Plan(BaseModel):
    goal: str
    steps: list[str]

@step(output=Analysis, model="gpt-4o", client=client)
def analyze(topic: str) -> str:
    return f"请严谨分析这个主题：{topic}"

@step(output=Plan, model="gpt-4o", client=client)
def plan_from(a: Analysis) -> str:
    return f"请把这份分析转成计划：\n{a.model_dump_json()}"

@flow
def research(topic: str) -> Plan:
    return plan_from(analyze(topic))

result = research("AI agents")
```

说明：

- `Analysis` 的字段顺序定义输出顺序
- `research(...)` 用普通函数组合两个 step

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

说明：

- `State` 在节点之间传递
- graph 编译后执行

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

说明：

- `Signature` 定义输入输出字段
- 多步编排写在 `forward` 里
- DSPy 提供 teleprompter 做 prompt 优化

## 维度对比

### 1. 编排层

- **LangGraph**：图 DSL，使用节点、边、条件边和状态字段
- **DSPy**：`Module.forward(...)` 是 Python 函数，字段由 `Signature` 定义
- **pyxis**：`@flow` 是普通 Python 函数，直接使用 `for`、`if`、`asyncio.gather`

### 2. 结构化输出

- **LangGraph**：通过 `with_structured_output(...)` 或解析器处理
- **DSPy**：使用 `Signature` 输出字段
- **pyxis**：使用 Pydantic 输出模型

### 3. 工具调用

- **LangGraph**：`ToolNode` + provider function calling
- **DSPy**：`dspy.Tool` 或 function calling
- **pyxis**：`BaseModel + run()`；用 Pydantic 判别式联合选择工具，用 Python 执行工具

### 4. 可观测性

- **LangGraph**：接 LangSmith
- **DSPy**：callback 或 `dspy.inspect_history()`
- **pyxis**：接 [Langfuse](cookbook/observability.md)、OpenTelemetry、Datadog、New Relic，观测位置在 OpenAI SDK 层

### 5. 测试

- **LangGraph / DSPy**：需要按项目自行 mock LLM
- **pyxis**：`FakeClient([响应, ...])` 返回预置模型，`fake.calls` 记录调用参数

### 6. 学习成本

从零到第一个示例：

- **pyxis**：README + Pydantic 基础
- **LangGraph**：`StateGraph`、节点、边、条件边、checkpointer
- **DSPy**：Signature、Module、Teleprompter

## 适合 pyxis 的场景

- 数据 pipeline 里的 LLM 节点
- 业务 agent 需要回归测试
- LLM 产出需要入库或分析
- 团队已经在用 Pydantic，不想再学一个字段系统
- 希望单测不碰网络
- 项目规模小到中等，不需要可视化状态机

## 更适合其他工具的场景

- 图状控制流、断点续跑、checkpointer、多 agent 协商：LangGraph
- 图可视化评审：LangGraph
- prompt 自动优化：DSPy
- 托管 trace UI：LangSmith
- 聊天界面体验优先：原生 chat SDK

## 总结

- **LangGraph**：状态机和图编排
- **DSPy**：prompt 优化
- **pyxis**：Pydantic 输出、Python 组合、单元测试
