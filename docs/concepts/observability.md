# 可观测性

生产环境推荐直接接 [Langfuse](https://langfuse.com)——换一个 import，pyxis
里所有 LLM 调用自动被抓。

测试和本地 debug 用 pyxis 自带的 `trace()` + `FakeClient`。

两套可以同时开，互不干扰。

## 生产：Langfuse 接入

### 1. 装依赖

```bash
uv add langfuse
```

pyxis 本身不依赖 langfuse，用到才装。

### 2. 设环境变量

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://cloud.langfuse.com   # 或自托管地址
```

### 3. 换一个 import

```python
import os

# 关键一行：langfuse 的 drop-in 替代。其他代码不动。
from langfuse.openai import OpenAI, AsyncOpenAI

import instructor
from pyxis import InstructorClient, set_default_client

key = os.environ["OPENROUTER_API_KEY"]
base = "https://openrouter.ai/api/v1"

sync = instructor.from_openai(OpenAI(api_key=key, base_url=base))
async_ = instructor.from_openai(AsyncOpenAI(api_key=key, base_url=base))
set_default_client(InstructorClient(sync, async_))
```

完毕。之后每一次 `@step` 调用都会被 langfuse 自动抓到，包含：

- 完整的 prompt / response
- token 用量与成本
- 响应延迟
- instructor 的 `response_model` schema（作为 trace metadata）

### 把一次 flow 拼成一个 trace

默认每次 LLM 调用是一个独立 trace。想把整个 `@flow` 拼成一棵带嵌套 span 的
trace，用 langfuse 自己的 `@observe()` 装饰 flow：

```python
from langfuse.decorators import observe

@flow
@observe()   # 先 @flow 再 @observe，给整个 flow 开一个外层 span
def research(topic: str):
    return plan_from(analyze(topic))
```

每次 `analyze` / `plan_from` 里的 LLM 调用都会挂在 `research` 父 span 下面。

可跑示例见
[examples/with_langfuse.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/with_langfuse.py)。

## 测试 / 本地 debug：trace()

`trace()` 是一个上下文管理器，把作用域内每次 `@step` 调用记一条：

```python
from pyxis import trace

with trace() as t:
    result = triage("今天糟透了")

print(t.to_json(indent=2))
print(t.total_usage())            # 本次 token 总量
t.to_jsonl("logs/local.jsonl")    # append 一条一行
for e in t.errors():
    print(e.step, e.error)
```

单测里最常用的断言是 `t.records[-1].output == Expected(...)`——Pydantic
实例直接 `==` 比较，不需要跑 LLM。

`@flow` 自带 `.run_traced()`，等价于自动开一个 `trace()`：

```python
result, t = triage.run_traced("...")
```

## 自己接指标 / 告警：StepHook

想接 Prometheus、OpenTelemetry、Slack 告警这种 Langfuse 不覆盖的路径，
用 `StepHook` 注册全局回调——见 [Hook：观察者](hooks.md)。

## 框架不做 dashboard

pyxis 不自建 trace UI。Langfuse / LangSmith / OpenTelemetry 生态已经够好了。
框架只负责把数据暴露出来，拿去哪里画图是应用层的事。

完整签名与字段见 [API 参考 → pyxis.trace](../api/trace.md) 与
[pyxis.hooks](../api/hooks.md)。
