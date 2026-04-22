# 可观测性

**pyxis 本体不做观测。** 观测由现成的 APM / LLM-ops 工具承担——pyxis
暴露干净的 OpenAI SDK 接口，你想接什么就接什么。

这是刻意的设计：把观测做进框架会变成"造配套"，既卷不过 Langfuse /
OpenTelemetry / Datadog，又会让用户学两套。不如不做。

---

## Langfuse：换一行 `import`

pyxis 的 `@step(client=...)` 吃任何 OpenAI-compatible SDK 实例。
Langfuse 就提供了一个 drop-in 的 `langfuse.openai.OpenAI`——包了
tracing 的同款 API。

```bash
uv add langfuse
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://cloud.langfuse.com
```

```python
import os

from langfuse.openai import OpenAI   # ← 换这一行
from pyxis import step

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

@step(output=Plan, model="gpt-4o", client=client)
def plan(topic: str) -> str:
    """..."""
    return topic
```

每次 `@step` 调用自动被 Langfuse 抓到：完整 prompt / response / token
用量 / 延迟 / `response_model` schema。

把一整个 `@flow` 拼成一棵带嵌套 span 的 trace：用 Langfuse 的 `@observe`
装饰 flow。

```python
from langfuse.decorators import observe
from pyxis import flow

@flow
@observe()
def research(topic: str):
    return plan_from(analyze(topic))
```

可跑示例：[examples/with_langfuse.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/with_langfuse.py)。

---

## OpenTelemetry

`opentelemetry-instrumentation-openai` 一装上就自动 instrument
`openai.OpenAI` / `AsyncOpenAI`——pyxis `@step` 内部就是调这两个。
你不需要对 pyxis 做任何改动。

```bash
uv add opentelemetry-instrumentation-openai
```

```python
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
OpenAIInstrumentor().instrument()
```

后续 `@step` 的所有调用出现在你的 OTel collector 里。

---

## Datadog / New Relic / 其他 APM

这些厂商的 Python agent 都支持 OpenAI SDK 的 auto-instrumentation。装上
agent、按它们的文档配好，`@step` 调用自动进 dashboard——pyxis 不需要
任何适配。

---

## 自己写装饰器（最灵活）

想在 `@step` 外加自定义的计时 / 日志 / Slack 告警？Python 装饰器叠加
就完事：

```python
import time
import functools

def timed(step_fn):
    @functools.wraps(step_fn)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return step_fn(*args, **kwargs)
        finally:
            print(f"{step_fn.__name__} 用了 {(time.perf_counter()-t0)*1000:.0f}ms")
    return wrapper

@timed
@step(output=Plan, model="gpt-4o", client=my_client)
def plan(topic: str) -> str: ...
```

这是 Python 原生的 middleware 模式——pyxis 不发明自己的 hook 协议。

---

## 测试：`FakeClient`

单测环境下零网络，靠 `FakeClient` 预置 Pydantic 响应 + 断言
`FakeClient.calls`：

```python
from pyxis import FakeClient, step

fake = FakeClient([Plan(goal="g", next_action="a")])

@step(output=Plan, client=fake)
def plan(topic: str) -> str:
    """..."""
    return topic

result = plan("build x")
assert result == Plan(goal="g", next_action="a")

# 想断言调用细节？用 fake.calls
assert fake.calls[0].model == "gpt-4o-mini"
assert fake.calls[0].messages[-1]["content"] == "build x"
assert fake.calls[0].params == {"temperature": 0}   # 如果 @step 传了 params
```

每次调用都写入 `fake.calls`，字段覆盖 messages / response_model / model /
max_retries / params。
