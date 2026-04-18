# pyxis-agent

以**声明式思维链（declarative chain-of-thought）**为组织哲学的 agent 框架。

## 核心哲学

```
声明式思维链 = code as prompt + schema as workflow
```

- **code as prompt**：Python 函数的 docstring 就是 system prompt，
  函数的字符串返回就是 user message。函数**就是** prompt。
- **schema as workflow**：Pydantic 输出模型的**字段顺序**就是思维链——
  LLM 必须自上而下把它们填完，于是 schema 直接声明了推理步骤。

## 两层编排

| 范围 | 机制 | 职责 |
|------|------|------|
| **隐式**（单次 LLM 调用） | `instructor` + Pydantic 字段顺序 | 单次调用**内部**的思维链 |
| **显式**（多次 LLM 调用） | 纯 Python 代码 | 调用**之间**的组合、分支、循环 |

框架刻意拒绝为显式编排发明 DSL —— Python 本身就有 `if`、`for`、函数组合。
我们只提供这些原语：

- `@step(output=...)`：把 prompt 函数变成类型化的 LLM 调用。同步 `def` 得到
  `Step[T]`；异步 `async def` 得到 `AsyncStep[T]`。
- `@flow`：多步函数的薄包装，附带 `.run_traced(...)` 一键观测。同步/异步分派。
- `Tool`：`BaseModel` 子类，带 `run() -> str`。动作即 schema，`run()` 即代码。
  LLM 在 schema 的判别式联合 `action` 字段里选一个工具；Python 用
  `isinstance` / `action.run()` 分派。
- `@tool` 装饰器：把一个普通函数直接转成 Tool 子类——类名、`kind` 字面量、
  字段全部从函数签名推出；无需手写样板。
- `Client` / `AsyncClient`：provider 无关的 LLM 接口，返回
  `CompletionResult[T]`（output + 可选 `Usage`）。生产用 instructor
  背后的真 client，测试用 `FakeClient`。
- `pyxis.providers.openrouter_client()` / `openai_client()`：一行拿到
  已配好 sync + async 两路的 `InstructorClient`；未提供 api_key 时
  自动读对应环境变量。
- `trace()` + `TraceRecord`：基于 `ContextVar` 的可观测性，跨 asyncio
  task 自动传播。记录带 `usage` 与 `error`；`Trace.to_dict()` /
  `to_json()` / `to_jsonl(path)` / `total_usage()` / `errors()` 负责
  导出与聚合。`@step` 在 LLM 调用抛异常时也会写一条 `error` 非空的
  `TraceRecord` 再重抛，保证 trace 完整可复现。
- `@step(..., max_retries=N)`：把重试预算传给 instructor 用于结构化
  输出的校验重试。
- `Step.stream(...)` / `AsyncStep.astream(...)`：按字段逐步 yield partial
  实例，把 schema-as-CoT 的"字段被逐个填完"过程完整暴露给用户。底层
  借 instructor `create_partial`；一次流完整消费后写一条 TraceRecord。
- `StepHook`：只读观察者中间件，三个回调 `on_start` / `on_end` / `on_error`。
  通过 `add_hook()` / `remove_hook()` / `clear_hooks()` 管理。用来接
  Prometheus、Slack 告警、OpenTelemetry；**不**允许修改 messages / output。
- `ask_human` / `finish` / `run_flow` / `run_aflow`：human-in-the-loop。
  `@flow` 写成生成器函数，中间 `yield ask_human(...)` 挂起；驱动器把
  人类答案 `.send()` 回生成器。没有 checkpoint、没有状态快照——生成器
  本身就是活的状态。异步生成器里用 `yield finish(value)` 作终态哨兵
  （Python 禁用 async gen 的值返回）。

**不做的事**（违反核心哲学）：图式 DSL、YAML pipeline、节点编辑器、
隐式响应式状态、function-calling 协议适配、把 agent loop 藏进框架。
能写成 Python 函数的东西，就写成 Python 函数。

## 目录

```
src/pyxis/        库代码
  step.py         Step / AsyncStep + @step 装饰器
  flow.py         Flow / AsyncFlow + @flow 装饰器
  tool.py         Tool 基类
  trace.py        Trace / TraceRecord + trace() 上下文管理器
  client.py       Client + AsyncClient 协议、CompletionResult、
                  Usage、FakeClient、InstructorClient
  providers.py    provider 便捷工厂：openrouter_client、openai_client
  hooks.py        StepHook + add_hook/remove_hook/clear_hooks 观察者钩子
  human.py        HumanQuestion / FlowResult / ask_human / finish /
                  run_flow / run_aflow 人工介入原语
tests/            pytest（用 FakeClient，零网络）
tests/integration/ 真实 LLM 烟雾测试，需要 OPENROUTER_API_KEY
specs/            SDD 规格 —— 每个迭代一份 markdown
examples/         跑得起来的 demo（默认接 OpenRouter）
```

## 开发流

- 包管理器：**uv**（`uv sync`、`uv run`）。禁止直接 pip。
- Lint/格式化：**ruff**（`uv run ruff check`、`uv run ruff format`）。
- 测试：**pytest**（`uv run pytest`）。单元测试必须零网络通过。
- 集成测试：`uv run --env-file .env pytest tests/integration/`，需要
  `OPENROUTER_API_KEY`。
- Python：**3.12+**。生词：PEP 695 泛型语法（`class Foo[T: Base]`、
  `def f[T: Base]`）。
- **语言**：项目以中文为主（见 [规约 006](specs/006-中文化.md)）。
  散文、docstring、异常消息用中文；标识符、commit 前缀、配置 key 用英文。
- **文档必须与代码同步**：公共面变了就改 CLAUDE.md / README / CHANGELOG。

## 迭代方法：SDD + TDD

每个迭代以**一次 commit** 的形式落地：

1. 写 `specs/NNN-<名字>.md`：目的、API 草图、验收标准、不做（简短，≤ 40 行）。
2. 在 `tests/` 里按规格先写**失败**的测试。
3. 实现到测试全绿。
4. 跑 `uv run ruff format && uv run ruff check && uv run pytest`。
5. 动过 Client、Step、provider 相关代码时，跑集成套件一次。
6. 公共面变了同步 CLAUDE.md、README 与 CHANGELOG。
7. Commit，正文引用本次规格。

规格是契约，不是设计稿。长过 40 行说明迭代拆得不够，拆了再写。

## 测试契约

单元测试不碰真 LLM。`FakeClient` 按队列顺序返回预置的 Pydantic 实例
（同一队列服务同步与异步路径），每次调用写入 `.calls`；用尽或类型不匹配
抛异常。需要断言 prompt 内容时，就用 `.calls`。集成烟雾测试放
`tests/integration/`，没有环境变量时整体 skip，保证 CI 不依赖外部。
