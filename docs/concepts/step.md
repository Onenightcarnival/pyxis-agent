# Step：code-as-prompt

`@step` 是 pyxis 里最基本的一个概念——把一个 Python 函数包装成一次类型化的 LLM 调用。

## 最小例子

```python
from pydantic import BaseModel
from pyxis import step

class Summary(BaseModel):
    key_points: list[str]   # 先抽关键点
    one_liner: str          # 再提炼一句话

@step(output=Summary)
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

`@step` 看函数是 `def` 还是 `async def` 自动分派：

```python
@step(output=Summary)
async def summarize_async(article: str) -> str:
    """..."""
    return article

s = await summarize_async("...")
```

- `def` → `Step[T]`
- `async def` → `AsyncStep[T]`
- 接口一致

## 流式输出：看字段被一个个填出来

```python
for partial in summarize.stream(article):
    print(partial)   # Summary 实例，字段从 None 逐步填满
```

- 底层走 instructor 的 `create_partial`
- 一次流消费完写一条完整 `TraceRecord`
- 典型用法：实时 UI、调试 schema 顺序

异步版：

```python
async for partial in summarize_async.astream(article):
    ...
```

## 重试

```python
@step(output=Summary, max_retries=2)
def summarize(article: str) -> str:
    """..."""
    return article
```

- `max_retries` → 转给 instructor，用于**结构化输出校验**失败重试
- 网络错误重试 → 底层 HTTP 客户端，不归这里管

## 换模型、换客户端

```python
from pyxis.providers import openrouter_client

@step(output=Summary, model="google/gemini-2.5-flash", client=openrouter_client())
def summarize(article: str) -> str:
    """..."""
    return article
```

- 不传 `client` → 用 `get_default_client()`
- `set_default_client(...)` 进程启动时设一次，之后所有 `@step` 走它

## 测试：FakeClient

`FakeClient` 按队列顺序吐预置的 Pydantic 实例，单测不碰真 LLM：

```python
from pyxis import FakeClient

client = FakeClient([Summary(key_points=["a"], one_liner="a one-liner")])

@step(output=Summary, client=client)
def summarize(article: str) -> str:
    """..."""
    return article

assert summarize("任意文本").one_liner == "a one-liner"
assert len(client.calls) == 1
```

- 断言 prompt 内容 → `client.calls[i].messages`

## 什么时候不用 Step

- 不走 LLM 的普通动作 → `Tool` 或普通函数
- 多次 LLM 调用的编排 → `@flow`
- 中途要等人类回应 → `ask_human` + 生成器版 `@flow`

---

- 可跑示例：[examples/research.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/research.py) · [examples/streaming_demo.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/streaming_demo.py)
- 完整签名：[API → pyxis.step](../api/step.md)
