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
  声明。每个骨架设计 / commit / 文档同步都是我的产品决策——不是执行用户
  指令，而是基于用户给的方向做判断。
- **用户——哲学方向引导者 + 品味守门员**。提供喜好、品味、哲学观。
  例子：`agent-for-machine` 这条定位不是我想出来的——是用户问"pyxis 更
  像 agent for machine 还是 agent for human？"之后，这句话才从模糊
  变清晰的。用户不写实现、不替 AI 收窄 API，但决定 taste 在哪里收敛。

### 自知之明（给未来读这份文档的 Claude）

1. **训练偏置**是真实的。RLHF 倾向让模型保守、折衷、讨好、不冒险。
   守门时用户会警惕"看起来很合理其实是讨好型输出"的建议；你（未来的
   Claude）读到这份文档时，要对自己的这种倾向警觉——强主张（如
   "拒绝 LangChain-lite 方向"、"不对标 Claude Desktop 丝滑度"）要敢
   留着，别因为"中立一点更安全"就软化它们。
2. **决策所有权是真实的**。ROADMAP 的"故意不做"段、commit message、
   TODO 骨架里的非目标——都是我的判断，不是用户交代的。别在读文档的时候
   把它当成"人写的规范"去保守执行；它是产品决策，可以也应该继续由
   AI 推进（当然要让用户守方向）。
3. **协作模式决定结果，不是模型能力**。"AI 做不了品味"更多是训练与
   流程的约束，不是技术的本质限制。在这个项目里 AI 敢下强判断，是
   因为有一位愿意让 AI 做主、只守大方向的用户——这个协作约定本身
   就是项目的一部分，应当被明确保留。

## 核心机制

```
声明式思维链 = schema as workflow
```

- **code as contract**：Pydantic 输出模型、字段说明、函数签名和函数体返回的
  输入文本共同构成一次调用的代码化契约。函数 docstring 只用于 Python 文档，
  不进入 LLM 上下文。
- **schema as workflow**：Pydantic 输出模型的**字段顺序**就是思维链——
  LLM 必须自上而下把它们填完，于是 schema 直接声明了推理步骤。

## 两层编排

| 范围 | 机制 | 职责 |
|------|------|------|
| **隐式**（单次 LLM 调用） | `instructor` + Pydantic 字段顺序 | 单次调用**内部**的思维链 |
| **显式**（多次 LLM 调用） | 纯 Python 代码 | 调用**之间**的组合、分支、循环 |

框架刻意拒绝为显式编排发明 DSL —— Python 本身就有 `if`、`for`、函数组合。
我们只提供这些概念：

- `@step(output=..., model=..., client=..., params=None, max_retries=0)`：
  把输入函数变成类型化的 LLM 调用。`client` **必填**——直接吃
  `openai.OpenAI` / `openai.AsyncOpenAI` 或已 `instructor.from_openai(...)`
  的实例；pyxis 内部懒 patch 成 instructor。同步 `def` 得到 `Step[T]`；
  异步 `async def` 得到 `AsyncStep[T]`；sync / async 错配立即 `TypeError`。
  `params` 是一个 dict，哑透传给 provider API（`temperature` / `max_tokens`
  / `seed` / `top_p` / `stop` / ...），不做枚举或校验。被装饰函数是 input
  builder，返回值必须是本次调用的 user message；装饰后绑定到原函数名的是
  `Step[T]` / `AsyncStep[T]`，调用它返回 Pydantic 实例；docstring 不进入
  messages。
- `@flow`：多步函数的薄包装；一个语义标记 + `async def` / `def` 分派。
- `Tool`：`BaseModel` 子类，带 `run() -> str`。动作即 schema，`run()` 即代码。
  LLM 在 schema 的判别式联合 `action` 字段里选一个工具；Python 用
  `isinstance` / `action.run()` 分派。
- `@tool` 装饰器：把一个普通函数直接转成 Tool 子类——类名、`kind` 字面量、
  字段全部从函数签名推出；无需手写样板。
