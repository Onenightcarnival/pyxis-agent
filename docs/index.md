# pyxis-agent

**声明式思维链（declarative chain-of-thought）agent 框架。**

> code as prompt · schema as workflow

---

## 定位：agent-for-machine

- LLM = 结构化数据生成器 → 直出 Pydantic 实例
- 下一段 Python 代码直接消费，给人看的由应用层从字段里拼
- **适合**：数据 pipeline 的 LLM 节点 · 要回归测试的业务 agent · 多 agent 机器对机器协作 · LLM 产出入库或聚合分析
- **不适合**：丝滑 chat app（→ Anthropic SDK 原生 tool use）· prompt 自动调优（→ DSPy）· 多 agent 图编排（→ LangGraph）

详见 [与其他框架对比](comparison.md)。

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

- **code as prompt** — 函数 docstring = system prompt；返回值 = user message
- **schema as workflow** — `Verdict` 字段顺序（`sentiment` 在 `confidence` 前）= LLM 的思维链步骤

---

## 两层编排

| 范围 | 机制 | 职责 |
|---|---|---|
| 隐式（单次 LLM 调用） | `instructor` + Pydantic 字段顺序 | 单次调用内部的思维链 |
| 显式（多次 LLM 调用） | 纯 Python 代码 | 调用之间的组合、分支、循环 |

显式那层直接用 `if` / `for` / 函数组合，不发明 DSL：

```python
from pyxis import flow

@flow
def triage(text: str) -> str:
    v = classify(text)
    if v.confidence < 0.6:
        return escalate(text)            # 另一个 @step
    return auto_reply(v.sentiment, text) # 另一个 @step
```

没有 DAG，没有 YAML，没有节点编辑器。

---

## 核心概念一览

| 概念 | 做什么 | 详见 |
|---|---|---|
| `@step` | 一次 LLM 调用（同步 / 异步 / 流式都有） | [概念](concepts/step.md) · [API](api/step.md) |
| `@flow` | 把多个 step 拼起来的普通 Python 函数 | [概念](concepts/flow.md) · [API](api/flow.md) |
| `Tool` / `@tool` | 工具 = `BaseModel` + `run() -> str` | [概念](concepts/tool.md) · [API](api/tool.md) |
| `ask_human` / `run_flow` | 生成器挂起等人类回应 | [概念](concepts/human.md) · [API](api/human.md) |
| `mcp_toolset` | MCP 远端工具翻成本地 `Tool` 子类 | [概念](concepts/mcp.md) · [API](api/mcp.md) |
| 可观测性 | 生产直接接 Langfuse；测试用 `trace()` + `FakeClient` | [概念](concepts/observability.md) |

---

## 下一步

| 想做的事 | 去 |
|---|---|
| **先看得见**——浏览器里看 schema 逐字段被填出来、native + MCP 工具混合调度 | [Demos](demos/index.md) |
| **照着抄**——一个可跑脚本对应一种姿势（研究、流式、ReAct、human-in-the-loop、Langfuse 接入 …） | [Cookbook](cookbook/index.md) |
| **读进去**——`@step` / `@flow` / `Tool` / `mcp_toolset` 各是什么、为什么长这样 | [概念](concepts/index.md) |
| **挑毛病**——完整的"故意不做"清单、为什么不发明 DSL / 不对标 ChatGPT 丝滑度 | [哲学与定位](concepts/philosophy.md) |
| **查签名**——每个公共符号的类型和 docstring | [API 参考](api/step.md) |
