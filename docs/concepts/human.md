# human-in-the-loop

agent 跑到一半需要人类回答一个问题再继续。pyxis 用 Python 生成器解决——
生成器本身就是活的暂停状态。没有 checkpoint 序列化、没有状态机图、没有
外部持久化。

## 核心想法

```python
from pyxis import flow, ask_human, run_flow

@flow
def booking():
    destination = yield ask_human("你要去哪？")
    budget = yield ask_human(f"去 {destination} 的预算？")
    confirm = yield ask_human(f"预算 {budget} 确认？", choices=["是", "否"])
    if confirm == "是":
        return plan_trip(destination, budget)
    return None
```

手动驱动：

```python
gen = booking()
q = next(gen)                     # 拿到第一个 HumanQuestion
answer = input(q.question)
q = gen.send(answer)              # 把答案塞回生成器
...
```

或者用封装好的驱动器：

```python
result = run_flow(booking(), on_ask=lambda q: input(q.question))
```

生成器挂起 → 驱动器拿到 `HumanQuestion` → 人回答 → `.send()` 回去 →
生成器继续跑。Python 语言本身把状态管好了。

## 异步版

```python
@flow
async def booking():
    destination = yield ask_human("你要去哪？")
    ...
    yield finish(result)   # async gen 禁用 return 值，用 finish 代替
```

```python
result = await run_aflow(booking(), on_ask=some_async_fn)
```

## 不做 checkpoint

生成器跑在内存里，进程重启就重跑。框架不做状态序列化与恢复；真要持久化，
应用层自己拿数据库存 `HumanQuestion` 和答案即可。

## 什么时候用

- 审批、澄清、择优、多轮采集这类需要人类拍板的 agent 场景。
- 客服 / 销售脚本的 agent 化。
- 合规场景下"必须有人确认"的节点。

## 什么时候不用

- 纯自动流程——用普通 `@flow` 不带 `ask_human`。
- 跨服务、跨进程、要长期挂起的工作流——那是工作流引擎的地盘
  （Temporal / Cadence），pyxis 不抢。

`ask_human(question, *, schema=None, **context)` 造出 `HumanQuestion`；
`**context` 原样挂在 `.context` 上，给 UI 渲染或判断用。

可跑示例：
[examples/human_review.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/human_review.py)。
完整签名与字段见 [API 参考 → pyxis.human](../api/human.md)。
