# chat-demo —— pyxis 的带前端聊天应用示例

用 pyxis 搭一个**多轮对话 agent**，后端流式推送 partial Pydantic schema，
前端用**一个开关**在两种渲染风格之间切换：

- **Chat view**：标准 `{role, content}` 气泡流。`content` 取 schema 里的
  自然语言字段（本 demo 是 `response`）。用户熟悉的聊天心智模型。
- **Inspect view**：把整个 Pydantic schema 展开，字段逐个"亮起"——
  `thought` 先出现，`response` 后出现。pyxis 独特性（schema-as-CoT）的
  可视化。

两种视图**共享同一份后端流式数据**。这正是把 pyxis 的核心原则
"展示层归上层开发者"落地成了一个按钮：schema 是结构化骨架，给谁看、
怎么拼、用什么 UI，都是应用代码的自由。

## 架构

```
apps/chat-demo/
├── backend/            FastAPI + pyxis
│   ├── pyproject.toml
│   ├── app.py          单 POST /chat SSE 端点，流式 partial JSON
│   └── .env.example
└── frontend/           Vite + React + TypeScript + Tailwind
    ├── package.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx     root，顶部 View toggle + 输入框 + 消息流
        ├── types.ts    ChatMessage / ChatReply schema（镜像后端）
        ├── sse.ts      fetch + ReadableStream 手工解析 SSE
        └── components/
            ├── ChatView.tsx    气泡流，content 取 reply.response
            ├── InspectView.tsx schema 字段逐个高亮
            └── ViewToggle.tsx
```

后端流数据契约（每帧一行 JSON）：

```json
{"kind": "partial", "thought": "...", "response": null}
{"kind": "partial", "thought": "...", "response": "..."}
{"kind": "done", "final": {"thought": "...", "response": "..."}}
```

## 跑起来

两个终端：

```bash
# 后端（3001 端口）
cd apps/chat-demo/backend
uv sync
uv run --env-file .env uvicorn app:app --reload --port 3001

# 前端（5173 端口）
cd apps/chat-demo/frontend
pnpm install     # 或 npm install
pnpm dev
```

打开 http://localhost:5173，顶部切换 Chat / Inspect 即可对比。

## 定位

这不是 pyxis 库的一部分，**只是一个跑得起来的示例**。根 `pyproject.toml`
用 `exclude = ["apps"]` 把它从 wheel 打包里移除；`ruff` / `pytest` 也都
跳过 `apps/`，保持库本体清爽。未来可以再加别的示例应用（agent 市场
浏览器、代码审查 agent 等），都走这个 `apps/<name>/` 的约定。

## 诚实的丝滑度说明

pyxis 是 **agent-for-machine** 阵营：LLM 直接产出 `ChatReply{thought, response}`
给代码消费，Chat view 的气泡是前端**从字段里拿 `response` 出来再渲染**
的结果。这和 Claude Desktop / ChatGPT "LLM 直出文本给人看" 的路径不同。

实际体感上：

- **Chat view 的丝滑度永远不如**原生 chat app——后端要把 `thought` 和
  `response` 两个字段都流式填（schema-as-CoT），用户才看见 response
  的 caret 开始跳。token 到字段到屏幕的链路比"直出文本"多了一步。
- **Inspect view 才是 pyxis 的主场**——你能肉眼看到 `thought` 先 filled、
  `response` 后 filled。每一轮都是可解析、可断言、可入库的 Pydantic。

这个开关**就是两种哲学的并置**：想看"给人"的体感切 Chat，想看"给机器"
的本质切 Inspect。要求 pyxis 两个都做到极致是贪心——它的赢点在右边。
