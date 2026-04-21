# mcp-demo

一个 agent，同时注册**三种来源**的工具，让 LLM 在一次 loop 里无感调度：

- **native `Tool`**：`Calculate`、`Finish`（本地 Python 类，`run()` 即代码）。
- **stdio MCP server**：`word_count` / `reverse` / `upper` / `now`。
  本地子进程、JSON-RPC over 管道。
- **Streamable HTTP MCP server**：`base64_encode` / `slugify` /
  `json_pretty`。独立 uvicorn 进程，JSON-RPC over HTTP，对齐
  **MCP 2024-11-05 Streamable HTTP** 规范。

两种 MCP 传输**并排跑**，证明 `pyxis.mcp` 的 `StdioMCP` / `HttpMCP` 在
`Tool.run()` 调用面上完全对称——agent loop 里只有一行
`decision.action.run()`，对三种来源全无感。

## 为什么这个 demo 值得看

前端把[`pyxis.mcp`](../concepts/mcp.md) 的两个核心事实画出来：

1. **左侧 Inventory**：所有工具扁平列出，按 source 用色彩区分
   （native 蓝、MCP 绿）。这就是 LLM 看到的**判别式联合**在 UI 里的样子。
2. **右侧 Step Cards**：agent loop 每一步 `thought → action（带来源徽章）→
   observation`。三种来源用**同一套 card**，只换徽章颜色——
   呼应框架设计点：**工具来源被 adapter 吸收，调用面统一**。

换一种说法：**可审计（徽章看得见）+ 简洁（代码里一行就调完）**
这两件事在同一个屏幕上被同时演示。

## 一个能穿过三种来源的好问题

内置的示例问法：

> 把 "pyxis agent" 先用 reverse 工具反转，再用 base64_encode 工具编码，
> 返回编码结果。

产生的步骤链：
`reverse[stdio-demo]` → `base64_encode[http-demo]` → `finish[native]`。
三种传输、一条 agent loop，前端看到同一种卡片，只是 badge 换颜色。

## 技术形态

- **后端**：FastAPI，启动时 `Popen` 起 HTTP MCP server，
  `async with mcp_toolset(...)` 嵌套两路 MCP 连接；
  `POST /run` SSE 端点流式推帧。
- **两个 MCP server** 各 20 行左右的 `FastMCP` + `@mcp.tool()`——
  这就是你生产里会写的形态。想换成**别人发布的 MCP server**
  （stdio 版本跑成子进程、HTTP 版本是个 URL），只改 `app.py` 里的
  `MCPServer` 声明即可，前端一行都不用动。
- **前端**：Vite + React + TypeScript + Tailwind，inventory + step 流
  两栏布局。

## 跑起来 & 完整说明

工具清单、SSE 帧契约、"换成你自己的 MCP server" 替换指引、
设计对照表，都在
[`apps/mcp-demo/README.md`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)。

源码：[`apps/mcp-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/mcp-demo)
