# 概念
这一栏介绍 pyxis 的两个核心 API：[Step](step.md)、[Tool](tool.md)。测试、可观测、MCP、Interrupt 和常见 agent 写法放在 [Cookbook](../cookbook/index.md)。

## 核心两件套

| 概念 | 职责 |
|---|---|
| [Step](step.md) | 一次 LLM 调用；schema 定义返回字段，函数返回本次输入 |
| [Tool](tool.md) | 用 `BaseModel` 描述参数，用 `run()` 执行动作 |

## 怎么读
建议先读 [定位](philosophy.md)，再读 [Step](step.md)、[Tool](tool.md)。
按任务找示例：

- 测输入消息与调用参数：[测试与 FakeClient](../cookbook/testing.md)
- 接 Langfuse / OTel / APM：[可观测](../cookbook/observability.md)
- 接远端 MCP 工具：[MCP](../cookbook/mcp.md)
- 让生成器流程中途等外部输入：[Interrupt](../cookbook/interrupt.md)
- 看常见 agent 写法：[Agent 模式](../cookbook/index.md)

## 最小代码地图
下面是两个核心 API 的最小形态。
```python
# Step：一次结构化 LLM 调用
summary = summarize(article)
```
```python
# Tool：动作是 schema，执行是 Python
observation = action.run()
```

---
读完：[Cookbook](../cookbook/index.md) · [API 参考](../api/step.md)
