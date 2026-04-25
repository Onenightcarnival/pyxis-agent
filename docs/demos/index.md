# Demos

`apps/` 目录下有两个前端示例：

| demo | 讲什么 |
|---|---|
| [chat-demo](chat-demo.md) | 同一份后端流，用 Chat 和 Inspect 两种方式展示 |
| [mcp-demo](mcp-demo.md)   | 本地 `Tool` 和 MCP 工具一起运行，界面展示工具来源和执行步骤 |

**环境**

- 都跑在 localhost
- 都要一个 `OPENROUTER_API_KEY`（或别的 OpenAI 兼容 key）
- 启动命令、架构图、数据契约见各自的 `apps/<name>/README.md`

**定位**

- 不随库打包
- `ruff` / `pytest` 默认跳过 `apps/`
- MIT License
