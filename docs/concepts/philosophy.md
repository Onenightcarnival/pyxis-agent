# 哲学与定位

## 一句话

> **LLM 的每次输出都要被下一段 Python 代码消费。**

## 代码消费的四条约束

把"LLM 输出喂给代码、不喂给人眼"当前提，下面四件事自动跟着来：

- **输出结构化** — 自然语言没结构 → Pydantic
- **输出可回放** — 测试里 `FakeClient` 预置 Pydantic 响应，`assert result == Expected(...)` 一行断言；生产观测接 Langfuse / APM
- **prompt 可追踪** — 函数 docstring 就是 prompt；git 管版本；无 template engine 中转层
- **推理步骤显式** — schema 字段顺序 = 思维链；改顺序 = 改推理

## 少做一点

设计层面不做：

- 图式 DSL / YAML pipeline / 节点编辑器
- 通用 agent loop（ReAct、Plan-and-Execute）——复杂图状控制流请用 [LangGraph](../comparison.md)
- function-calling 协议适配层（Pydantic 判别式联合够用）
- 内置 memory / vector store 抽象
- prompt 模板语言（docstring 就是模板）
- 全局 registry（显式 import 够用）
- **永远不让用户手写 messages 列表**——docstring 是 system、函数返回
  是 user，就这两个。想要多轮 chat、手动控制 system / user / assistant
  轮次？那不是 pyxis 的用法，直接用原生 OpenAI SDK 或 instructor。
- **不造观测生态**——Langfuse / OpenTelemetry / Datadog 已经足够好；
  pyxis 只暴露干净的 OpenAI SDK 接口，观测工具自己来适配。
- **不封装 client**——`@step(client=...)` 直接吃 `openai.OpenAI` /
  `AsyncOpenAI` 或已 `instructor.from_openai(...)` 的实例。构造 client
  是你业务代码的事。
- **不提供 hook / middleware 协议**——Python 装饰器叠加已经是最好的
  middleware 机制。

能用普通 Python 函数组合表达的事，就写成普通 Python 函数。
