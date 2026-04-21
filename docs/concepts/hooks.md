# Hook：观察者

`StepHook` 是**只读观察者中间件**，给每次 `@step` 调用加三个回调：

- `on_start(name, messages, model)` —— 调用前
- `on_end(record)` —— 成功后（带完整 `TraceRecord`）
- `on_error(name, messages, model, error)` —— 失败后

## 典型用法

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

装好以后，框架里**每次** `@step` 调用都会走这些回调。不需要改业务代码。

## 观察者 ≠ 中间件

pyxis 的 hook **故意不能**修改 `messages` 或 `output`。它是 observer，不是
middleware——防止业务行为被"插件"悄悄改写。

要改 LLM 行为？那是业务代码，不是 hook 能做的事。

## 接 Prometheus / Slack / OpenTelemetry

- Prometheus：在 `on_end` 里喂 Counter / Histogram
- Slack：在 `on_error` 里发卡片
- OpenTelemetry：在 `on_start` 起 span，`on_end` 结束；跨 asyncio 用 context
  propagation

这些都是一个 `class XxxHook(StepHook)` + `add_hook(...)`。

## 管理多个 hook

```python
from pyxis import add_hook, remove_hook, clear_hooks

h = PrometheusHook()
add_hook(h)
...
remove_hook(h)    # 或者
clear_hooks()     # 通常只在测试里用
```

hook 按**添加顺序**依次调用；一个 hook 抛错不会影响其他 hook。

## Hook vs trace()

| | `trace()` | Hook |
|---|---|---|
| 形态 | 上下文管理器，范围局部 | 全局注册，范围整程 |
| 用途 | 一次 flow 执行的记录 / 导出 | 接外部系统：指标、告警、分布式追踪 |
| 范围 | 只覆盖 `with trace():` 内 | 所有 `@step` 调用 |

两者**可以同时开**。trace 给你"这次调用的完整证据"；hook 给你"长期的运行
时观测"。

完整签名看 [API 参考 → pyxis.hooks](../api/hooks.md)；接 Langfuse 的详细做法在[附录](../langfuse.md)。
