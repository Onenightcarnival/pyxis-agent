# Interrupt：外部输入点

Interrupt 是 flow 运行中的一个结构化暂停点：flow 产出一个“需要外部输入才能继续”的请求，应用层拿到请求、收集答案，再把答案送回正在运行的生成器。

human、machine agent、审批服务、webhook 都可以是 interrupt 的来源。概念层只关心机制；具体来源放到 Cookbook 和应用层处理。

`ask_interrupt` 产出 `InterruptRequest`，`run_flow` / `run_aflow` 负责把答案 `.send()` 回生成器。

- 无 checkpoint 序列化
- 无状态机图
- 无外部持久化

## 核心想法

```python
from pyxis import ask_interrupt, flow, run_flow

@flow
def booking():
    destination = yield ask_interrupt("你要去哪？")
    budget = yield ask_interrupt(f"去 {destination} 的预算？")
    confirm = yield ask_interrupt(f"预算 {budget} 确认？", choices=["是", "否"])
    if confirm == "是":
        return plan_trip(destination, budget)
    return None
```

手动驱动：

```python
gen = booking()
q = next(gen)                     # 拿到第一个 InterruptRequest
answer = input(q.question)
q = gen.send(answer)              # 把答案塞回生成器
...
```

或者用封装好的驱动器：

```python
result = run_flow(booking(), on_interrupt=lambda q: input(q.question))
```

生成器挂起 → 驱动器拿到 `InterruptRequest` → 外部参与者回答 → `.send()` → 生成器继续跑。Python 本身把状态管好了。

这里的人只是第一种 interrupt source。换成 machine agent 时，`on_interrupt` 可以把请求转发给另一个 agent；换成 webhook 时，应用层可以把请求入库并在回调里恢复自己的流程。pyxis 当前不把这些来源提前抽象成通用 runtime。

## 异步版

```python
@flow
async def booking():
    destination = yield ask_interrupt("你要去哪？")
    ...
    yield finish(result)   # async gen 禁用 return 值，用 finish 代替
```

```python
result = await run_aflow(booking(), on_interrupt=some_async_fn)
```

## 不做 checkpoint

生成器跑在内存里，进程重启就重跑。框架不做状态序列化与恢复；要持久化，应用层自己用数据库存 `InterruptRequest` 和答案。

## 什么时候用

- 审批 · 澄清 · 择优 · 多轮采集 — 要外部参与者拍板的 agent
- 一个 machine agent 需要把子任务交给另一个 agent
- HTTP webhook / 队列事件回来之后，流程才能继续
- 合规场景下"必须有人确认"的节点

## 什么时候不用

- 纯自动流程 → 普通 `@flow` 不带 `ask_interrupt`
- 跨服务 / 跨进程 / 长期挂起的工作流 → 工作流引擎（Temporal / Cadence）
- 需要 checkpoint / resume token / 多 pending interrupt 管理 → 这已经是 runtime 系统

`ask_interrupt(question, *, schema=None, **context)` 造出 `InterruptRequest`；`**context` 原样挂在 `.context` 上，给 UI 渲染、agent 转发或判断用。

---

- 可跑示例：[examples/interrupt_review.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/interrupt_review.py)
- 完整签名：[API → pyxis.interrupt](../api/interrupt.md)
