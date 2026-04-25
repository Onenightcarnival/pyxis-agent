# 概念

这一组页面先定义 pyxis 的概念分层，再用最小代码例子说明每个概念如何落地。Cookbook 负责更完整的场景化示例和最佳实践。

## 认知分层

| 层级 | 概念 | 职责 |
|---|---|---|
| 定位 | [哲学与定位](philosophy.md) | 为什么 pyxis 选择 agent-for-machine：LLM 输出先给 Python 代码消费 |
| Core primitives | [Step](step.md) | 一次结构化 LLM 调用；函数 = prompt，字段顺序 = 思维链 |
| Core primitives | [Flow](flow.md) | 多次调用之间的显式编排；Python 函数就是工作流 |
| Core primitives | [Tool](tool.md) | 动作即 schema；`BaseModel + run()` 让 Python 执行动作 |
| Runtime patterns | [Interrupt](interrupt.md) | Flow 运行中产出外部输入点，再把答案送回去继续 |
| Runtime patterns | [MCP 适配](mcp.md) | 把远端工具系统翻成本地 `Tool` 子类 |
| Runtime patterns | [可观测性](observability.md) | 让 Langfuse / OTel / APM 接在 OpenAI SDK 层 |

## 怎么读

先读 [哲学与定位](philosophy.md)，再顺序读 [Step](step.md)、[Flow](flow.md)、[Tool](tool.md)。这三页是最小内核。

之后按场景读 runtime patterns：

- 要让 flow 在中途等待外部参与者 → [Interrupt](interrupt.md)
- 要接远端工具服务 → [MCP 适配](mcp.md)
- 要接生产观测或测试断言 → [可观测性](observability.md)

human review、machine agent 协作、webhook resume 这类来源差异，放在 [Cookbook](../cookbook/index.md) 展开；概念层只定义机制和边界。

## 最小代码地图

Concepts 里的例子刻意短，只回答“这个概念是什么”。同一个机制进入 Cookbook 后，才展开成可直接改造的 recipe。

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

```python
# Interrupt：flow 产出外部输入点，再被答案恢复
decision = yield ask_interrupt("批准这个计划吗？", schema=Decision)
```

```python
# MCP：远端工具翻成本地 Tool 子类
async with mcp_toolset(server) as remote_tools:
    Tools = Union[LocalTool, *remote_tools]
```

```python
# Observability：instrument OpenAI SDK 层，@step 不需要专用 trace API
client = LangfuseOpenAI(...)
```

---

读完：[Cookbook](../cookbook/index.md) · [Demos](../demos/index.md) · [API 参考](../api/step.md)
