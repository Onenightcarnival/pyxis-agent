# human-in-the-loop

agent 跑到一半需要人类回答一个问题再继续。pyxis 用 **Python 生成器** 解决这个
问题——没有 checkpoint 序列化、没有状态机图、没有外部持久化。

## 核心想法

生成器**本身**就是活的暂停状态。

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

驱动：

```python
gen = booking()
question = next(gen)              # 拿到第一个 ask_human
answer = input(question.prompt)
question = gen.send(answer)       # 把人类回答塞回生成器
...
```

或者用封装好的驱动器：

```python
result = run_flow(booking(), resolver=lambda q: input(q.prompt))
```

生成器被挂起 → 驱动器拿到 `HumanQuestion` → 人回答 → `.send()` 回去 → 生成器
继续跑。**Python 语言本身把状态给你管了**——没有框架再抽一层。

## 异步版

```python
@flow
async def booking():
    destination = yield ask_human("你要去哪？")
    ...
    yield finish(result)   # async gen 禁用 return 值，用 finish 代替
```

```python
result = await run_aflow(booking(), aresolver=some_async_fn)
```

## 为什么不做 checkpoint？

"保存状态到磁盘，下次加载恢复" 看起来很有用，但：

- 需要序列化框架（pickle / JSON / protobuf），把变量类型圈地限制
- 需要版本迁移（代码改了，老 checkpoint 要能加载）
- 调试复杂度飙升（堆栈是从文件恢复的，断点不一定对应源码行）

pyxis 的取舍：**生成器跑在内存里，重启就重跑**。真需要持久化中途问题，
应用层自己拿数据库存 `HumanQuestion` / `answer` 就行。

## 什么时候用

- 任何需要人类拍板的 agent 场景：审批、澄清、择优、多轮采集
- 客服 / 销售脚本的 agent 化
- 合规场景下"必须有人确认"的节点

## 什么时候**不**用

- 纯自动流程——用 `@flow` 不带 `ask_human`
- 跨服务、跨进程、要长期挂起的工作流——那是工作流引擎的地盘（Temporal /
  Cadence），pyxis 不抢

完整签名看 [API 参考 → pyxis.human](../api/human.md)。
