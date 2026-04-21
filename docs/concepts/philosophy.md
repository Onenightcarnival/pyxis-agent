# 哲学与定位

## 一句话

> **LLM 的每次输出都要被下一段 Python 代码消费。**

## 代码消费的四条约束

把"LLM 输出喂给代码、不喂给人眼"当前提，下面四件事自动跟着来：

- **输出结构化** — 自然语言没结构 → Pydantic
- **输出可回放** — `TraceRecord` 存的是 Pydantic 实例；`assert trace.records[-1].output == Expected(...)` 一行断言
- **prompt 可追踪** — 函数 docstring 就是 prompt；git 管版本；无 template engine 中转层
- **推理步骤显式** — schema 字段顺序 = 思维链；改顺序 = 改推理

## 少做一点

设计层面不做：

- 图式 DSL / YAML pipeline / 节点编辑器
- 通用 agent loop（ReAct、Plan-and-Execute）
- function-calling 协议适配层（Pydantic 判别式联合够用）
- 内置 memory / vector store 抽象
- prompt 模板语言（docstring 就是模板）
- 全局 registry（显式 import 够用）
- 自建可观测性 dashboard（生产接 [Langfuse](observability.md)）

能用普通 Python 函数组合表达的事，就写成普通 Python 函数。
