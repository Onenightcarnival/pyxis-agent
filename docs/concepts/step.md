# Step：schema-first 的单次调用
`@step` 把 Python 函数包装成一次结构化 LLM 调用。

## 最小例子
```python
from openai import OpenAI
from pydantic import BaseModel, Field
from pyxis import step

client = OpenAI(api_key="sk-...")


class Summary(BaseModel):
    """简洁摘要。先抽关键点，再提炼一句话。"""

    key_points: list[str] = Field(description="从文章里抽取 3-5 个关键点")
    one_liner: str = Field(description="基于关键点写一句话摘要，不堆砌修辞")


@step(output=Summary, model="gpt-4o", client=client)
def summarize(article: str) -> str:
    return f"请摘要这篇文章：\n{article}"


s = summarize("Python 3.12 新增 PEP 695 泛型语法...")
print(s.one_liner)
```
调用时：

- `output=Summary` 是这次调用的结构化契约
- `Summary` 的字段名、类型、字段说明和字段顺序会进入结构化输出约束
- 函数体是 input builder，`-> str` 表示它只负责加工本次调用的 `user` message
- 被 `@step` 装饰后，`summarize` 绑定到 `Step[Summary]`；调用
  `summarize(article)` 会完成 LLM 调用，返回 `Summary` 实例

- `summarize` 的 docstring 只用于 Python 文档，不进入 LLM 上下文
如果要给模型更多任务说明，优先写进 Pydantic schema；与本次输入强相关的上下文，
写进函数返回的字符串。

## code as contract
pyxis 里的 code-as-contract 不是“把 prompt 藏在 docstring 里”，而是：

- `BaseModel` / `Field(description=...)` 描述输出契约
- 字段顺序声明单次调用内部的生成步骤
- 函数签名声明应用层输入
- input builder 的返回值把这次调用的业务上下文序列化成 `user` message
- 装饰后的 step callable 返回 Pydantic 实例
这让 LLM 调用契约变成可测试、可审计、可复用的 Python 类型，而不是一段游离的模板文本。

## 字段顺序
Pydantic 字段顺序会影响结构化输出的生成顺序。下面的 `Summary` 会先生成 `key_points`，再生成 `one_liner`。
颠倒顺序：
```python
class SummaryReversed(BaseModel):
    one_liner: str  # 先一句话
    key_points: list[str]  # 再补关键点
```
这会让模型先写一句话，再补关键点。需要先收集材料再下结论时，不要这样排。

## 同步 vs 异步
`@step` 根据函数类型返回同步或异步 step。client 要匹配函数类型：
```python
from openai import AsyncOpenAI

aclient = AsyncOpenAI(api_key="sk-...")


@step(output=Summary, model="gpt-4o", client=aclient)
async def summarize_async(article: str) -> str:
    return article


s = await summarize_async("...")
```

- `def` + `OpenAI` 返回 `Step[T]`
- `async def` + `AsyncOpenAI` 返回 `AsyncStep[T]`
- sync / async 不匹配会抛 `TypeError`

## 流式输出
```python
for partial in summarize.stream(article):
    print(partial)  # Summary 实例，字段从 None 逐步填满
```

- 底层使用 instructor 的 `create_partial`
- 适合实时 UI 和调试 schema 顺序
异步版：
```python
async for partial in summarize_async.astream(article):
    ...
```

## 重试
```python
@step(output=Summary, model="gpt-4o", client=client, max_retries=2)
def summarize(article: str) -> str:
    return article
```

- `max_retries` 会传给 instructor，用于结构化输出校验失败后的重试
- 网络错误重试由底层 HTTP 客户端处理

## 采样参数：`params`
`params` 是一个字典，透传给 provider API（`temperature` / `max_tokens`
/ `seed` / `top_p` / `stop` / ...）。
```python
@step(
    output=Route,
    model="gpt-4o-mini",
    client=client,
    params={"temperature": 0, "max_tokens": 200},
)
def route(user_input: str) -> str:
    return user_input
```
可以给不同 step 设置不同参数，例如路由 step 用 `temperature=0`，生成类 step 用更高温度。

## 客户端
`client` 必填，支持两类实例：
```python
# ① 原生 OpenAI SDK
from openai import OpenAI, AsyncOpenAI

sync_client = OpenAI(base_url="...", api_key="...")
async_client = AsyncOpenAI(base_url="...", api_key="...")
# ② instructor 已 patch 的实例（例如接 Langfuse）
import instructor

traced_client = instructor.from_openai(some_langfuse_openai)
```
原生实例会在第一次调用时转换成 instructor client。`def` / `async def` 与 client 类型不匹配时会抛 `TypeError`。
OpenRouter、Ollama 或其他 OpenAI-compatible provider 可以通过 `base_url` 接入：
```python
openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
```

## 测试：FakeClient
`FakeClient` 按队列顺序返回预置的 Pydantic 实例，单元测试不需要访问真实 LLM：
```python
from pyxis import FakeClient

fake = FakeClient([Summary(key_points=["a"], one_liner="a one-liner")])


@step(output=Summary, client=fake)
def summarize(article: str) -> str:
    return article


assert summarize("任意文本").one_liner == "a one-liner"
assert len(fake.calls) == 1
assert fake.calls[0].messages[-1]["content"] == "任意文本"
```

- 断言输入消息：`fake.calls[i].messages`
- 断言采样参数：`fake.calls[i].params`

## 什么时候不用 Step

- 不走 LLM 的普通动作：`Tool` 或普通函数
- 多次 LLM 调用的编排：普通 Python 函数
- 中途要等外部输入：Cookbook 里的 [Interrupt](../cookbook/interrupt.md)

---

- 可跑示例：[examples/research.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/research.py) · [examples/streaming_demo.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/streaming_demo.py)
- 完整签名：[API：pyxis.step](../api/step.md)