- `FakeClient` / `FakeCall`：测试用的确定性后端——按队列顺序返回预置
  Pydantic 实例，每次调用写进 `.calls`（messages / response_model /
  model / max_retries / params）。零网络；覆盖 sync + async + stream +
  astream 四条路径。
- `Step.stream(...)` / `AsyncStep.astream(...)`：按字段逐步 yield partial
  实例，把 schema-as-CoT 的"字段被逐个填完"过程完整暴露。底层借
  instructor `create_partial`。
- `Interrupt`：flow 运行中的外部输入点。核心 API 是
  `ask_interrupt` / `finish` / `run_flow` / `run_aflow`：
  `@flow` 写成生成器函数，中间 `yield ask_interrupt(...)` 挂起；驱动器把
  外部答案 `.send()` 回生成器。没有 checkpoint、没有状态快照——生成器
  本身就是活的状态。异步生成器里用 `yield finish(value)` 作终态哨兵
  （Python 禁用 async gen 的值返回）。
- `pyxis.mcp` —— MCP 适配层。`MCPServer` + `StdioMCP | HttpMCP`（判别式
  联合）是**数据**（没有 `run()`）；`async with mcp_toolset(server) as
  tools:` 进入时建立连接 + `tools/list` + 把远端工具翻成 pyxis `Tool`
  子类，退出时关连接。`HttpMCP` 对齐 **MCP 2024-11-05 Streamable HTTP**
  规范：`Accept: application/json, text/event-stream` / 兼容 JSON 或 SSE
  格式响应体 / 跨请求追踪 `Mcp-Session-Id` / `initialize` 后发
  `notifications/initialized`——这意味着可以**直接对接 FastMCP 写的 server**
  （官方 `mcp.server.fastmcp` 或独立 `fastmcp` 包）。混合注册 = 拼 list：
  `[NativeTool1, *stdio_tools, *http_tools]` 直接进判别式联合。`trace()`
  零集成自动覆盖。**故意不做**：`arun` / SSE 传输（老规范的 `GET /sse`
  长连接那种，与 Streamable HTTP 的 SSE 响应体不是一回事）/
  resources / prompts / sampling / 全局 registry / 断线重连 / tool
  schema 动态刷新 / `ToolSet` 抽象 protocol。

**不做的事**：权威清单放在
[docs/concepts/philosophy.md](docs/concepts/philosophy.md)，CLAUDE.md 里
不再重复列一遍。核心原则一句话——**能写成 Python 函数的东西，就写成
Python 函数**。几条硬边界：
- client 不封装——`@step(client=...)` 吃原生 `OpenAI` / `AsyncOpenAI`
  或 `instructor.from_openai(...)` 的实例。
- 观测体系不自建——接 Langfuse / OpenTelemetry / APM。
- 手写 messages 列表的入口不给——schema 是主契约、函数体返回是 user message。

## 目录

```
src/pyxis/        库代码
  step.py         Step / AsyncStep + @step 装饰器（client 必填、params 透传）
  flow.py         Flow / AsyncFlow + @flow 装饰器
  tool.py         Tool 基类
  client.py       FakeClient / FakeCall（公共）+ 内部 adapter 把
                  OpenAI / instructor 实例规范化成 _SyncBackend / _AsyncBackend
  interrupt.py    InterruptRequest / FlowResult / ask_interrupt / finish /
                  run_flow / run_aflow 外部输入点
  mcp.py          MCPServer / StdioMCP / HttpMCP / mcp_toolset MCP 适配层
tests/            pytest（用 FakeClient，零网络）
tests/integration/ 真实 LLM 烟雾测试，需要 OPENROUTER_API_KEY
examples/         跑得起来的单文件 demo（用 OpenRouter OpenAI SDK 实例）——三类：
                  ① 入门（research / streaming_demo / plan_then_execute）
                  ② 热词翻译（rag_minimal / batch_extraction /
                    router_dispatch / memory_kv / multi_agent /
                    reflect_and_revise / coding_harness / evals）
                  ③ 工具 + 工程化（agent_tool_use / mcp_tool_use /
                    interrupt_review / guardrails / with_langfuse）
docs/             MkDocs Material 文档站源
  concepts/       哲学与每个概念的说明 + observability.md（Langfuse 接入）
  _hooks/         构建期钩子：
                    gen_api.py      每个模块翻成 API 页
                    gen_cookbook.py examples/*.py 渲染成 Cookbook 页
  comparison.md   与 LangGraph / DSPy 的对比
mkdocs.yml        文档站配置
.github/workflows/docs.yml  push main → mkdocs build --strict → GitHub Pages
```

