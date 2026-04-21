# Flow：显式编排

`@flow` 在多次 LLM 调用之间加一层薄壳。一个 `@flow` 就是一个普通 Python 函数，额外挂一个 `.run_traced()` 方便本地 debug。

## 最小例子

```python
from pyxis import flow, step

@step(output=Verdict)
def classify(text: str) -> str:
    """你是情感分类器..."""
    return text

@step(output=Reply)
def reply(sentiment: str, text: str) -> str:
    """根据情感生成回复..."""
    return f"sentiment={sentiment}, text={text}"

@flow
def triage(text: str) -> Reply:
    v = classify(text)
    if v.confidence < 0.6:
        return escalate(text)
    return reply(v.sentiment, text)
```

`@flow` 给函数挂一个 `.run_traced()`，方便本地 debug 一次拿到中间结果：

```python
result, trace = triage.run_traced("今天糟透了")
print(trace.to_jsonl())
```

- `result` — 函数正常返回值
- `trace` — `Trace` 实例，含本次所有 `@step` 的 `TraceRecord`
- `trace.total_usage()` — token 总量
- `trace.errors()` — 失败记录

不加 `.run_traced()` 也能直接调：

```python
result = triage("今天糟透了")   # 等价于 triage.run_traced(...)[0]
```

生产的可观测性一般不走这个 → 直接接 [Langfuse](observability.md)。`run_traced` 主要给单测断言和本地 debug 用。

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

result, trace = await triage.run_atraced("...")
```

- `@flow` 按函数签名分派同步 / 异步
- trace API 对应 `run_traced` / `run_atraced`
- 底层 `trace()` 基于 `ContextVar`，跨 asyncio task 自动传播；`asyncio.gather` 并发也能完整记录

## 什么时候不用 Flow

- 只调一次 LLM → `@step` 就够
- loop 要被外部驱动或中断 → 生成器版 `@flow` + `run_flow`（见 [human-in-the-loop](human.md)）

---

- 可跑示例：[examples/research.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/research.py) · [examples/agent_tool_use.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/agent_tool_use.py)
- 完整签名：[API → pyxis.flow](../api/flow.md)
