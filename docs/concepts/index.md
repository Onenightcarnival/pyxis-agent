# 概念指南

所有概念都从一条哲学展开：**声明式思维链**。

- [哲学与定位](philosophy.md)——为什么 agent-for-machine，为什么不做 LangChain-lite
- [Step：code-as-prompt](step.md)——函数即 prompt，字段即思维链
- [Flow：显式编排](flow.md)——纯 Python 组合多次 LLM 调用
- [Tool：action 即 schema](tool.md)——动作本身是 Pydantic 类
- [Hook：观察者](hooks.md)——只读中间件，接告警不碰业务
- [human-in-the-loop](human.md)——生成器驱动的中断/续传
- [MCP 适配](mcp.md)——远端工具翻成本地 `Tool` 子类

每篇尽量短，都带一个可跑的 snippet。API 参考在另一个 tab——那边是完整签名，
这边讲 **为什么这样设计、什么时候用、边界在哪**。
