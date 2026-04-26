# Interrupt 接入说明

Interrupt 用生成器流程表达外部输入点。流程运行到某一步时 `yield ask_interrupt(...)`，应用层收集答案后再把答案送回生成器。

外部输入可以来自人、另一个 agent、审批服务或 webhook。展示方式和持久化策略由应用层处理。

`ask_interrupt` 产出 `InterruptRequest`，`run_flow` / `run_aflow` 负责把答案 `.send()` 回生成器。

- 不做 checkpoint 序列化
- 不做状态机图
- 不做外部持久化

## 核心写法
```python
from pyxis import ask_interrupt, run_flow


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
q = next(gen)  # 拿到第一个 InterruptRequest
answer = input(q.question)
q = gen.send(answer)  # 把答案送回生成器
...
```

或者用封装好的驱动器：
```python
result = run_flow(booking(), on_interrupt=lambda q: input(q.question))
```

执行过程是：生成器挂起，驱动器拿到 `InterruptRequest`，外部参与者回答，驱动器用 `.send()` 继续生成器。

如果输入来自另一个 agent，`on_interrupt` 可以转发请求；如果输入来自 webhook，应用层可以先保存请求，再在回调里恢复流程。

## 异步版
```python
async def booking():
    destination = yield ask_interrupt("你要去哪？")
    ...
    yield finish(result)  # async gen 禁用 return 值，用 finish 代替
```
```python
result = await run_aflow(booking(), on_interrupt=some_async_fn)
```

## 不做 checkpoint

生成器状态保存在当前进程里。进程重启后需要重新运行流程。需要持久化时，应用层保存 `InterruptRequest` 和答案。

## 什么时候用

- 审批、澄清、择优、多轮采集
- 一个 machine agent 需要把子任务交给另一个 agent
- HTTP webhook / 队列事件回来之后，流程才能继续
- 合规场景下“必须有人确认”的节点

## 什么时候不用

- 纯自动流程：普通 Python 函数
- 跨服务、跨进程、长期挂起的工作流：工作流引擎（Temporal / Cadence）
- checkpoint、resume token、多 pending interrupt 管理：业务 runtime 或工作流系统

`ask_interrupt(question, *, schema=None, **context)` 返回 `InterruptRequest`。`**context` 会保存到 `.context`，可用于 UI 渲染、agent 转发或判断。

---

- 可跑示例：[examples/interrupt_review.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/interrupt_review.py)
- 完整签名：[API：pyxis.interrupt](../api/interrupt.md)
