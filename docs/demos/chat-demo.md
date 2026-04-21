# chat-demo

多轮对话 agent。

**数据路径**

- 后端 `AsyncStep.astream(...)` 推 partial `ChatReply{thought, response}`
- 前端顶部 toggle 切渲染

**两种渲染**

- **Chat view** — `{role, content}` 气泡流，`content` 取 `response`
- **Inspect view** — 整个 schema 铺开，`thought` 先填、`response` 后填

同一份后端流，两种前端拼法；给人看什么、怎么排版归应用层。

**Tradeoff**

- Chat view 气泡出字速度**永远不如**原生 chat app
- 后端要先流 `thought`，`response` 的 caret 才开始跳 — schema-as-CoT 多一步
- 聊天顺滑度优先的场景本来就不该选 pyxis

## 技术栈

- 后端：FastAPI + pyxis，`POST /chat` SSE
- 前端：Vite + React + TS + Tailwind；`fetch` + `ReadableStream` 手解 SSE

## 相关

- 启动命令 / SSE 帧格式 / 目录 → [`apps/chat-demo/README.md`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/chat-demo)
- 源码 → [`apps/chat-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/chat-demo)
