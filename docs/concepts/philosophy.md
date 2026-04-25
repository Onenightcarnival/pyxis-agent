# 哲学与定位

## 基本设定

pyxis 把 LLM 当作结构化数据生成器。一次调用返回一个 Pydantic 实例，后续逻辑用 Python 代码处理这个实例。

## 设计要求

这个设定带来四个要求：

- 输出用 Pydantic 表达
- 测试可以用 `FakeClient` 预置响应并断言结果
- prompt 写在函数 docstring 里，随代码一起管理
- schema 字段顺序表示输出步骤

## 边界

pyxis 不提供这些能力：

- 图式 DSL / YAML pipeline / 节点编辑器
- 通用 agent loop（ReAct、Plan-and-Execute）
- function-calling 协议适配层（Pydantic 判别式联合够用）
- 内置 memory / vector store 抽象
- prompt 模板语言（docstring 就是模板）
- 全局 registry（显式 import 够用）
- 手写 messages 列表的入口
- client 封装。`@step(client=...)` 使用 `openai.OpenAI` / `AsyncOpenAI`
  或 `instructor.from_openai(...)` 的实例
- 观测体系（trace / usage / hook）。接 Langfuse / OpenTelemetry / APM，
  见 [可观测](../cookbook/observability.md)

多轮对话、assistant 轮次控制、图式编排、长期状态管理，可以直接使用 OpenAI SDK、LangGraph、Temporal 或业务系统。
