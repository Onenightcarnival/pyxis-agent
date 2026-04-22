# Step：code-as-prompt

`@step` 是 pyxis 里最基本的一个概念——把一个 Python 函数包装成一次类型化的 LLM 调用。

## 最小例子

```python
from openai import OpenAI
from pydantic import BaseModel
from pyxis import step

client = OpenAI(api_key="sk-...")

class Summary(BaseModel):
    key_points: list[str]   # 先抽关键点
    one_liner: str          # 再提炼一句话

@step(output=Summary, model="gpt-4o", client=client)
def summarize(article: str) -> str:
    """你是一个简洁明了的摘要器。

    先抽关键点，再用一句话概括。不要堆砌修辞。
    """
    return article

s = summarize("Python 3.12 新增 PEP 695 泛型语法...")
print(s.one_liner)
```

两件事：

- `summarize` 的 docstring → **system prompt**
- `summarize(article)` 的返回值 → **user message**

函数本身就是 prompt，没有模板层。

## 字段顺序就是思维链

`Summary` 先 `key_points` 再 `one_liner` → instructor 让 LLM 按声明顺序填 → 先发散（抽点）再收敛（一句话）。

颠倒顺序：

```python
class SummaryReversed(BaseModel):
    one_liner: str          # 先一句话
    key_points: list[str]   # 再补关键点
```

行为会变差：LLM 先塞一个模糊的一句话，再用关键点"自圆其说"。改字段顺序等于改思维链。

## 同步 vs 异步

`@step` 看函数是 `def` 还是 `async def` 自动分派，client 要匹配：

```python
from openai import AsyncOpenAI

aclient = AsyncOpenAI(api_key="sk-...")

@step(output=Summary, model="gpt-4o", client=aclient)
async def summarize_async(article: str) -> str:
    """..."""
    return article

s = await summarize_async("...")
```

- `def` + `OpenAI` → `Step[T]`
- `async def` + `AsyncOpenAI` → `AsyncStep[T]`
- sync / async 错配会立即 `TypeError`——不隐式转换

## 流式输出：看字段被一个个填出来

```python
for partial in summarize.stream(article):
    print(partial)   # Summary 实例，字段从 None 逐步填满
```

- 底层走 instructor 的 `create_partial`
- 典型用法：实时 UI、调试 schema 顺序

异步版：

```python
async for partial in summarize_async.astream(article):
    ...
```

## 重试

```python
@step(output=Summary, model="gpt-4o", client=client, max_retries=2)
def summarize(article: str) -> str:
    """..."""
    return article
```

- `max_retries` → 转给 instructor，用于**结构化输出校验**失败重试
- 网络错误重试 → 底层 HTTP 客户端，不归这里管

## 采样参数：`params`

`params` 是一个字典，哑透传给 provider API（`temperature` / `max_tokens`
/ `seed` / `top_p` / `stop` / ...）。pyxis 不枚举、不校验，所以 provider
原生支持什么参数就能传什么。

```python
@step(
    output=Route,
    model="gpt-4o-mini",
    client=client,
    params={"temperature": 0, "max_tokens": 200},   # 路由 step 要确定性
)
def route(user_input: str) -> str:
    """..."""
    return user_input
```

不同 `@step` 可以用不同的 `params`——路由要 `temperature=0`，creative
要 `temperature=0.9`。

## 客户端：直接吃 OpenAI SDK 实例

`client` 是必填参数。吃两种东西之一：

```python
# ① 原生 OpenAI SDK（最常见）
from openai import OpenAI, AsyncOpenAI
sync_client = OpenAI(base_url="...", api_key="...")
async_client = AsyncOpenAI(base_url="...", api_key="...")

# ② 已经 patch 过的 instructor 实例（例如接 Langfuse）
import instructor
traced_client = instructor.from_openai(some_langfuse_openai)
```

pyxis 内部自动把原生 OpenAI 实例懒 patch 成 instructor。不传 `client`
会立即 `TypeError`——没有"默认 client"这回事，你业务代码里的 client
就是 client。

想接 OpenRouter / Ollama / 自己的 OpenAI-compatible proxy？就是换
`base_url`：

```python
openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
```

## 测试：FakeClient

`FakeClient` 按队列顺序吐预置的 Pydantic 实例，单测不碰真 LLM：

```python
from pyxis import FakeClient

fake = FakeClient([Summary(key_points=["a"], one_liner="a one-liner")])

@step(output=Summary, client=fake)
def summarize(article: str) -> str:
    """..."""
    return article

assert summarize("任意文本").one_liner == "a one-liner"
assert len(fake.calls) == 1
assert fake.calls[0].messages[-1]["content"] == "任意文本"
```

- 断言 prompt 内容 → `fake.calls[i].messages`
- 断言采样参数 → `fake.calls[i].params`

## 什么时候不用 Step

- 不走 LLM 的普通动作 → `Tool` 或普通函数
- 多次 LLM 调用的编排 → `@flow`
- 中途要等人类回应 → `ask_human` + 生成器版 `@flow`

---

- 可跑示例：[examples/research.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/research.py) · [examples/streaming_demo.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/streaming_demo.py)
- 完整签名：[API → pyxis.step](../api/step.md)
