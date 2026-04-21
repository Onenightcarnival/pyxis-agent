# mcp-demo —— MCP + native Tool 混合注册的可视化 demo

用 pyxis 搭一个 agent，**同时注册三种来源的工具**：

- **native `Tool`**：`Calculate`、`Finish`。
- **stdio MCP server**（`mcp_server.py`）：`word_count` / `reverse` /
  `upper` / `now`。本地子进程、JSON-RPC over 管道。
- **Streamable HTTP MCP server**（`mcp_http_server.py`）：`base64_encode` /
  `slugify` / `json_pretty`。独立的 uvicorn 进程，JSON-RPC over HTTP。

两条 MCP 传输**并排跑**，证明 `pyxis.mcp` 的 `StdioMCP` / `HttpMCP`
在 `Tool.run()` 调用面完全对称——agent loop 一行 `d.action.run()`，
对三种来源全都无感。前端把两件事可视化：

1. **左侧 Inventory**——所有工具扁平列出，用色彩区分来源
   （native 蓝、MCP 绿）。这就是 LLM 看到的那张**判别式联合**。
2. **右侧 Step Cards**——agent loop 的每一步：`thought` → `action`（带
   来源徽章） → `observation`。同一套 card 形态，native / MCP 无差别渲染，
   呼应 pyxis 设计点：agent loop 里 `d.action.run()` 一行，不做来源分派。

换句话说：**这两个面板就是 pyxis MCP 集成的两个核心事实的可视化：**
工具来源被标注（可审计），但调用面统一（简洁）。

## 架构

```
apps/mcp-demo/
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── mcp_server.py       零依赖的 stdio MCP server（子进程）
│   ├── mcp_http_server.py  FastAPI 版 HTTP MCP server（独立 uvicorn，:3003）
│   └── app.py              FastAPI，启动时 Popen http server +
│                           async with 两个 mcp_toolset；POST /run 流式推帧
└── frontend/               Vite + React + TypeScript + Tailwind
    ├── package.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx         左侧 inventory + 右侧 step 流 + 输入框
        ├── types.ts        ToolDescriptor / AgentStep / SseFrame
        ├── sse.ts          fetchInventory + streamRun
        ├── index.css       step-enter / source-pulse 等动画
        └── components/
            ├── Inventory.tsx    工具清单（按 source 分组）
            ├── StepCard.tsx     单次 agent 迭代的卡片
            └── SourceBadge.tsx  native / mcp 色彩约定
```

SSE 帧契约（每帧一行 JSON）：

```json
{"kind": "inventory", "tools": [{"name": "calculate", "source": "native", ...}, {"name": "reverse", "source": "mcp:stdio-demo", ...}, {"name": "base64_encode", "source": "mcp:http-demo", ...}]}
{"kind": "step", "index": 0, "thought": "...", "action": {"name": "reverse", "args": {"text": "..."}, "source": "mcp:stdio-demo"}, "observation": "..."}
{"kind": "step", "index": 1, "thought": "...", "action": {"name": "base64_encode", "args": {"text": "..."}, "source": "mcp:http-demo"}, "observation": "..."}
{"kind": "step", "index": 2, "thought": "...", "action": {"name": "finish", "args": {...}, "source": "native"}, "observation": "..."}
{"kind": "done", "answer": "..."}
```

## 跑起来

两个终端：

```bash
# 后端（3002 端口）
cd apps/mcp-demo/backend
cp .env.example .env   # 填你的 OPENROUTER_API_KEY
uv sync
uv run --env-file .env uvicorn app:app --reload --port 3002

# 前端（5174 端口）
cd apps/mcp-demo/frontend
pnpm install   # 或 npm install
pnpm dev
```

打开 http://localhost:5174，点"跑一次"。

## 工具清单（本 demo）

| name | source | 描述 |
|---|---|---|
| `calculate` | native | 算术表达式求值 |
| `finish` | native | 终止 agent 并给出答案 |
| `word_count` | mcp:stdio-demo | 数单词数 |
| `reverse` | mcp:stdio-demo | 反转字符串 |
| `upper` | mcp:stdio-demo | 转大写 |
| `now` | mcp:stdio-demo | 当前 ISO 时间 |
| `base64_encode` | mcp:http-demo | base64 编码 |
| `slugify` | mcp:http-demo | 文本转 URL slug |
| `json_pretty` | mcp:http-demo | JSON 美化 |

一个能同时跑过三个来源的好问题：

> 把 "pyxis agent" 先用 reverse 工具反转，再用 base64_encode 工具编码，返回编码结果。

实测会产生三步链：`reverse[stdio-demo]` → `base64_encode[http-demo]` →
`finish[native]`。三种传输、一条 agent loop，前端看到同一种卡片、只是
badge 换颜色。

## 换成真 MCP server

`backend/app.py` 里有两个声明：

```python
stdio_server = MCPServer(
    name="stdio-demo",
    transport=StdioMCP(command=sys.executable, args=[str(MCP_STDIO_SCRIPT)]),
)
http_server = MCPServer(
    name="http-demo",
    transport=HttpMCP(url=HTTP_MCP_URL),
)
```

把 `transport` 指到真 server 的启动命令 / URL 即可：

- stdio：`StdioMCP(command="uvx", args=["mcp-server-filesystem", "/tmp"])`
- HTTP：`HttpMCP(url="https://your.mcp.example.com/mcp", headers={"Authorization": "..."})`

前端代码**一行都不用改**。pyxis 的 MCP adapter 把传输差异吸收在内部，
应用层只管拿到 `list[type[Tool]]`。

## 设计对照

| 设计点 | 代码里的体现 |
|---|---|
| MCP server 是数据不是行为 | `MCPServer` 是 Pydantic 模型，没有 `run()` |
| 工具来源被 adapter 吸收 | `app.py` 里对 native / stdio-MCP / http-MCP 是同一行 `d.action.run()` |
| 传输生命周期绑 `async with` | `_lifespan()` 里 `async with mcp_toolset(stdio), mcp_toolset(http)` 嵌套 |
| 混合注册 = 拼 list | `tool_classes = [*NATIVE_TOOLS, *stdio_tools, *http_tools]` |
| 选择由 LLM 做 | 判别式联合 + `kind` 字段，框架不做路由 |
