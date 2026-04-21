# 路线图（Roadmap）

- 刻意**推迟**的功能列在这里 —— 防止公共面被撑垮、迭代节奏被打乱
- 每项对应一次未来的规格迭代：新建 `specs/NNN-*.md` → SDD + TDD

## 近期候选

- ~~**流式输出**~~ [规格 010](specs/010-流式输出.md) 已实现（`Step.stream` / `AsyncStep.astream`）；"流式 usage" 未做（instructor 在 partial 路径下不稳定）
- ~~**错误可见性**~~ [规格 009](specs/009-错误可见性.md) 已实现；**退避重试** 仍待做（目前 `max_retries` 直转 instructor，无指数退避）
- ~~**`@tool` 装饰器糖**~~ [规格 007](specs/007-tool-装饰器.md) 已实现
- ~~**Provider 便捷工厂**~~ [规格 008](specs/008-providers-and-jsonl.md) 已实现；`anthropic_client` 未做（instructor 的 Anthropic 调用面不同，留到 v1.1）
- **类型化 `@step` 重载** — 让 mypy / pyright 在调用处准确推断 `Step[T]` / `AsyncStep[T]`，不再落到 `Any`

## 中期候选

- **成本估算** — 可选的 per-model 费率表，Usage 换算成货币
- **Trace 持久化** — ~~`Trace.to_jsonl`~~ 已于 [规格 008](specs/008-providers-and-jsonl.md) 落地；Langfuse 用 `from langfuse.openai import OpenAI` 零侵入（见 [observability](docs/concepts/observability.md)）；其他 log collector / OpenTelemetry 后端框架层不做（用 Langfuse 或自己写 `StepHook`）
- **并行 step 工具** — `@flow` 的 fan-out / gather 糖，超越裸 `asyncio.gather`
- ~~**中间件 hook**~~ [规格 011](specs/011-hook.md) 已以**只读观察者**形式落地（`StepHook` + `add_hook` / `remove_hook` / `clear_hooks`）；刻意不给 hook 改 messages / output 的能力
- **对话式记忆** — 历史记录 helper（仍只通过参数传，不藏隐式状态）；多轮对话已可用 [规格 012](specs/012-human-in-the-loop.md) 的生成器 flow 写，helper 再看需求
- **CLI** — `pyxis run path/to/flow.py`，支持 env-file / dry-run / trace-as-JSON
- **更多 `apps/` 示例应用**
    - ~~`chat-demo`~~：多轮聊天 + Chat / Inspect 双视图
    - ~~`mcp-demo`~~：native Tool + stdio/HTTP MCP 混合注册的可视化
    - 两者已通过 [规格 016](specs/016-文档与仓库的映射一致性.md) 挂进 **Demos** tab
    - 候选：`pr-review`（代码审）、`research-assistant`（多工具调研）

## 故意不做

违反核心哲学，**永远不加**：

- **图 / DAG DSL、YAML pipeline 配置** — Python 已经能组合函数
- **function-calling 协议适配层** — 输出 schema 就是接口；要用 provider 的 function-calling 直接用 instructor
- **响应式状态 / 全局可变 agent context** — 显式传参
- **内置 agent loop helper** — loop 是用户自己的 `@flow`
- **对标 Claude Desktop / ChatGPT 的对话丝滑度** — pyxis 是 agent-for-machine，LLM 直出 Pydantic 给代码用，给人看的由应用层拼，天然慢过"LLM 直出文本"的原生 chat app；要聊天顺滑用 Anthropic SDK 原生 tool use

## 怎么贡献一个迭代

1. 挑一项 → 开分支
2. 写 `specs/NNN-<名字>.md`（≤ 40 行，含验收 + 不做）
3. 先写失败的测试
4. 写实现
5. `uv run ruff format && uv run ruff check && uv run pytest`
6. 动到 Client / Step / Flow / provider 连线 → 跑
   `uv run --env-file .env pytest tests/integration/`
7. 公共面变了 → 同步 `CLAUDE.md` + 文档站
8. 一次迭代 = 一次 commit，正文引用规格编号
