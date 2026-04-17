# 004：异步支持 —— 把同步路径原样镜像到 asyncio

## 目的

生产上的 agent 都是 IO 密集型，必须要有 async 路径。每个原语都添加一个
异步孪生，调用时按"装饰的函数是否是 `async def`"来分派。trace 用的
`ContextVar` 本身就能跨 asyncio task 传播，trace API 不变。

## API 草图

```python
import asyncio
from pydantic import BaseModel
from pyxis import FakeClient, flow, step, trace

class Analysis(BaseModel):
    observation: str
    conclusion: str

fake = FakeClient([Analysis(observation="o", conclusion="c")])

@step(output=Analysis, client=fake)
async def analyze(text: str) -> str:
    """异步分析。"""
    return text

@flow
async def research(topic: str) -> Analysis:
    return await analyze(topic)

async def main():
    result, t = await research.run_traced("AI")
    assert [r.step for r in t.records] == ["analyze"]

asyncio.run(main())
```

## 验收标准

- `Client` 协议（同步）新增同胞 `AsyncClient` 协议，带 `acomplete(...)`。
- `FakeClient` 同时实现 `complete` 与 `acomplete`（async 版本直接委托给
  sync 版本——同一队列、同一 call 日志、同一错误语义）。
- `InstructorClient` 同样两路都实现；async 需要 `AsyncOpenAI` 背后的
  instructor 客户端。构造函数签名：`InstructorClient(sync=..., async_=...)`，
  任一为 `None` 时懒构造默认的 OpenAI / AsyncOpenAI 实现。
- `@step` 检测到 `async def` 的 prompt 函数时返回 `AsyncStep`；它的
  `__call__` 是 coroutine function。
- `AsyncStep` await prompt 函数（如它自己也是 coroutine）、await
  `client.acomplete(...)`、成功后写一条 `TraceRecord`（形状与 sync 相同）。
- `@flow` 检测到 `async def` 时返回 `AsyncFlow`；`AsyncFlow.run_traced(*args)`
  是 `async def`，返回 `(result, Trace)`。
- `asyncio.gather` 并发的若干异步 step 落入同一 active trace，按完成顺序排列。

## 不做（留给后续迭代）

- 流式输出（iter 10 覆盖）。
- 同一 flow 里同步与异步 step 混用（理论上可行但暂不保证，未测）。
- asyncio 之外的取消语义。
