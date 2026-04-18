# 012：Human-in-the-loop —— 用生成器在 flow 里挂起等人

## 目的

真实 agent 几乎总要在某些中间点停下来等人拍板：看一眼计划再决定要不要
执行、确认一个危险工具调用、给段补充信息、在长对话里接一句。pyxis 不
引入持久化 checkpoint 机制——直接借 Python 原生的**生成器挂起/恢复**：
`@flow` 写成 `def` + `yield ask_human(...)` 的生成器，驱动器
`run_flow` 在每次 yield 处停下，把问题交给 `on_ask` 回调，再把答案
`.send()` 回去，直到生成器 `return`。

"人在中间"就此变成一段普通 Python 控制流。没有新 DSL，没有 state 快照，
没有隐藏的恢复语义——生成器本身就是活的状态。

## API 草图

```python
from pydantic import BaseModel
from pyxis import ask_human, flow, run_flow, step

class ReviewDecision(BaseModel):
    approve: bool
    comments: str | None = None

@flow
def review_flow(topic: str):
    """写计划 → 人审 → 执行。"""
    plan = make_plan(topic)   # 普通 @step
    decision: ReviewDecision = yield ask_human(
        "审核计划？",
        schema=ReviewDecision,
        plan=plan.model_dump(),
    )
    if not decision.approve:
        return {"status": "rejected", "comments": decision.comments}
    return {"status": "done", "result": execute(plan)}

# 同步驱动（CLI / 脚本）
def terminal_ask(q):
    print(q.question, q.context)
    return ReviewDecision(approve=input("y/N? ").lower() == "y")

result = run_flow(review_flow("建个博客"), on_ask=terminal_ask)

# 异步驱动（Web UI / bot）；on_ask 可以是 async def
result = await run_aflow(async_review_flow("x"), on_ask=async_handler)
```

## 验收标准

- `ask_human(question: str, *, schema: type[BaseModel] | None = None, **context) -> HumanQuestion`
  返回一个 `@dataclass(frozen=True)`，字段 `question: str`、
  `schema: type[BaseModel] | None`、`context: dict[str, Any]`。
- `finish(value) -> FlowResult`：显式终态哨兵，给无法写 `return value`
  的异步生成器 flow 使用。同步 flow 两种都支持：`return v` 或
  `yield finish(v)`。
- `@flow` 已经支持生成器函数：调用 `flow(*args)` 返回一个 `Generator` /
  `AsyncGenerator`，`__name__` / `__doc__` 保留。生成器 `flow` 不支持
  `.run_traced`（它需要 `for`/`next` 驱动，没有"一次性拿到结果"的概念；
  用 `run_flow` 代替）。
- `run_flow(gen, *, on_ask) -> Any`：
  - 驱动一个普通（同步）生成器；
  - 每次 yield 的必须是 `HumanQuestion`，否则抛 `TypeError`；
  - `on_ask(q)` 的返回值若不是 `q.schema` 的实例且 `schema` 非 None，
    先 `schema.model_validate(...)` 转换再 send；
  - 生成器 `return v` 后，`run_flow` 返回 `v`；
  - 生成器内部抛异常时，异常原样向外传。
- `run_aflow(agen, *, on_ask) -> Any`（`async def`）：
  - 同时支持普通生成器与 async generator；
  - `on_ask` 可以是 sync 或 `async def`（用 `inspect.iscoroutinefunction`
    判定，必要时 `await` 其结果）；
  - 其他语义与 `run_flow` 对齐。
- `trace()` 覆盖整个生成器执行期（Step 调用发生时 trace 已经打开，
  ContextVar 天然跟着 yield/send）。
- 一个生成器 flow 里完全不 yield `HumanQuestion`（只 return）时，
  `run_flow` 等价于直接调用普通函数 flow，行为一致。

## 不做（留给 v1.1 之后）

- Checkpoint 持久化 / 跨进程恢复。用户自己 pickle context 或保存历史。
- UI 脚手架（on_ask 的前端实现完全在用户手里）。
- 把 `HumanQuestion` 建模为 `Tool`。Tool 是 LLM 在 schema 里"选"的动作；
  HumanQuestion 是 Python 代码主动插入的介入点，语义不同。
- 多工人并发 + 锁 / 抢答等复杂协作。
