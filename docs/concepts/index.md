# 概念指南

核心机制就两条：**code as prompt**（函数即 prompt）+ **schema as workflow**
（字段顺序即思维链）。其余都是围绕这两条展开的原语。

- [哲学与定位](philosophy.md)
- [Step：code-as-prompt](step.md)
- [Flow：显式编排](flow.md)
- [Tool：action 即 schema](tool.md)
- [human-in-the-loop](human.md)
- [MCP 适配](mcp.md)
- [可观测性](observability.md)——生产接 Langfuse，测试用 `trace()` + `FakeClient`
- [Hook：观察者（进阶）](hooks.md)——自己接 Prometheus / OTel / Slack 告警时用

每篇都带一个能直接跑的 snippet。API 参考在另一个 tab，那边是完整签名。
