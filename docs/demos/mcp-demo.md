# mcp-demo

一个 agent 同时注册**三种来源**的工具：

| 来源 | 工具 | 传输 |
|---|---|---|
| **native `Tool`**               | `Calculate` · `Finish`                          | 本地 Python 类 |
| **stdio MCP server**            | `word_count` · `reverse` · `upper` · `now`      | 子进程，JSON-RPC over 管道 |
| **Streamable HTTP MCP server**  | `base64_encode` · `slugify` · `json_pretty`     | 独立 uvicorn，JSON-RPC over HTTP，MCP 2024-11-05 |

三种来源在 agent loop 里写同一行：`decision.action.run()`。LLM 选谁跑谁，来源无感。

## 前端两栏

- **左 Inventory** — 所有工具列出，按来源上色（native 蓝、MCP 绿）；就是 LLM 看到的那张判别式联合
- **右 Step Cards** — 每步 `thought → action（带来源徽章）→ observation`；三种来源同一种 card，只换徽章颜色

## 示例问法

> 把 `pyxis agent` 先用 `reverse` 反转，再用 `base64_encode` 编码。

步骤链：`reverse[stdio]` → `base64_encode[http]` → `finish[native]`。

## 换成你自己的 MCP server

- demo 里两个 server 都是 20 行的 `FastMCP` + `@mcp.tool()` — 生产里大概率也长这样
- 要接真 server → 改 `backend/app.py` 里 `MCPServer(...)` 的 `transport`，前端一行不动
- `HttpMCP` 对齐 MCP 2024-11-05 Streamable HTTP 规范 → FastMCP 写的 server 直接能连

## 技术栈

- 后端：FastAPI，启动时 `Popen` 起 HTTP MCP server + `async with mcp_toolset(...)` 嵌套两路
- 前端：Vite + React + TS + Tailwind

## 相关

- 启动命令 / 完整工具清单 / SSE 帧契约 / 设计对照表 → [`apps/mcp-demo/README.md`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)
- 源码 → [`apps/mcp-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)
