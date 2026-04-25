# 概念

这一栏介绍 pyxis 的三个核心 API：[Step](step.md)、[Tool](tool.md)、[Flow](flow.md)。测试、可观测、MCP、Interrupt 和常见 agent 写法放在 [Cookbook](../cookbook/index.md)。

## 核心三件套

| 概念 | 职责 |
|---|---|
| [Step](step.md) | 一次结构化 LLM 调用；函数提供 prompt，schema 定义输出 |
| [Tool](tool.md) | 动作即 schema；`BaseModel + run()` 让 Python 执行动作 |
| [Flow](flow.md) | 多次调用之间的显式编排；Python 函数就是工作流 |

## 怎么读

建议先读 [哲学与定位](philosophy.md)，再读 [Step](step.md)、[Tool](tool.md)、[Flow](flow.md)。

按任务找示例：

- 测 prompt 与调用参数：[测试与 FakeClient](../cookbook/testing.md)
- 接 Langfuse / OTel / APM：[可观测](../cookbook/observability.md)
- 接远端 MCP 工具：[MCP](../cookbook/mcp.md)
- 让 flow 中途等外部输入：[Interrupt](../cookbook/interrupt.md)
- 看常见 agent 写法：[Agent 模式](../cookbook/index.md)

## 最小代码地图

下面是三个 API 的最小形态。

```python
# Step：一次结构化 LLM 调用
summary = summarize(article)
```

```python
# Flow：Python 负责多步编排
@flow
def research(topic: str):
    return write_report(plan(topic))
```

```python
# Tool：动作是 schema，执行是 Python
observation = action.run()
```

---

读完：[Cookbook](../cookbook/index.md) · [Demos](../demos/index.md) · [API 参考](../api/step.md)
