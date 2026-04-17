# 002：Flow —— 显式多轮编排，Python 原生

## 目的

框架拒绝为多轮编排发明 DSL —— Python 本身就有 `if`、`for`、函数组合。
`@flow` 只做两件事：

1. 为函数加一个"这是一个多轮 flow"的标记；
2. 提供 `.run_traced(*args, **kwargs)` → `(result, Trace)` 的一键观测。

`trace()` 是一个上下文管理器，作用域内的所有 `Step` 调用都会被捕获，
不管这些 Step 是否在某个 flow 里。

## API 草图

```python
from pyxis import flow, step, trace
from pydantic import BaseModel

class A(BaseModel):
    observation: str
    conclusion: str

class P(BaseModel):
    plan: str

@step(output=A, client=fake_a)
def analyze(text: str) -> str:
    """你负责分析文本。"""
    return text

@step(output=P, client=fake_p)
def plan(a: A) -> str:
    """你把分析结果转成计划。"""
    return a.conclusion

@flow
def research(topic: str) -> P:
    """先分析再规划。"""
    return plan(analyze(topic))

# 普通调用：就像普通函数
p = research("AI agents")

# 带 trace 的一次调用
p, t = research.run_traced("AI agents")
assert [r.step for r in t.records] == ["analyze", "plan"]

# 跨多次调用的 ad-hoc trace
with trace() as t:
    research("a")
    research("b")
assert len(t.records) == 4
```

## 验收标准

- `@flow` 返回 callable，保留 `__name__` 与 `__doc__`。
- 直接调用 flow 的行为与原函数完全一致。
- `flow.run_traced(*args, **kwargs)` 返回 `(result, Trace)`，Trace 里的
  `TraceRecord` 数量等于该 flow 同步路径上执行过的 Step 数量。
- `trace()` 上下文管理器捕获作用域内所有 Step 调用，跨多次 flow 调用也算。
- `TraceRecord` 暴露：`step`（Step 名字）、`messages`（消息列表）、
  `output`（返回的 BaseModel 实例）、`model`（字符串）。
- 不在任何 `trace()` 里的 Step 调用不写入任何记录，返回值照常。
- 嵌套 `trace()`：内层捕获内层；外层不重复。已记入文档、已有测试。

## 不做（留给后续迭代）

- 异步 flow、并行 fan-out、retry/backoff、流式 trace、trace 持久化。
