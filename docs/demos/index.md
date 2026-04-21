# Demos

`examples/` 是**单文件脚本**——一条主线、一个终端输出，读源码就能懂。
`apps/` 不一样：带**前端**、带**服务进程**、能在浏览器里看 agent 每一步
怎么被填出来的。

文档站里只讲每个 demo 的**看点**和**挑选建议**；跑起来的说明、
后端契约、架构图都在各自仓库里的 README（每页底部有链接）。

## 两个 demo 怎么挑

| 想看什么                                        | 挑                      |
|---|---|
| **schema 被逐字段填完**是什么样子；Chat vs Inspect 两种前端渲染风格对同一份流的对照 | [chat-demo](chat-demo.md) |
| **native `Tool` + 远端 MCP server** 在同一个 agent loop 里被 LLM 无感调度；stdio / Streamable HTTP 两种 MCP 传输并排跑 | [mcp-demo](mcp-demo.md)   |

两个都有完整后端 + 前端，都跑在 localhost，都需要一个 `OPENROUTER_API_KEY`
（或任一 OpenAI 兼容 key）。

## 这些不是库的一部分

`apps/` 下的东西**打包时被 exclude**（`pyproject.toml`），`ruff` / `pytest`
也跳过。它们是**跑得起来的使用姿势示例**，目的是把 pyxis 的抽象落到
"能看得见"的形态上。想把这些拿去改成自己的应用完全可以，License 和
库本体一致（MIT）。