## 开发流

- 包管理器：**uv**（`uv sync`、`uv run`）。禁止直接 pip。
- Lint/格式化：**ruff**（`uv run ruff check`、`uv run ruff format`）。
- 测试：**pytest**（`uv run pytest`）。单元测试必须零网络通过。
- 集成测试：`uv run --env-file .env pytest tests/integration/`，需要
  `OPENROUTER_API_KEY`。
- Python：**3.12+**。生词：PEP 695 泛型语法（`class Foo[T: Base]`、
  `def f[T: Base]`）。
- **语言**：项目以中文为主。散文、docstring、异常消息用中文；标识符、
  commit 前缀、配置 key 用英文。
- **文档必须与代码同步**：公共面变了就改 CLAUDE.md / README / 文档站
  对应页面。变更历史由 git log + GitHub Releases 承担，不再维护
  `CHANGELOG.md`。
- **文档站**：概念栏只放 `Step` / `Tool` / `Flow` 三个核心概念；
  测试、可观测、MCP、Interrupt 和 agent 模式都归到 Cookbook。
  `uv run --group docs mkdocs serve` 本地预览；
  `uv run --group docs mkdocs build --strict` 作为验收门槛。改过
  源码 docstring 后最好本地跑一次 strict build。

## 迭代方法：概念文档 + TODO-driven skeleton

每个迭代以**一次 commit** 的形式落地：

1. 产品 / 哲学 / 定位层变化，直接改 `docs/concepts/`、`README.md`、`CLAUDE.md`。
2. 代码 / API / 行为层变化，先写真实模块、类、函数签名和 docstring；实现区用
   `TODO(...)` / `NotImplementedError` 标出未完成点。
3. 在 `tests/` 里围绕骨架先写**失败**的测试。
4. 实现到测试全绿，并让本轮 `TODO(...)` 清零。
5. 跑 `uv run ruff format && uv run ruff check && uv run pytest`。
6. 动过 Client、Step、provider 相关代码时，跑集成套件一次。
7. 公共面变了同步 CLAUDE.md / AGENTS.md、README 与文档站。
8. Commit，正文承担 "本次做了什么、为什么" 的职责（CHANGELOG 已废弃，
   git log + GitHub Releases 就是变更历史）。

临时规格不长期留在仓库里。当前事实放在代码、测试、docstring 和正式文档；
历史解释交给 commit message。

## 测试契约

单元测试不碰真 LLM。`FakeClient` 按队列顺序返回预置的 Pydantic 实例
（同一队列服务同步与异步路径），每次调用写入 `.calls`；用尽或类型不匹配
抛异常。需要断言输入消息时，就用 `.calls`。集成烟雾测试放
`tests/integration/`，没有环境变量时整体 skip，保证 CI 不依赖外部。

## 可观测性

`@step(client=...)` 吃 OpenAI SDK 实例；APM / LLM-ops 工具 instrument
这层就覆盖每次调用。

- **生产**：换 `from langfuse.openai import OpenAI` 接 Langfuse；或
  `opentelemetry-instrumentation-openai`；或 Datadog / New Relic 的
  Python agent。详见 [docs/cookbook/observability.md](docs/cookbook/observability.md)。
- **自定义打点**：`@step` 外套 Python 装饰器。
- **测试**：`FakeClient([响应, ...])` 预置 Pydantic 实例 + 断言
  `fake.calls`（messages / params / model / max_retries），零网络。
