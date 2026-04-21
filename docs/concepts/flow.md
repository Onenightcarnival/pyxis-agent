# Flow：显式编排

`@flow` 在**多次 LLM 调用之间**加一层很薄的壳。它**不是**图引擎、不是 DAG、
不是 pipeline DSL——就是一个"带 trace 能力的普通 Python 函数"。

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

`triage` 长得像普通 Python 函数——因为它就是。`if`、`for`、`try/except`、嵌套
函数调用、早 return——Python 怎么写，`@flow` 就怎么写。

## 那它到底给了我什么？

**一个 `.run_traced()` 方法。**

```python
result, trace = triage.run_traced("今天糟透了")
print(trace.to_jsonl())
# 每条记录都是一次 @step 调用：messages + output + usage + error
```

- `result` 是函数的正常返回值
- `trace` 是一个 `Trace`，包含本次执行里所有 `@step` 的 `TraceRecord`
- `trace.total_usage()` 给 token 总量，`trace.errors()` 给失败记录

没有 `run_traced()` 也能直接调用，就是拿不到 trace 对象：

```python
result = triage("今天糟透了")   # 等价于 triage.run_traced(...)[0]
```

## 显式 > 隐式

pyxis **故意不做** agent loop 封装。如果你要做 ReAct 风格的循环：

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

这段代码**没有任何框架神秘感**。for 循环就是 for 循环；判别式联合用 `isinstance`
分派；超限就抛异常。调试：打断点、看堆栈。

如果框架把这段 loop 藏起来，代价是：

- 调试要翻框架源码
- 改 loop 行为要配置或子类继承
- 静态类型检查失效

所以我们不藏。**能写成 Python 函数，就写成 Python 函数。**

## 异步

```python
@flow
async def triage(text: str) -> Reply:
    v = await classify_async(text)
    ...

result, trace = await triage.run_atraced("...")
```

`@flow` 看函数签名分派同步 / 异步；对应的 trace API 也分 `run_traced` /
`run_atraced`。`trace()` 基于 `ContextVar`，跨 asyncio task 自动传播——
`asyncio.gather` 里跑多个 step，trace 会完整记录。

## 什么时候**不**用 Flow

- 只调一次 LLM——用 `@step` 就够了，不需要额外一层
- 要让 loop 可被外部驱动 / 中断——用 `@flow` 生成器版 + `run_flow` 驱动器
  （见 [human-in-the-loop](human.md)）

完整签名看 [API 参考 → pyxis.flow](../api/flow.md) 和 [pyxis.trace](../api/trace.md)。
