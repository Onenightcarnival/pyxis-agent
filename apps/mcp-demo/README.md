# mcp-demo —— MCP + native Tool 混合注册的可视化 demo

用 pyxis 搭一个 agent，**同时注册** native `Tool`（`Calculate`、`Finish`）
和从一个本地 stdio MCP server 发现出来的工具（`word_count` / `reverse` /
`upper` / `now`）。前端把两件事可视化：

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
│   ├── mcp_server.py       零依赖的 stdio MCP server（demo 用）
│   └── app.py              FastAPI，启动时连 MCP，POST /run 流式推帧
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
{"kind": "inventory", "tools": [{"name": "calculate", "source": "native", ...}, ...]}
{"kind": "step", "index": 0, "thought": "...", "action": {"name": "reverse", "args": {"text": "..."}, "source": "mcp:demo"}, "observation": "..."}
{"kind": "step", "index": 1, "thought": "...", "action": {"name": "finish", ...}, "observation": "..."}
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
| `word_count` | mcp:demo | 数单词数 |
| `reverse` | mcp:demo | 反转字符串 |
| `upper` | mcp:demo | 转大写 |
| `now` | mcp:demo | 当前 ISO 时间 |

## 换成真 MCP server

`backend/app.py` 里：

```python
server = MCPServer(
    name="demo",
    transport=StdioMCP(command=sys.executable, args=[str(MCP_SERVER_SCRIPT)]),
)
```

把 `transport` 改成 `StdioMCP(command="uvx", args=["mcp-server-filesystem", "/tmp"])`
或任何真 MCP server 的启动命令即可——前端代码**一行都不用改**。

HTTP 传输也同样——换成 `HttpMCP(url="https://...", headers={...})`。pyxis
的 MCP adapter 把传输差异吸收在内部，应用层只管拿到 `list[type[Tool]]`。

## 设计对照

| 设计点 | 代码里的体现 |
|---|---|
| MCP server 是数据不是行为 | `MCPServer` 是 Pydantic 模型，没有 `run()` |
| 工具来源被 adapter 吸收 | `app.py` 里 `run()` 对 native / MCP 是同一行 `d.action.run()` |
| 传输生命周期绑 `async with` | `_lifespan()` 里 `async with mcp_toolset(server) as mcp_tools` |
| 混合注册 = 拼 list | `tool_classes = [*NATIVE_TOOLS, *mcp_tools]` |
| 选择由 LLM 做 | 判别式联合 + `kind` 字段，框架不做路由 |
