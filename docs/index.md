# pyxis-agent

**声明式思维链（declarative chain-of-thought）agent 框架。**

> code as prompt · schema as workflow

---

## 一句话定位：agent-for-machine

LLM 的直接输出喂给下一段 Python 代码消费，**不是喂给人眼消费**。
给人看的东西由应用层用 schema 字段拼出来。

|  | Claude Desktop / ChatGPT 风 | pyxis |
|---|---|---|
| LLM 直接输出 | 给人看的自然语言 | 给机器解析的 Pydantic |
| 人能看的东西来自 | LLM 本身 | 应用层渲染 |
| 对话丝滑度 | 高 | 低（先填 schema 再渲染） |
| 可测试 / 可审计 / 可回放 | 低 | 高（`==` 对 Pydantic 实例） |

pyxis 的战场是 **LLM 当结构化数据生成器**——数据 pipeline 里的 LLM 节点、
要做回归测试的业务 agent、多 agent 机器对机器协作、LLM 产出直接入库或做
聚合的场景。

想做丝滑 chat app，用 Anthropic SDK；想做 prompt 自动调优，用 DSPy；
多 agent 图编排，用 LangGraph。pyxis 不抢这些位子——详见[对比其他框架](comparison.md)。

---

## 安装

```bash
uv add pyxis-agent
# 或
pip install pyxis-agent
```

Python 3.12+。

---

## 30 秒看懂

```python
from pydantic import BaseModel
from pyxis import step

class Verdict(BaseModel):
    sentiment: str     # 先判情感
    confidence: float  # 再给置信度——字段顺序就是思维链

@step(output=Verdict)
def classify(text: str) -> str:
    """你是一个情感分类器。判断给定文本的情感倾向，给出置信度。"""
    return text

v = classify("今天简直完美")
assert v.sentiment == "positive"
```

两件事同时发生：

- **code as prompt** — 函数的 docstring 就是 system prompt，返回值就是 user message
- **schema as workflow** — `Verdict` 的字段顺序（`sentiment` 在 `confidence` 之前）
  就是 LLM 的思维链步骤

---

## 两层编排

框架只有两层，**没有第三层**：

| 范围 | 机制 | 职责 |
|------|------|------|
| **隐式**（单次 LLM 调用） | `instructor` + Pydantic 字段顺序 | 单次调用**内部**的思维链 |
| **显式**（多次 LLM 调用） | 纯 Python 代码 | 调用**之间**的组合、分支、循环 |

框架刻意拒绝为显式编排发明 DSL——Python 本身就有 `if`、`for`、函数组合。

```python
from pyxis import flow

@flow
def triage(text: str) -> str:
    v = classify(text)
    if v.confidence < 0.6:
        return escalate(text)            # 另一个 @step
    return auto_reply(v.sentiment, text) # 另一个 @step
```

显式编排 = 纯 Python。没有 DAG、没有 YAML、没有节点编辑器。

---

## 核心概念一览

| 概念 | 做什么 | 详见 |
|---|---|---|
| `@step` | 一次 LLM 调用（同步 / 异步 / 流式都有） | [概念](concepts/step.md) · [API](api/step.md) |
| `@flow` | 多步组合的薄壳，附带 `.run_traced()` | [概念](concepts/flow.md) · [API](api/flow.md) |
| `Tool` / `@tool` | 工具 = `BaseModel` + `run() -> str`，动作即 schema | [概念](concepts/tool.md) · [API](api/tool.md) |
| `trace()` | `ContextVar` 驱动的可观测性，跨 asyncio 传播 | [API](api/trace.md) |
| `StepHook` | 只读观察者中间件：`on_start` / `on_end` / `on_error` | [概念](concepts/hooks.md) · [API](api/hooks.md) |
| `ask_human` / `run_flow` | human-in-the-loop：生成器挂起等人类回应 | [概念](concepts/human.md) · [API](api/human.md) |
| `mcp_toolset` | MCP 适配：远端工具翻译成 pyxis `Tool` 子类 | [概念](concepts/mcp.md) · [API](api/mcp.md) |

---

## 故意不做的事

违反核心哲学的东西，框架就不做：

- 图式 DSL、YAML pipeline、节点编辑器
- 隐式响应式状态
- function-calling 协议适配（用 schema 就够了）
- 把 agent loop 藏进框架

**能写成 Python 函数的东西，就写成 Python 函数。**

---

## 从哪里开始看

- 想读哲学：[哲学与定位](concepts/philosophy.md)
- 想写代码：[概念指南](concepts/index.md) → 从 Step 开始
- 想查 API：[API 参考](api/step.md)
