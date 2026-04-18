# 接入 Langfuse：托管级可观测性（零侵入）

pyxis 自带的可观测性刻意做得**轻**：`trace()` / `TraceRecord` / `to_jsonl`
够测试、够本地 debug、够往自家日志管道里推。但生产环境通常想要的是：
Web dashboard、检索、告警、跨服务拼接 trace 层级——**这些就交给
[Langfuse](https://langfuse.com)**，它原生支持 OpenAI SDK 和 instructor。

本页说清楚两件事：
1. **为什么 pyxis 不把 langfuse 做进框架**：因为 langfuse 已经做对了。
2. **怎么两行接进去**：换一个 import，环境变量设好，完事。

## 两层可观测性：各司其职

| 层 | 工具 | 关心什么 | 什么场景 |
|----|------|---------|----------|
| 框架层 | pyxis `trace()` / `TraceRecord` / `StepHook` | Step 名、Pydantic schema、flow 结构、错误可见性 | 单测断言、本地 debug、自家日志 |
| LLM 层 | Langfuse（或 OpenTelemetry） | 原始 prompt、response、token、延迟、多 trace 拼接 | 生产 dashboard、回归分析、告警 |

这两层**不重叠**、**不冲突**、**可以同时开**。pyxis 不打算再造第二个
dashboard——世上已经有 Langfuse 了。

## 接入步骤

### 1. 装依赖

```bash
uv add langfuse
```

pyxis 本身不依赖 langfuse；你想用才装。

### 2. 设环境变量

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://cloud.langfuse.com   # 或自托管地址
```

### 3. 用 langfuse 包装过的 OpenAI import

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

完毕。此后每一次 `@step` 调用都会被 langfuse 自动抓到，包含：

- 完整的 prompt / response
- token 用量与成本
- 响应延迟
- instructor 的 `response_model` schema（作为 trace metadata）

pyxis 自己的 `trace()` 也正常工作——两套同时在。

## 嵌套：把一次 flow 拼成一个 langfuse trace

默认情况下每次 LLM 调用是一个独立的 trace。如果想把整个 `@flow` 拼成
一个带嵌套 span 的 langfuse trace，用 langfuse 自己的 `@observe()` 装饰
flow：

```python
from langfuse.decorators import observe

@flow
@observe()   # 先 @flow 再 @observe，等价于给整个 flow 开一个外层 span
def research(topic: str):
    return plan_from(analyze(topic))
```

每次 `analyze` / `plan_from` 里的 LLM 调用都会自动嵌在 `research` 这个
父 span 下面，在 langfuse dashboard 里就是一棵树。

## 和 pyxis `trace()` 一起用

```python
with trace() as t:
    research("x")

# pyxis 本地 trace：
print(t.to_json(indent=2))        # 拿到 Step 名 + Pydantic schema
print(t.total_usage())            # 本地 token 汇总
t.to_jsonl("logs/local.jsonl")    # 推本地日志

# langfuse 那边是另一条并行链路，不需要你额外做任何事：
# 去 langfuse dashboard 看就行。
```

## 为什么 pyxis 不直接把 langfuse 作为依赖

- **provider 无关**：pyxis 也能接 Anthropic、自建 OpenAI-兼容接口、
  未来的任何 provider。把 langfuse 绑成必装依赖，会让不用 langfuse 的
  用户也吃这个依赖。
- **哲学上**：langfuse 已经做完了"LLM 层可观测性"这件事——**别重复造**。
  pyxis 的差异化价值在 schema-as-CoT + 纯 Python 编排，不是再造一个
  dashboard。
- **升级独立**：langfuse 有自己的版本演进节奏；pyxis 不把它绑进来，
  你升 langfuse 的时候不用跟 pyxis 协调。

## 可运行示例

完整的可跑示例见 [examples/with_langfuse.py](../examples/with_langfuse.py)；
装了 langfuse 就能跑，没装就友好提示并退出。
