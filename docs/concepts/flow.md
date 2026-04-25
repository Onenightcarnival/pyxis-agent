# Flow：显式编排

`@flow` 标记一个多步流程。函数体仍然是普通 Python 代码。

## 最小例子

```python
from pyxis import flow, step

@step(output=Verdict, model="gpt-4o", client=client)
def classify(text: str) -> str:
    return f"请判断情感：{text}"

@step(output=Reply, model="gpt-4o", client=client)
def reply(sentiment: str, text: str) -> str:
    return f"请根据情感生成回复：sentiment={sentiment}, text={text}"

@flow
def triage(text: str) -> Reply:
    v = classify(text)
    if v.confidence < 0.6:
        return escalate(text)
    return reply(v.sentiment, text)

result = triage("今天糟透了")
```

调用 `triage(...)` 就会按函数体顺序执行。

## 写一个 agent loop

ReAct 风格的循环可以直接写 `for`：

```python
@flow
def react(question: str) -> Answer:
    history: list[Step] = []
    for _ in range(MAX_STEPS):
        action = plan(question, history)
        if isinstance(action, Finish):
            return action.answer
        observation = action.run()
        history.append(Step(action=action, observation=observation))
    raise RuntimeError("超出最大步数")
```

工具选择用 `isinstance` 或 `.run()` 分派。超过步数时抛异常。

## 异步

```python
@flow
async def triage(text: str) -> Reply:
    v = await classify_async(text)
    ...

result = await triage("...")
```

- `@flow` 根据 `def` / `async def` 返回同步或异步 flow
- 多个 step 并发时直接使用 `asyncio.gather`

## 观测

- 生产：[可观测](../cookbook/observability.md) 页说明了 Langfuse、OTel 和 APM 的接入方式
- 测试：`FakeClient` 预置响应 + 断言 `fake.calls`
- 自定义打点：`@step` 外再套 Python 装饰器

## 什么时候不用 Flow

- 只调一次 LLM：使用 `@step`
- loop 要被外部驱动或中断：使用生成器版 `@flow` + `run_flow`，见 Cookbook 的 [Interrupt](../cookbook/interrupt.md)

---

- 可跑示例：[examples/research.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/research.py) · [examples/agent_tool_use.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/agent_tool_use.py)
- 完整签名：[API：pyxis.flow](../api/flow.md)
