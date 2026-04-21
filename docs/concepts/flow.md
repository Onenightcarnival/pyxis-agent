# Flow：显式编排

`@flow` 在多次 LLM 调用之间加一层很薄的壳。一个 `@flow` 函数就是一个普通
Python 函数，只是带了 `.run_traced()` 方法方便本地 debug。

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

`@flow` 唯一做的事是给函数挂一个 `.run_traced()` 方法，方便本地 debug 时
一口气拿到中间结果：

```python
result, trace = triage.run_traced("今天糟透了")
print(trace.to_jsonl())
```

- `result` 是函数的正常返回值
- `trace` 是一个 `Trace`，包含本次执行里所有 `@step` 的 `TraceRecord`
- `trace.total_usage()` 给 token 总量，`trace.errors()` 给失败记录

没有 `run_traced()` 也能直接调用：

```python
result = triage("今天糟透了")   # 等价于 triage.run_traced(...)[0]
```

生产场景的可观测性一般不用这个——直接接 [Langfuse](observability.md) 就行。
`run_traced` 主要是单测断言和本地 debug 的小帮手。

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

`@flow` 根据函数签名分派同步 / 异步，trace API 也分 `run_traced` /
`run_atraced`。底层 `trace()` 基于 `ContextVar`，跨 asyncio task 自动传播——
`asyncio.gather` 里并发跑多个 step 也能被完整记录。

## 什么时候不用 Flow

- 只调一次 LLM——`@step` 就够了。
- loop 要能被外部驱动或中断——用生成器版 `@flow` + `run_flow` 驱动器
  （见 [human-in-the-loop](human.md)）。

可跑示例：
[examples/research.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/research.py)、
[examples/agent_tool_use.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/agent_tool_use.py)。
完整签名见 [API 参考 → pyxis.flow](../api/flow.md)。
