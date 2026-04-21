# 变更日志（Changelog）

本文件按 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 的格式
记录每次发布，版本号遵守 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增

- **MCP（Model Context Protocol）适配层 —— `pyxis.mcp`**（规格 013）。
  把一个 MCP server 变成一批 pyxis `Tool` 子类：声明 `MCPServer` +
  `StdioMCP | HttpMCP` 判别式联合、`async with mcp_toolset(server) as
  tools:` 拿到 `list[type[Tool]]`，直接拼进 agent loop 的判别式联合。
  **`Tool.run()` 契约不扩**——HTTP 用 `httpx.Client`、stdio 用持久子
  进程 + `id→response` 关联表，传输复杂度全部吸收在 adapter 里，
  agent loop 里仍是一行 `d.action.run()`。`trace()` 自动生效（零集成）。
  故意不做（见 [specs/013-mcp.md](specs/013-mcp.md)）：不扩 `arun` /
  不做 SSE / 不做 resources / prompts / sampling / 不做全局 registry /
  不做断线重连 / 不做 tool schema 动态刷新 / 不做 `ToolSet` 抽象
  protocol（只有 MCP 一家实现时它就是空抽象）。
- **`examples/mcp_tool_use.py` + `examples/_mcp_demo_server.py`**：零外
  部依赖的示例——后者是一个 10 行的 stdio MCP server（`word_count` /
  `reverse`），前者把它和 `Finish` native 工具拼成混合联合跑 agent loop。
  真场景只需把 `StdioMCP(command=..., args=[...])` 指向任意 MCP server。
- **`apps/mcp-demo/` —— 带前端的 MCP 可视化 demo**。
  - 后端：FastAPI，启动时 `async with mcp_toolset(...)` 连上本地 demo
    MCP server，POST `/run` 流式推帧：先一帧 `inventory`（工具清单 +
    每个工具的 source 标签：`native` 或 `mcp:<server>`），再按 agent
    迭代推 `step` 帧（`thought` + `action{name, args, source}` +
    `observation`），最后 `done` 携带 `answer`。
  - 前端：Vite + React + TS + Tailwind。左栏 `Inventory` 把工具按 source
    分组展示（native 蓝、MCP 绿），右栏 `StepCard` 流逐步显示 agent 的
    每一步——同一种卡片形态渲染 native / MCP，只在 badge 上区分来源，
    呼应"agent loop 对来源无感"。
  - 详见 [apps/mcp-demo/README.md](apps/mcp-demo/README.md)。
- **CLAUDE.md 记录协作模式**：明确 Claude（我）是这个项目的"AI 产品
  经理"、用户是"哲学方向引导者 + 品味守门员"。附带"自知之明"三条
  注意事项留给未来读文档的 Claude——警惕训练偏置导致的讨好折衷、
  明确决策所有权属于 AI、理解协作模式而非模型能力决定结果。这段
  写进 CLAUDE.md 顶部（定位段之后、核心机制之前）。
- **顶层定位加一层**：项目被重新定位为 **agent-for-machine** 阵营——
  LLM 直接输出喂给下一段 Python 代码消费，不喂给人眼。这句话比"声明式
  思维链"更易 catch，明确告诉读者 pyxis 服务谁、不服务谁。落到
  CLAUDE.md（新加"定位"段 + 对照 Claude Desktop 的表）、README（新加
  "定位一句话"段）、ROADMAP 的"故意不做"段（加了"对标 Claude Desktop
  丝滑度"这条）、`examples/human_review.py` 顶 docstring（加"诚实提示"
  承认 HITL 丝滑度权衡）、`apps/chat-demo/README.md`（加"诚实的丝滑度
  说明"，解释 Chat view 永远不如原生 chat app 的原因）。
- **`apps/chat-demo/` —— 带前端的聊天应用示例**。monorepo 风格的子目录
  应用（非库，打包时 exclude）。
  - 后端：FastAPI + pyxis，POST `/chat` 返回 SSE 流，逐帧推 partial
    Pydantic JSON（`ChatReply{thought, response}`）。历史由前端维护并
    随请求发来，后端无状态。
  - 前端：Vite + React + TS + Tailwind。顶部 **Chat / Inspect** 视图切换：
    - Chat view：`{role, content}` 气泡流，只显示 `response`（熟悉心智）；
    - Inspect view：schema 字段逐个亮起（`thought` 先 filled、`response`
      后 filled），schema-as-CoT 的可视化。
  - 两种视图**共享同一份后端流式数据**，按一下开关就是"展示层归应用代码"
    的活证据——schema 在两种渲染风格下同时自然。
  - 多轮对话直接可跑：第二轮能正确引用第一轮语境。
  - 详见 [apps/chat-demo/README.md](apps/chat-demo/README.md)。
- 根 `pyproject.toml` 加 `[tool.hatch.build] exclude = ["apps"]` 与 ruff
  `extend-exclude = ["apps"]`。
- `.gitignore` 加 `node_modules/`、`apps/*/frontend/dist/`、`.claude/`、
  `*.tsbuildinfo`。

## [1.1.0] — 2026-04-18

两处关键 use case 补齐：**人工介入多轮对话** 与 **托管级可观测性**。
核心 API 向后兼容 1.0.0；新增能力都走新入口，老代码不用改。

### 新增

