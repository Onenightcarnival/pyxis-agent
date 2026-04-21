# mcp-demo

一个 agent 同时注册**三种来源**的工具：

- **native `Tool`**：`Calculate`、`Finish`（本地 Python 类）。
- **stdio MCP server**：`word_count` / `reverse` / `upper` / `now`
  （子进程，JSON-RPC over 管道）。
- **Streamable HTTP MCP server**：`base64_encode` / `slugify` /
  `json_pretty`（独立 uvicorn 进程，JSON-RPC over HTTP，MCP 2024-11-05
  规范）。

三种来源在 agent loop 里写同一行：`decision.action.run()`。LLM 选到哪个
就跑哪个，来源无感。

前端两栏：

- 左边 Inventory：所有工具列出来，按来源上色（native 蓝、MCP 绿）。
  就是 LLM 看到的那张判别式联合。
- 右边 Step Cards：agent 每一步的 `thought → action（带来源徽章）→
  observation`。三种来源用同一种 card，只换徽章颜色。

内置的示例问法："把 `pyxis agent` 先用 `reverse` 反转，再用
`base64_encode` 编码。" 跑起来会产生
`reverse[stdio]` → `base64_encode[http]` → `finish[native]` 三步，前端
能看到各步的来源徽章。

## 换成你自己的 MCP server

demo 里两个 MCP server 都是 20 行的 `FastMCP` + `@mcp.tool()`——生产里
大概率也长这样。要接真的 server，改 `backend/app.py` 里 `MCPServer(...)`
声明的 `transport` 就行，前端一行不用动。`HttpMCP` 对齐了 MCP
2024-11-05 Streamable HTTP 规范，FastMCP 写的 server 直接能连。

## 技术栈

- 后端：FastAPI，启动时 `Popen` 起 HTTP MCP server +
  `async with mcp_toolset(...)` 嵌套两路。
- 前端：Vite + React + TS + Tailwind。

启动命令、完整工具清单、SSE 帧契约、设计对照表都在
[`apps/mcp-demo/README.md`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)。

源码：[`apps/mcp-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)
