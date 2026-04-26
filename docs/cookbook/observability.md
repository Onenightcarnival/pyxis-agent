# 可观测
`@step(client=...)` 使用 OpenAI SDK 实例。Langfuse、OpenTelemetry、Datadog、New Relic 等工具可以接在 SDK 层，覆盖每次 step 调用。
pyxis 不提供单独的 trace API。

## Langfuse
```bash
uv add langfuse
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://cloud.langfuse.com
```
`langfuse.openai.OpenAI` 可以直接传给 `client=`：
```python
import os
from langfuse.openai import OpenAI
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
每次调用会记录 messages、response、token、延迟和 schema。
多 step 流程可以在普通编排函数外再加 `@observe`。
```python
from langfuse.decorators import observe
@observe()
def research(topic: str):
    return plan_from(analyze(topic))
```
完整示例：[examples/with_langfuse.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/with_langfuse.py)。

## OpenTelemetry
```bash
uv add opentelemetry-instrumentation-openai
```
```python
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
OpenAIInstrumentor().instrument()
```
之后 `@step` 调用会进入 OTel collector。

## Datadog / New Relic / 其他 APM
按各厂商文档安装 Python agent，OpenAI auto-instrumentation 会覆盖 step 调用。

## 自定义打点：装饰器叠加
```python
import functools
import time
def timed(step_fn):
    @functools.wraps(step_fn)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return step_fn(*args, **kwargs)
        finally:
            print(f"{step_fn.__name__} 用了 {(time.perf_counter() - t0) * 1000:.0f}ms")
    return wrapper
@timed
@step(output=Plan, model="gpt-4o", client=my_client)
def plan(topic: str) -> str: ...
```

## 测试观测逻辑
单元测试使用 [FakeClient](testing.md)，断言 `.calls` 里的 messages、model、params 与 retry 设置。
