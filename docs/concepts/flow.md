# Flow：显式编排

`@flow` 在多次 LLM 调用之间加一层**语义标记**——就是一个普通 Python
函数包一下，外加 `async def` / `def` 自动分派。不做观测、不做
checkpoint、不做重跑——那些交给 APM 和你的业务代码。

## 最小例子

```python
from pyxis import flow, step

@step(output=Verdict, model="gpt-4o", client=client)
def classify(text: str) -> str:
    """你是情感分类器..."""
    return text

@step(output=Reply, model="gpt-4o", client=client)
def reply(sentiment: str, text: str) -> str:
    """根据情感生成回复..."""
    return f"sentiment={sentiment}, text={text}"

@flow
def triage(text: str) -> Reply:
    v = classify(text)
    if v.confidence < 0.6:
        return escalate(text)
    return reply(v.sentiment, text)

result = triage("今天糟透了")
```

没有 `.run_traced()` 这类糖——就是一个函数调用。

## 写一个 agent loop

要做 ReAct 风格的循环，自己 `for` 一下就行：

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

判别式联合用 `isinstance` 分派，超限抛异常，调试打断点看堆栈。

## 异步

```python
@flow
async def triage(text: str) -> Reply:
    v = await classify_async(text)
    ...

result = await triage("...")
```

- `@flow` 按函数签名分派同步 / 异步
- 多 step 并发就裸写 `asyncio.gather(step_a(...), step_b(...))`

## 观测怎么做？

- 生产：接 [Langfuse](observability.md) / OpenTelemetry / Datadog——OpenAI
  SDK 层 auto-instrument 自动覆盖每个 `@step` 调用。pyxis 不提供自己的
  trace 体系。
- 测试：用 `FakeClient` 预置响应 + 断言 `fake.calls`。
- 自定义打点：`@step` 外再套自己的 Python 装饰器。

## 什么时候不用 Flow

- 只调一次 LLM → `@step` 就够
- loop 要被外部驱动或中断 → 生成器版 `@flow` + `run_flow`（见 [human-in-the-loop](human.md)）

---

- 可跑示例：[examples/research.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/research.py) · [examples/agent_tool_use.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/agent_tool_use.py)
- 完整签名：[API → pyxis.flow](../api/flow.md)
