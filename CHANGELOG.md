# 变更日志（Changelog）

本文件按 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 的格式
记录每次发布，版本号遵守 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增

- **语言规约**（[规格 006](specs/006-中文化.md)）——项目的文档、规格、
  源码 docstring、异常消息、commit message 正文全部切换为中文。代码
  标识符仍按 PEP 8 使用英文。新增 `tests/test_language_policy.py`
  防止未来迭代意外把这些文件回退成英文。
- **`@tool` 装饰器**（[规格 007](specs/007-tool-装饰器.md)）——把一个普通
  Python 函数直接转成 Tool 子类：函数名变 PascalCase 类名、自动生成
  `kind: Literal[...] = ...` 字段、参数推成 Pydantic 字段、函数本体接管
  `run()`。工具的定义成本降到"就是一个函数"。真实 LLM 小 agent 场景
  已跑通 `7*6=42` 用 `@tool` 写的 calculate + finish。

### 变更

- 所有既存的 README、CLAUDE.md、CHANGELOG、ROADMAP、规格 001–005、
  源码 docstring、示例 docstring 一次性重写为中文。Commit 历史按惯例
  不做破坏性重写。

## [0.2.0] — 2026-04-18

首个功能完整的版本。在 `main` 上又走了三轮 SDD+TDD 迭代。

### 新增

- **Tool 原语** —— `Tool(BaseModel)` 子类，带 `run() -> str`，用于声明式
  思维链的 tool use。Tool 作为判别式联合参与 Step 输出 schema；Python 按
  类型分派。（[规格 003](specs/003-tool.md)）
- **异步支持** —— `@step` / `@flow` 检测 `async def` 并分派到
  `AsyncStep` / `AsyncFlow`。新增 `AsyncClient` 协议；`FakeClient` 和
  `InstructorClient` 两路都实现。trace 的 `ContextVar` 自动穿透
  `asyncio.gather`。（[规格 004](specs/004-async.md)）
- **可观测性三件套** —— `Usage` 数据类 + `CompletionResult[T]` 包裹了
  Client 协议的返回值；`@step(..., max_retries=N)` 转发给 instructor 的
  校验重试；`TraceRecord.usage` 每次调用都填入；`Trace.to_dict()` /
  `to_json()` / `total_usage()` 负责结构化导出与成本汇总；
  `InstructorClient` 通过 `create_with_completion` 提取 usage。
  （[规格 005](specs/005-observability.md)）

### 变更

- `Client.complete` / `AsyncClient.acomplete` 的返回类型从裸 model 改成
  `CompletionResult[T]`，同时新增 `max_retries` kwarg。实现 Client 协议
  的外部代码需要跟进。（1.0 之前允许破坏性变更。）
- `FakeClient` 构造函数新增可选 `usages=` 并列列表。
- `FakeCall` 新增 `max_retries: int` 字段，便于测试断言转发。

### 用真实 LLM 验证

通过 OpenRouter（模型 `openai/gpt-5.4-nano`）跑通 4 个 live smoke：
单步调用、多步 flow + trace、`asyncio.gather` 并发、真实 token 用量捕获。

## [0.1.0] — 2026-04-18

首个 MVP。把"声明式思维链"这套哲学落成代码。

### 新增

- **`Step`** —— `@step(output=M)` 装饰器。docstring 即 system prompt；
  字符串返回即 user message；Pydantic 字段顺序即隐式 CoT。
  （[规格 001](specs/001-step.md)）
- **`Flow`** —— `@flow` 包装 + `.run_traced(...)`，用于把多次调用的
  显式编排写成普通 Python。不引入 DSL。（[规格 002](specs/002-flow.md)）
- **`trace()`** 上下文管理器 + 经 `ContextVar` 捕获的 `TraceRecord`。
- **`Client`** 协议：`FakeClient`（测试，零网络）+ `InstructorClient`
  （生产，通过 instructor 对接 OpenAI 兼容接口）。
- SDD+TDD 迭代协议：先写 `specs/NNN-*.md`；先写失败测试；ruff + pytest
  为闸；一次迭代一次 commit。
- uv 项目脚手架 + ruff + pytest + mypy 配置。
