# Demos

`apps/` 下两个带前端的小应用。各自讲一件事：

| demo | 讲什么 |
|---|---|
| [chat-demo](chat-demo.md) | 一个开关切换两种前端拼法，看**同一份**后端流。 |
| [mcp-demo](mcp-demo.md)   | 本地 `Tool` + 远端 MCP server 混着跑，工具来源和 agent 每一步画在界面上。 |

两个都要一个 `OPENROUTER_API_KEY`（或别的 OpenAI 兼容 key），都跑在
localhost。启动命令、架构图、数据契约都在各自的 `apps/<name>/README.md`
里，这里只负责帮你决定要不要点进去。

`apps/` 不是库的一部分——打包时被 exclude，`ruff` / `pytest` 也跳过。
拿去改成自己的应用没问题，MIT。
