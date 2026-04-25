# chat-demo

一个多轮对话示例。

**数据路径**

- 后端用 `AsyncStep.astream(...)` 推送 partial `ChatReply{thought, response}`
- 前端用顶部 toggle 切换渲染方式

**两种渲染**

- **Chat view** — `{role, content}` 气泡流，`content` 取 `response`
- **Inspect view** — 整个 schema 铺开，`thought` 先填、`response` 后填

后端数据相同，前端展示方式不同。

**取舍**

- Chat view 要等 `response` 字段开始生成后才显示回复
- Inspect view 可以看到 `thought` 和 `response` 的生成顺序
- 如果产品只需要聊天体验，直接使用原生 chat SDK 更合适

## 技术栈

- 后端：FastAPI + pyxis，`POST /chat` SSE
- 前端：Vite + React + TS + Tailwind；`fetch` + `ReadableStream` 手解 SSE

## 相关

- 启动命令、SSE 帧格式、目录说明：[`apps/chat-demo/README.md`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/chat-demo)
- 源码：[`apps/chat-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/chat-demo)
