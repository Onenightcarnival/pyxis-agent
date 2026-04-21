# Hook：观察者（进阶）

- 大多数人只需要 [Langfuse](observability.md)
- `StepHook` 是给"Langfuse 不覆盖、要自己接 Prometheus / OpenTelemetry / Slack 告警"用的

## 长什么样

三个回调：

- `on_start(name, messages, model)` — 调用前
- `on_end(record)` — 成功后，带完整 `TraceRecord`
- `on_error(name, messages, model, error)` — 失败后

```python
from pyxis import StepHook, add_hook

class PrometheusHook(StepHook):
    def on_end(self, record):
        step_latency.labels(step=record.step).observe(record.duration_ms)
        if record.usage:
            tokens_total.labels(step=record.step).inc(record.usage.total_tokens)

    def on_error(self, name, messages, model, error):
        errors_total.labels(step=name, model=model).inc()

add_hook(PrometheusHook())
```

装好以后每次 `@step` 调用走这些回调，无需改业务代码。

## 只读，不修改

- `StepHook` 不能改 `messages` 或 `output`
- 它是 observer，定位就是观察
- 要改 LLM 行为 → 业务代码的事

## 典型用途

- **Prometheus** — `on_end` 喂 Counter / Histogram
- **Slack** — `on_error` 发卡片
- **OpenTelemetry** — `on_start` 起 span，`on_end` 结束；跨 asyncio 用 context propagation

都是 `class XxxHook(StepHook)` + `add_hook(...)`。

## 管理多个 hook

```python
from pyxis import add_hook, remove_hook, clear_hooks

h = PrometheusHook()
add_hook(h)
...
remove_hook(h)    # 或
clear_hooks()     # 一般只在测试里用
```

- 按添加顺序依次调用
- 一个 hook 抛错不影响其他

## Hook vs trace() vs Langfuse

| | `trace()` | `StepHook` | Langfuse |
|---|---|---|---|
| 形态 | 上下文管理器，范围局部 | 全局注册，范围整程 | 全局，换 import 即启用 |
| 用途 | 单测断言 · 本地 debug | 自己接指标 / 告警 | 生产 dashboard · 回放 · 告警 |
| 覆盖 | `with trace():` 内的 step | 所有 step | 所有走 langfuse-wrapped OpenAI 的调用 |

三者可同时开，互不干扰。

---

完整签名：[API → pyxis.hooks](../api/hooks.md)
