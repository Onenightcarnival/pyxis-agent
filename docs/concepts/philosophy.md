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
- 通用 agent loop（ReAct、Plan-and-Execute）——要图状控制流走 [LangGraph](../comparison.md)
- function-calling 协议适配层（Pydantic 判别式联合够用）
- 内置 memory / vector store 抽象
- prompt 模板语言（docstring 就是模板）
- 全局 registry（显式 import 够用）
- 手写 messages 列表的入口——docstring 是 system、函数返回是 user，
  没有第三个位置。多轮对话 / assistant 轮次控制直接用 OpenAI SDK
- client 封装——`@step(client=...)` 吃 `openai.OpenAI` / `AsyncOpenAI`
  或 `instructor.from_openai(...)` 的实例
- 观测体系（trace / usage / hook）——接 Langfuse / OpenTelemetry / APM，
  见 [可观测性](observability.md)

能用普通 Python 函数组合表达的事，就写成普通 Python 函数。

## 开发方法

pyxis 的 SDD 不再靠长期保留的迭代规格文档驱动。概念设计和工程设计分层：

- **产品 / 哲学 / 定位层**直接改长期文档：`docs/concepts/`、`README.md`、
  `CLAUDE.md` / `AGENTS.md`。这些文档表达当前系统是什么、为什么故意不做某些事。
- **代码 / API / 行为层**走 TODO-driven skeleton：先建真实模块、类型、
  函数签名和 docstring，在实现区留下 `TODO(...)` 或 `NotImplementedError`，
  再用失败测试绑定行为契约。
- 迭代完成时，测试、ruff、文档构建通过，并且本轮 `TODO(...)` 清零。
  历史解释交给 commit message 和 GitHub Releases，不把临时规格伪装成长期文档。
