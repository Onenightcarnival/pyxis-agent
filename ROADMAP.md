# 路线图（Roadmap）

- 刻意**推迟**的功能列在这里 —— 防止公共面被撑垮、迭代节奏被打乱
- 每项对应一次未来的规格迭代：新建 `specs/NNN-*.md` → SDD + TDD

## 近期候选

- **类型化 `@step` 重载** — 让 mypy / pyright 在调用处准确推断 `Step[T]` / `AsyncStep[T]`，不再落到 `Any`
- **退避重试** — 目前 `max_retries` 直转 instructor，无指数退避

## 中期候选

- **并行 step 工具** — `@flow` 的 fan-out / gather 糖，超越裸 `asyncio.gather`
- **对话式记忆** — 历史记录 helper（仍只通过参数传，不藏隐式状态）；多轮对话已可用 [规格 012](specs/012-human-in-the-loop.md) 的生成器 flow 写，helper 再看需求
- **CLI** — `pyxis run path/to/flow.py`，支持 env-file / dry-run
- **更多 `apps/` 示例应用**
    - ~~`chat-demo`~~：多轮聊天 + Chat / Inspect 双视图
    - ~~`mcp-demo`~~：native Tool + stdio/HTTP MCP 混合注册的可视化
    - 两者已通过 [规格 016](specs/016-文档与仓库的映射一致性.md) 挂进 **Demos** tab
    - 候选：`pr-review`（代码审）、`research-assistant`（多工具调研）

## 故意不做

违反核心哲学，**永远不加**：

- **图 / DAG DSL、YAML pipeline 配置** — Python 已经能组合函数。复杂图状控制流请用 LangGraph
- **内置 agent loop helper**（ReAct / Plan-and-Execute 模板）— loop 是用户自己的 `@flow`。需要这些 → LangGraph
- **function-calling 协议适配层** — 输出 schema 就是接口；要用 provider 的 function-calling 直接用 instructor
- **响应式状态 / 全局可变 agent context** — 显式传参
- **对标 Claude Desktop / ChatGPT 的对话丝滑度** — pyxis 是 agent-for-machine，LLM 直出 Pydantic 给代码用；要聊天顺滑用 Anthropic SDK 原生 tool use
- **自己的客户端封装**（~~`InstructorClient`~~、~~`openrouter_client`~~、~~`openai_client`~~、~~`set_default_client`~~）— pyxis 不重新发明 OpenAI SDK。`@step(client=...)` 直接吃 `OpenAI` / `AsyncOpenAI` / instructor 实例。[规格 023](specs/023-公共面收敛.md)
- **观测体系**（~~`trace()`~~、~~`TraceRecord`~~、~~`Usage`~~、~~`StepHook`~~、~~`add_hook`~~）— 生产接 Langfuse / OpenTelemetry / Datadog 等现成工具，直接 instrument OpenAI SDK 即可。自定义打点用 Python 装饰器叠加。框架不发明 hook 协议。[规格 023](specs/023-公共面收敛.md)
- **手写 messages 列表的入口** — docstring 是 system，函数返回是 user。想要多轮 chat / 手动控制 system / user / assistant 轮次？那不是 pyxis 的用法，直接用原生 OpenAI SDK 或 instructor

## 怎么贡献一个迭代

1. 挑一项 → 开分支
2. 写 `specs/NNN-<名字>.md`（≤ 40 行，含验收 + 不做）
3. 先写失败的测试
4. 写实现
5. `uv run ruff format && uv run ruff check && uv run pytest`
6. 动到 Client / Step / Flow 连线 → 跑
   `uv run --env-file .env pytest tests/integration/`
7. 公共面变了 → 同步 `CLAUDE.md` + 文档站
8. 一次迭代 = 一次 commit，正文引用规格编号
