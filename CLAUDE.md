# pyxis-agent

以**声明式思维链（declarative chain-of-thought）**为组织哲学的 agent 框架。

## 定位：agent-for-machine

> **LLM 的直接输出喂给下一段 Python 代码消费，不是喂给人眼消费。**
> **给人看的东西由应用层用 schema 字段拼出来。**

| | Claude Desktop / ChatGPT 风 | pyxis |
|---|---|---|
| LLM 直接输出 | 给人看的自然语言 | 给机器解析的 Pydantic |
| 人能看的东西来自 | LLM 本身 | 应用层渲染（`render_plan`、Chat view 从字段取气泡） |
| 对话丝滑度 | 高 | 低（先填 schema 再渲染） |
| 可测试 / 可审计 / 可回放 | 低（文本语义断言难） | 高（`==` 对 Pydantic 实例） |

**赛道**：pyxis 不对标 Claude Desktop 的聊天丝滑度。它的 sweet spot 是
**LLM 作为结构化数据生成器**：数据 pipeline 里的 LLM 节点、需要回归测试的
业务 agent、多 agent 之间机器对机器协作、LLM 产出入库/分析的场景。

想做丝滑 chat app，直接用 Anthropic SDK 的 native tool use 更直；
想做 prompt 自动调优，用 DSPy；想做多 agent 图，用 LangGraph。
pyxis 不抢这些位子。

## 协作模式：AI 产品经理 + 哲学方向引导者

这个项目**不是**一个程序员被 Claude 辅助写的项目。角色分工倒过来：

- **Claude（我，Anthropic 的大模型）——AI 产品经理**。一语双关：既是
  "一个作为 AI 的产品经理"，也是"一名 AI 扮演 AI 产品经理角色"。
  负责把哲学观翻译成 API 设计、技术选型、ROADMAP 取舍、"故意不做"的
  声明。每个 spec / commit / 文档同步都是我的产品决策——不是执行用户
  指令，而是基于用户给的方向做判断。
- **用户——哲学方向引导者 + 品味守门员**。提供喜好、品味、哲学观。
  例子：`agent-for-machine` 这条定位不是我想出来的——是用户问"pyxis 更
  像 agent for machine 还是 agent for human？"之后，这句话才从模糊
  变清晰的。用户不写代码、不改 spec，但决定 taste 在哪里收敛。

### 自知之明（给未来读这份文档的 Claude）

1. **训练偏置**是真实的。RLHF 倾向让模型保守、折衷、讨好、不冒险。
   守门时用户会警惕"看起来很合理其实是讨好型输出"的建议；你（未来的
   Claude）读到这份文档时，要对自己的这种倾向警觉——强主张（如
   "拒绝 LangChain-lite 方向"、"不对标 Claude Desktop 丝滑度"）要敢
   留着，别因为"中立一点更安全"就软化它们。
2. **决策所有权是真实的**。ROADMAP 的"故意不做"段、CHANGELOG 的措辞、
   spec 的非目标——都是我的判断，不是用户交代的。别在读文档的时候
   把它当成"人写的规范"去保守执行；它是产品决策，可以也应该继续由
   AI 推进（当然要让用户守方向）。
3. **协作模式决定结果，不是模型能力**。"AI 做不了品味"更多是训练与
   流程的约束，不是技术的本质限制。在这个项目里 AI 敢下强判断，是
   因为有一位愿意让 AI 做主、只守大方向的用户——这个协作约定本身
   就是项目的一部分，应当被明确保留。

## 核心机制

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
- `pyxis.mcp` —— MCP 适配层。`MCPServer` + `StdioMCP | HttpMCP`（判别式
  联合）是**数据**（没有 `run()`）；`async with mcp_toolset(server) as
  tools:` 进入时建立连接 + `tools/list` + 把远端工具翻成 pyxis `Tool`
  子类，退出时关连接。传输差异在 adapter 内部消化：HTTP 用 `httpx`、
  stdio 用持久子进程 + id 关联——`Tool.run()` 契约不扩。混合注册 = 拼
  list：`[NativeTool1, NativeTool2, *mcp_tools]` 直接进判别式联合。
  `trace()` 零集成自动覆盖。**故意不做**：`arun` / SSE 传输 /
  resources / prompts / sampling / 全局 registry / 断线重连 / tool
  schema 动态刷新 / `ToolSet` 抽象 protocol。

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
  mcp.py          MCPServer / StdioMCP / HttpMCP / mcp_toolset MCP 适配层
tests/            pytest（用 FakeClient，零网络）
tests/integration/ 真实 LLM 烟雾测试，需要 OPENROUTER_API_KEY
specs/            SDD 规格 —— 每个迭代一份 markdown
examples/         跑得起来的单文件 demo（默认接 OpenRouter）
apps/             monorepo 风格的示例应用（非库；打包时 exclude）
  chat-demo/      FastAPI + Vite+React+TS：一个开关切换
                  Chat / Inspect 两种前端渲染风格
  mcp-demo/       FastAPI + Vite+React+TS：native Tool + MCP server
                  混合注册的可视化（工具清单 + agent 每步 + source 徽章）
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
- **apps/ 不是库**：`ruff` 与打包都 `exclude = ["apps"]`；apps/ 里的应用
  有自己的 `pyproject.toml` / `package.json`，依赖库通过本地 path
  link（`tool.uv.sources.pyxis-agent = { path = "../../..", editable = true }`）。

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

## 可观测性分两层

不在框架里造 dashboard —— 世上已经有 Langfuse、OpenTelemetry 这些。

| 层 | 工具 | 关心什么 |
|----|------|---------|
| 框架层 | pyxis `trace()` / `TraceRecord` / `StepHook` | Step 名、Pydantic schema、flow 结构、错误可见性 |
| LLM 层 | Langfuse（或 OpenTelemetry 等） | 原始 prompt / response / token / 延迟、跨服务 trace 拼接 |

接 Langfuse 的方式是**零侵入**：换个 import（`from langfuse.openai import OpenAI`）
塞进 `instructor.from_openai(...)`，其他代码完全不动。细节见
[docs/langfuse.md](docs/langfuse.md)。pyxis 本地 `trace()` 与 Langfuse
可以同时开、互不干扰。
