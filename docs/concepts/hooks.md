# Hook：观察者（进阶）

大多数人只需要 [Langfuse](observability.md) 就够了——换一个 import，全站的
LLM 调用都自动被抓。`StepHook` 是留给"Langfuse 满足不了、要自己接
Prometheus / OpenTelemetry / Slack 告警"的场景。

## 长什么样

`StepHook` 有三个回调：

- `on_start(name, messages, model)` —— 调用前
- `on_end(record)` —— 成功后，带完整 `TraceRecord`
- `on_error(name, messages, model, error)` —— 失败后

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

装好以后，每次 `@step` 调用都会走这些回调。不需要改业务代码。

## 只读，不修改

`StepHook` 不能改 `messages` 或 `output`。它是 observer，定位就是观察；
要改 LLM 行为，那是业务代码的事。

## 典型用途

- Prometheus：在 `on_end` 里喂 Counter / Histogram。
- Slack：在 `on_error` 里发卡片。
- OpenTelemetry：`on_start` 起 span，`on_end` 结束；跨 asyncio 用 context
  propagation。

这些都是一个 `class XxxHook(StepHook)` + `add_hook(...)`。

## 管理多个 hook

```python
from pyxis import add_hook, remove_hook, clear_hooks

h = PrometheusHook()
add_hook(h)
...
remove_hook(h)    # 或者
clear_hooks()     # 一般只在测试里用
```

hook 按添加顺序依次调用；一个 hook 抛错不会影响其他 hook。

## Hook vs trace() vs Langfuse

| | `trace()` | `StepHook` | Langfuse |
|---|---|---|---|
| 形态 | 上下文管理器，范围局部 | 全局注册，范围整程 | 全局，换个 import 就启用 |
| 用途 | 单测断言、本地 debug | 自己接指标 / 告警 | 生产 dashboard、回放、告警 |
| 覆盖 | `with trace():` 内的 step | 所有 step | 所有通过 langfuse-wrapped OpenAI 的调用 |

三者可以同时开，互不干扰。

完整签名看 [API 参考 → pyxis.hooks](../api/hooks.md)。
