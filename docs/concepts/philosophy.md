# 哲学与定位

## 基本设定

pyxis 把 LLM 当作结构化数据生成器。一次调用返回一个 Pydantic 实例，后续逻辑用 Python 代码处理这个实例。

## 设计要求

这个设定带来四个要求：

- 输出用 Pydantic 表达
- 测试可以用 `FakeClient` 预置响应并断言结果
- Pydantic schema 是单次调用的主契约，字段顺序表示输出步骤
- 被装饰函数是 input builder，返回值是本次调用的输入消息；装饰后的 step callable 返回 Pydantic 实例；函数 docstring 不进入 LLM 上下文

## 函数式思想

pyxis 不是一个函数式编程框架，但它借用了函数式思想里最重要的边界感：

> 把一次 LLM 调用收束成一个可组合、可替换、可测试的函数边界。

`@step` 装饰前，函数是普通的 input builder：应用层输入进去，返回本次调用的
user message。`@step` 装饰后，同一个名字绑定到 `Step[T]`：调用它会执行一次
LLM 调用，并返回类型化的 Pydantic 实例。

所以 pyxis 里的 LLM 更像一个带自然语言理解能力的“AI 函数”：

- 函数签名声明应用层输入
- 函数体声明本次调用的输入文本
- Pydantic schema 声明返回类型和单次调用内部的生成顺序
- Python 函数组合负责多步 workflow
- `FakeClient` 可以把这个 AI 函数替换成确定性函数，用于单元测试

这也是 pyxis 不发明图 DSL、prompt 模板语言和全局 agent runtime 的原因。
LLM 的不确定性被包在 step 边界里；边界外尽量回到普通 Python 世界。

## 边界

pyxis 不提供这些能力：

- 图式 DSL / YAML pipeline / 节点编辑器
- 通用 agent loop（ReAct、Plan-and-Execute）
- function-calling 协议适配层（Pydantic 判别式联合够用）
- 内置 memory / vector store 抽象
- prompt 模板语言
- 全局 registry（显式 import 够用）
- 手写 messages 列表的入口
- client 封装。`@step(client=...)` 使用 `openai.OpenAI` / `AsyncOpenAI`
  或 `instructor.from_openai(...)` 的实例
- 观测体系（trace / usage / hook）。接 Langfuse / OpenTelemetry / APM，
  见 [可观测](../cookbook/observability.md)

多轮对话、assistant 轮次控制、图式编排、长期状态管理，可以直接使用 OpenAI SDK、LangGraph、Temporal 或业务系统。
