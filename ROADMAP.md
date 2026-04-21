# 路线图（Roadmap）

刻意**推迟**的功能列在这里，这样公共面不会被撑垮，迭代节奏也保得住。
每一项对应一个**未来的规格迭代**：想做的时候新建 `specs/NNN-*.md`
再进入 SDD+TDD 流程。

## 近期候选

- ~~**流式输出** —— 通过 instructor 的 partial streaming 逐 token 填充 schema~~
  （已于 [规格 010](specs/010-流式输出.md) 实现，提供 `Step.stream` /
  `AsyncStep.astream`；"流式 usage" 仍未做——instructor 在 partial
  路径下不稳定提供 usage，需要时单独加）。
- ~~**错误可见性** —— 重试耗尽时在 `TraceRecord` 上暴露验证错误~~
  （已于 [规格 009](specs/009-错误可见性.md) 实现）；**退避重试** 仍待做——
  目前 max_retries 直接转给 instructor，无指数退避；框架层的 retry
  helper 等有需求再加。
- ~~**`@tool` 装饰器糖** —— 从普通函数的签名 + docstring 自动生成 Tool 子类~~
  （已于 [规格 007](specs/007-tool-装饰器.md) 实现）。
- ~~**Provider 便捷工厂** —— `openrouter_client(api_key=...)`、
  `openai_client(...)` 返回就绪的 `InstructorClient`~~（已于
  [规格 008](specs/008-providers-and-jsonl.md) 实现；`anthropic_client`
  仍未做——instructor 对 Anthropic 的调用面不同，留到 v1.1）。
- **类型化 `@step` 重载** —— 一对 `@overload` 让 mypy / pyright 在调用处
  准确推断 `Step[T]` 或 `AsyncStep[T]`，不再落到 `Any`。

## 中期候选

- **成本估算** —— 可选的 per-model 费率表，把 Usage 换算到货币。
- **Trace 持久化** —— ~~JSONL sink 到文件~~（已于
  [规格 008](specs/008-providers-and-jsonl.md) 实现基础版 `Trace.to_jsonl`）；
  对接 **Langfuse** 已由其自己的 `from langfuse.openai import OpenAI`
  实现零侵入接入（见 [docs/concepts/observability.md](docs/concepts/observability.md)）；
  对接 log collector / OpenTelemetry 后端在框架层仍不做——走 Langfuse
  或用户自己写 `StepHook` 就够了。
- **并行 step 工具** —— `@flow` 的 fan-out/gather 工效糖，超越裸
  `asyncio.gather`。
- ~~**中间件 hook**~~（已于 [规格 011](specs/011-hook.md) 以**只读观察者**
  形式落地：`StepHook` + `add_hook` / `remove_hook` / `clear_hooks`；
  刻意不给 hook 留修改 messages / output 的能力）。
- **对话式记忆** —— 历史记录的 helper（仍只通过参数传入；不藏隐式状态）。
  （多轮对话已经可以用 human-in-the-loop 生成器 flow 直接写，
  [规格 012](specs/012-human-in-the-loop.md)；是否再加 helper 看需求。）
- **CLI** —— `pyxis run path/to/flow.py`，附带 env-file 支持、dry-run、
  trace-as-JSON 输出。
- **更多 `apps/` 示例应用**——已有：
  - `apps/chat-demo/`：带前端的多轮聊天，Chat / Inspect 双视图切换。
  - `apps/mcp-demo/`：native Tool + FastMCP 写的 stdio & Streamable HTTP
    两个 MCP server 混合注册的可视化（工具清单按 source 分组 + agent
    每一步的 thought / action / observation 带来源徽章）。

  两者都已通过 [规格 016](specs/016-文档与仓库的映射一致性.md) 挂进文档站
  **Demos** 一级 tab。未来候选：`apps/pr-review/`（代码审 agent）、
  `apps/research-assistant/`（多工具调研助手）。

## 故意不做

这些会违反核心哲学，**永远不要**加进来：

- flow 的图/DAG DSL。Python 已经能组合函数。
- YAML pipeline 配置。Python 已经能组合函数。
- 把 function-calling 协议适配烧进框架。输出 schema 本身就是接口；
  想用 provider 的 function-calling 就直接用 instructor。
- 隐藏的响应式状态或全局可变 agent context。显式传参。
- 把 agent loop 藏进框架的 helper。loop 是用户自己的 `@flow`。
- **对标 Claude Desktop / ChatGPT 的对话丝滑度**。pyxis 是 agent-for-machine
  阵营，LLM 直接输出是结构化 Pydantic（给代码消费），给人看的东西是
  应用层再拼出来的——天然就丝滑不过"LLM 直出文本"的原生 chat app。
  想做人机聊天流畅体验直接用 Anthropic SDK 的 native tool use。

## 怎么贡献一个迭代

1. 挑一个项目。开分支。
2. 写 `specs/NNN-<名字>.md`（≤ 40 行，含验收标准、不做）。
3. 先写失败的测试。
4. 写实现。
5. `uv run ruff format && uv run ruff check && uv run pytest`。
6. 动到 Client / Step / Flow 或 provider 连线，就跑
   `uv run --env-file .env pytest tests/integration/`。
7. 更新 `CLAUDE.md` 与文档站（公共面变了才要）。
8. 一次迭代一次 commit，正文引用规格编号。
