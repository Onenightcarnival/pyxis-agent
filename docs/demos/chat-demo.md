# chat-demo

多轮对话 agent，后端流式推 partial `ChatReply{thought, response}`，
前端**一个开关**切换两种渲染风格：

- **Chat view**：标准 `{role, content}` 气泡流。`content` 取 schema 里的
  `response` 字段。用户熟悉的聊天心智模型。
- **Inspect view**：整个 Pydantic schema 展开，字段逐个"亮起"——
  `thought` 先填完、`response` 再填完。schema-as-CoT 的可视化。

同一份后端流，两种前端拼法。

## 为什么这个 demo 值得看

它把 pyxis 一条核心原则落成了一个按钮：

> **LLM 直接输出是给代码消费的结构化数据；给人看的东西由应用层从字段
> 里拼出来。**

Chat view 不是"pyxis 做不到丝滑"的道歉——它是应用层从结构化数据里
**再渲染**出一层"像 ChatGPT 的体感"。Inspect view 才是 pyxis 的主场：
schema 字段被 LLM 一个个填出来的过程，平时藏在 JSON 里，这里被直接
画在屏幕上。

这也是"和 Claude Desktop 对标丝滑度"被
[ROADMAP 明确拒绝](https://github.com/Onenightcarnival/pyxis-agent/blob/main/ROADMAP.md#%E6%95%85%E6%84%8F%E4%B8%8D%E5%81%9A)
的理由——token 到字段到屏幕比"LLM 直出文本"多一步，不可能追平；
但**可审计 / 可断言 / 可入库**换来的东西，在 Inspect view 里看得一清二楚。

## 技术形态

- **后端**：FastAPI + pyxis，单个 `POST /chat` 的 SSE 端点，每帧一行
  JSON（`partial` 与 `done` 两类），基于 `AsyncStep.astream(...)`。
- **前端**：Vite + React + TypeScript + Tailwind，`fetch` + `ReadableStream`
  手工解析 SSE。
- **数据契约**在 app README 里有完整示例帧。

## 跑起来 & 完整说明

两个终端的启动命令、帧格式、目录结构、设计对照表都在
[`apps/chat-demo/README.md`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/chat-demo)。

源码：[`apps/chat-demo/`](https://github.com/Onenightcarnival/pyxis-agent/tree/main/apps/chat-demo)