- **Human-in-the-loop**（[规格 012](specs/012-human-in-the-loop.md)）——
  `@flow` 写成生成器函数，中间 `yield ask_human(...)` 挂起等人回答；
  `run_flow` / `run_aflow` 驱动生成器，把 `on_ask` 的返回值（可选
  Pydantic 验证）`.send()` 回去。异步生成器用 `yield finish(value)`
  替代 `return value`（Python 禁用语法限制）。不走 checkpoint——生成器
  本身就是活的状态；跨进程恢复是用户的事。
  - 配套示例 `examples/human_review.py`：LLM 产计划 → 终端审核 →
    根据意见迭代最多 3 轮。
  - 真实 LLM live smoke：plan + review 路径跑通。
  - 18 个新单元测试覆盖同步/异步生成器、schema 验证、多轮对话、
    异常透传、finish 哨兵、metadata 保留。
  - 多轮对话 use case 无需额外 API：把 `yield ask_human` 放进
    `while True` 就是 chat session。
- **Langfuse 零侵入接入指南** ——
  新增 [docs/langfuse.md](docs/langfuse.md) 与
  [examples/with_langfuse.py](examples/with_langfuse.py)。接入方式不在
  pyxis 里加任何代码：用户把 `OpenAI` 的 import 换成
  `from langfuse.openai import OpenAI`，塞进 `instructor.from_openai(...)`，
  其他代码完全不动。
  - 可观测性被显式拆成**两层**：框架层 pyxis `trace()`（Step 名、
    Pydantic schema、flow 结构、错误可见性）+ LLM 层 langfuse
    （prompt / response / token / 延迟、跨服务 trace 拼接）。
  - 两层同时开、互不干扰。pyxis 不再造 dashboard。

### 变更

- `tool-decorator` live smoke 的 `max_retries` 从 2 升到 3，应付 LLM
  偶发的 schema 不匹配。
- ROADMAP 标记"对接 OpenTelemetry"在框架层不再做——走 Langfuse 或用户
  自己写 `StepHook` 就够了。

## [1.0.0] — 2026-04-18

## [1.0.0] — 2026-04-18

首个稳定版本。0.2.0 → 1.0.0 的跨度覆盖：项目中文化、`@tool` 装饰器糖、
provider 工厂、JSONL 落盘、错误可见性、流式输出、观察者中间件、示例
画廊。此后 API 保持向后兼容，按语义化版本演进。

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
- **Provider 工厂与 JSONL 落盘**（[规格 008](specs/008-providers-and-jsonl.md)）——
  `pyxis.providers.openrouter_client()` 与 `openai_client()` 一行拿到
  已配好 sync + async 两路的 `InstructorClient`（未传 api_key 时自动读
  环境变量并给出带变量名的错误消息）。`Trace.to_jsonl(path)` 以 append
  模式把每条 `TraceRecord` 写成一行 JSON，`ensure_ascii=False` 让中文
  肉眼可读。examples/*.py 迁到工厂 API。
- **错误可见性**（[规格 009](specs/009-错误可见性.md)）——`@step` / `@astep`
  在 `client.complete` 抛任意异常时先写一条 `error` 非空的 `TraceRecord`
  （`output=None`），再重抛原异常（保留 traceback）。`TraceRecord.error`
  字段为 `str | None`；`Trace.errors()` 返回所有失败记录；`to_dict` /
  `to_json` / `to_jsonl` 一并支持 `error` 字段与 `output: None` 的序列化。
- **流式输出**（[规格 010](specs/010-流式输出.md)）——`Step.stream(...)` 与
  `AsyncStep.astream(...)` 按 schema 字段顺序逐步 yield partial 实例，
  让"schema 即思维链"变得肉眼可见。`Client` / `AsyncClient` 协议添加
  `stream` / `astream` 方法；`FakeClient` 模拟单帧流用于单测；
  `InstructorClient` 直连 instructor 的 `create_partial` 产出真实流。
- **观察者中间件 StepHook**（[规格 011](specs/011-hook.md)）——三个回调
  `on_start` / `on_end` / `on_error` 在每个 Step 的同步、异步、流式三条
  路径上统一触发。全局注册 `add_hook()` / `remove_hook()` / `clear_hooks()`；
  单个 hook 内的异常不影响其他 hook 与主流程，仅走 `warnings.warn` 提示。
  刻意做成**只读观察者**以守护"schema as workflow"哲学。
- **示例画廊**：新增 `examples/streaming_demo.py`（流式字段逐个填满）、
  `examples/plan_then_execute.py`（plan-then-execute + hook 打点），
  加上已有的 `research.py` 与 `agent_tool_use.py` 共四个典型 agent 模式。
- **对比文档**（[docs/对比.md](docs/对比.md)）——诚实地对比 pyxis 与
  LangGraph / DSPy：何时选 pyxis、何时该选别的、同一个"分析 + 规划"
  例子三种框架下的代码放一起看。

### 变更

- 所有既存的 README、CLAUDE.md、CHANGELOG、ROADMAP、规格 001–005、
  源码 docstring、示例 docstring 一次性重写为中文。Commit 历史按惯例
  不做破坏性重写。
- ruff 规则：禁用 `RUF001/002/003`（全角标点是中文写作里的正常形态）。

### 质量

- 133 个测试全绿：127 单元（零网络）+ 6 真实 LLM 烟雾（OpenRouter +
  `openai/gpt-5.4-nano`）。
- 11 份规格文档（001–011）落档；每份对应一次 commit。
- 新增语言规约测试：24 个关键文件（README、CLAUDE、CHANGELOG、ROADMAP、
  specs/*、src/pyxis/*）均被强制要求至少 100 个 CJK 字符。

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
