# mcp-demo

这个 demo 注册三类工具：

| 来源 | 工具 | 传输 |
|---|---|---|
| **native `Tool`**               | `Calculate` · `Finish`                          | 本地 Python 类 |
| **stdio MCP server**            | `word_count` · `reverse` · `upper` · `now`      | 子进程，JSON-RPC over 管道 |
| **Streamable HTTP MCP server**  | `base64_encode` · `slugify` · `json_pretty`     | 独立 uvicorn，JSON-RPC over HTTP，MCP 2024-11-05 |

agent loop 统一调用 `decision.action.run()`，工具来源只影响界面上的徽章。

## 前端两栏

- **左侧 Inventory**：列出所有工具，并按来源上色
- **右侧 Step Cards**：展示每步 `thought`、`action`、`observation`

## 示例问法

> 把 `pyxis agent` 先用 `reverse` 反转，再用 `base64_encode` 编码。

步骤链：`reverse[stdio]`、`base64_encode[http]`、`finish[native]`。

## 换成你自己的 MCP server

- demo 里的两个 server 都用 `FastMCP` + `@mcp.tool()` 定义
- 接真实 server 时，改 `backend/app.py` 里的 `MCPServer(...)` transport
- `HttpMCP` 使用 MCP 2024-11-05 Streamable HTTP 规范，可连接 FastMCP server

## 技术栈

- 后端：FastAPI，启动时用 `Popen` 起 HTTP MCP server，并用 `mcp_toolset(...)` 连接两路 MCP
- 前端：Vite + React + TS + Tailwind

## 相关

- 启动命令、工具清单、SSE 帧契约、设计对照表：[`apps/mcp-demo/README.md`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)
- 源码：[`apps/mcp-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)
