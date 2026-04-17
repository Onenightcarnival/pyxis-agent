# 011：StepHook —— 观察者中间件

## 目的

生产环境需要在每个 Step 的入口/出口/失败处挂观察者：打点到 Prometheus、
发 Slack 告警、写结构化日志、刷 OpenTelemetry span。这些全都是**只读**
诉求，不应该改写 messages、output 或 usage——否则"schema as workflow"
这条哲学线就破了。

pyxis 的 hook 刻意设计成**只读的观察者**：三个回调（开始、结束、出错），
全局注册，在 Step 的同步、异步、流式三条路径上统一触发。

## API 草图

```python
from pyxis import StepHook, add_hook, clear_hooks

class PrintHook(StepHook):
    def on_start(self, step, messages, model):
        print(f"[{step}] 开始")
    def on_end(self, record):
        usage = record.usage.total_tokens if record.usage else 0
        print(f"[{record.step}] 完成；tokens={usage}")
    def on_error(self, step, messages, model, error):
        print(f"[{step}] 失败：{error}")

add_hook(PrintHook())

# 业务代码完全不变 —— hook 全局生效
plan("x")

clear_hooks()  # 通常只有测试会用
```

## 验收标准

- `StepHook` 是一个普通类，三个方法 `on_start` / `on_end` / `on_error`
  全部默认 no-op。用户按需覆盖。签名固定：
  - `on_start(step: str, messages: list[Message], model: str) -> None`
  - `on_end(record: TraceRecord) -> None`
  - `on_error(step: str, messages: list[Message], model: str, error: str) -> None`
- 注册/注销：`add_hook(hook)`、`remove_hook(hook)`、`clear_hooks()`。
  注册顺序 = 触发顺序（FIFO）。
- `Step.__call__`、`Step.stream`、`AsyncStep.__call__`、`AsyncStep.astream`
  均在调用 client 前触发 `on_start`，写完 TraceRecord 后触发 `on_end`；
  任意异常路径先写 error 记录 → 触发 `on_error` → 重抛。
- 某个 hook 抛异常不应该影响其他 hook 或主流程：框架吞掉异常并在该 hook
  上标记一次（通过 warnings.warn 提示）。
- hook 回调传入的 `messages` 是框架传给 client 的**同一引用**；约定为**只读**
  （用户不得修改）。本轮不做 deep-copy（运行时成本）。
- 流式路径：`on_start` 在开始迭代前调用一次；`on_end` 在流完整消费后
  （写了最终 TraceRecord 之后）调用一次；流中途异常走 `on_error`。

## 不做（留给后续迭代）

- 异步 hook（hook 方法都是同步；如果用户要发网络请求，自己起后台任务）。
- 每 step 粒度的 hook 作用域（目前全局；要作用域可以自己用 `add_hook` /
  `remove_hook` 成对）。
- 在 hook 里修改 messages 或 output（核心哲学拒绝）。
- 向量化/批量 hook 派发（全局 hook 数通常 ≤ 个位数，循环调用已够）。
