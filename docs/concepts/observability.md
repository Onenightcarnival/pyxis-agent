# 可观测性

`@step(client=...)` 吃 OpenAI SDK 实例；APM / LLM-ops 工具直接
instrument 这层就覆盖每次调用。框架自己不维护 trace / usage / hook。

## Langfuse

```bash
uv add langfuse
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://cloud.langfuse.com
```

`langfuse.openai.OpenAI` 是 OpenAI SDK 的 drop-in，直接塞给 `client=`：

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

每次调用写一条 trace：prompt / response / token / 延迟 / schema。

把多 step 合并成一棵 trace：`@flow` 外再套 `@observe`。

```python
from langfuse.decorators import observe
from pyxis import flow

@flow
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

之后 `@step` 调用进 OTel collector。

## Datadog / New Relic / 其他 APM

按各厂商文档装 Python agent，OpenAI auto-instrumentation 自动覆盖。

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

## 测试：`FakeClient`

零网络。按队列吐预置 Pydantic 实例，`.calls` 记录每次调用：

```python
from pyxis import FakeClient, step

fake = FakeClient([Plan(goal="g", next_action="a")])

@step(output=Plan, client=fake)
def plan(topic: str) -> str:
    """..."""
    return topic

result = plan("build x")
assert result == Plan(goal="g", next_action="a")
assert fake.calls[0].messages[-1]["content"] == "build x"
assert fake.calls[0].params == {"temperature": 0}
```
