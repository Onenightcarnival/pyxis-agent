# 路线图（Roadmap）

- 刻意**推迟**的功能列在这里 —— 防止公共面被撑垮、迭代节奏被打乱
- 每项对应一次未来的骨架迭代：先落真实 API 骨架、docstring、失败测试和
  `TODO(...)`，再实现到测试全绿并清空本轮 TODO

## 近期候选

- **类型化 `@step` 重载** — 让 mypy / pyright 在调用处准确推断 `Step[T]` / `AsyncStep[T]`，不再落到 `Any`
- **退避重试** — 目前 `max_retries` 直转 instructor，无指数退避

## 中期候选

- **并行 step 工具** — 可选的 fan-out / gather helper；默认仍推荐裸 `asyncio.gather`
- **对话式记忆** — 历史记录 helper（仍只通过参数传，不藏隐式状态）；多轮对话已可用生成器流程写，helper 再看需求
- **CLI** — `pyxis run path/to/script.py`，支持 env-file / dry-run

## 故意不做

违反核心哲学，**永远不加**：

- **图 / DAG DSL、YAML pipeline 配置** — Python 已经能组合函数。图状控制流用 LangGraph
- **内置 agent loop helper**（ReAct / Plan-and-Execute 模板）— loop 是用户自己的普通 Python 函数；要模板走 LangGraph
- **function-calling 协议适配层** — 输出 schema 就是接口；要用 provider 的 function-calling 直接用 instructor
- **响应式状态 / 全局可变 agent context** — 显式传参
- **对标 Claude Desktop / ChatGPT 的对话丝滑度** — pyxis 是 agent-for-machine，LLM 直出 Pydantic 给代码用；要聊天顺滑用 Anthropic SDK 原生 tool use
- **客户端封装**（~~`InstructorClient`~~、~~`openrouter_client`~~、~~`openai_client`~~、~~`set_default_client`~~）— `@step(client=...)` 吃 `OpenAI` / `AsyncOpenAI` / instructor 实例
- **观测体系**（~~`trace()`~~、~~`TraceRecord`~~、~~`Usage`~~、~~`StepHook`~~、~~`add_hook`~~）— 接 Langfuse / OpenTelemetry / Datadog，instrument OpenAI SDK 层；自定义打点用 Python 装饰器叠加
- **手写 messages 列表的入口** — schema 是主契约、函数体返回是 user message；多轮 chat / assistant 轮次控制直接用 OpenAI SDK

## 怎么贡献一个迭代

1. 挑一项 → 开分支
2. 产品 / 哲学 / 定位层变化 → 直接改 `docs/concepts/`、`README.md`、`CLAUDE.md`
3. 代码 / API / 行为层变化 → 先建真实文件、类、函数签名和 docstring，在实现区留下 `TODO(...)` / `NotImplementedError`
4. 先写失败的测试
5. 写实现，直到本轮 `TODO(...)` 清零
6. `uv run ruff format && uv run ruff check && uv run pytest`
7. 动到 Client / Step / provider 连线 → 跑
   `uv run --env-file .env pytest tests/integration/`

8. 公共面变了 → 同步 `CLAUDE.md` / `AGENTS.md` + 文档站
9. 一次迭代 = 一次 commit，正文解释本次做了什么、为什么
