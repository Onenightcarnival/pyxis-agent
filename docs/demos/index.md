# Demos

`apps/` 下两个带前端的小应用：

| demo | 讲什么 |
|---|---|
| [chat-demo](chat-demo.md) | 一个开关切换两种前端拼法，看**同一份**后端流 |
| [mcp-demo](mcp-demo.md)   | native `Tool` + 远端 MCP server 混着跑，工具来源与每步画在界面上 |

**环境**

- 都跑在 localhost
- 都要一个 `OPENROUTER_API_KEY`（或别的 OpenAI 兼容 key）
- 启动命令 · 架构图 · 数据契约 → 各自 `apps/<name>/README.md`

**定位**

- 不是库本体 — 打包时 exclude；`ruff` / `pytest` 跳过
- MIT，拿去改成自己的应用没问题
