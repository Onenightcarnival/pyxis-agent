# chat-demo

一个多轮对话 agent。后端用 `AsyncStep.astream(...)` 流式推 partial
`ChatReply{thought, response}`。前端顶上一个 toggle，切两种渲染：

- **Chat view**：常见的 `{role, content}` 气泡流，`content` 就是 schema
  里的 `response` 字段。
- **Inspect view**：把整个 schema 铺开，能看到 `thought` 先填完、
  `response` 再填完。字段被 LLM 一个一个写进来的过程平时藏在 JSON 里，
  这里直接画出来。

同一份后端流，两种前端拼法——后端吐的就是 Pydantic 实例，给人看哪些字段、
怎么排版，应用层自己决定。

有个诚实的 tradeoff：Chat view 的气泡出字速度永远不如原生 chat app。
后端要把 `thought` 先流完，`response` 的 caret 才开始跳——schema-as-CoT
多一步。聊天顺滑度优先的场景本来就不太该选 pyxis。

## 技术栈

- 后端：FastAPI + pyxis，单个 `POST /chat` 的 SSE 端点。
- 前端：Vite + React + TS + Tailwind，`fetch` + `ReadableStream` 手解 SSE。

启动命令、SSE 帧格式、目录结构都在
[`apps/chat-demo/README.md`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/chat-demo)。

源码：[`apps/chat-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/chat-demo)
