# 测试与 FakeClient
单元测试使用 `FakeClient`，不访问真实 LLM。`FakeClient` 按队列顺序返回预置的 Pydantic 实例，并把每次调用记录到 `.calls`。

## 最小例子
```python
from pydantic import BaseModel
from pyxis import FakeClient, step


class Plan(BaseModel):
    goal: str
    next_action: str


fake = FakeClient([Plan(goal="g", next_action="a")])


@step(output=Plan, client=fake, params={"temperature": 0})
def plan(topic: str) -> str:
    """根据主题生成计划。"""
    return topic


result = plan("build x")
assert result == Plan(goal="g", next_action="a")
assert fake.calls[0].messages[-1]["content"] == "build x"
assert fake.calls[0].params == {"temperature": 0}
```

## 适合断言什么

- 输出模型：直接 `==` 比较 Pydantic 实例
- 输入消息：断言 `fake.calls[i].messages`
- provider 参数：断言 `fake.calls[i].params`
- 模型名与重试：断言 `model` / `max_retries`
- 多步普通函数：预置多个响应，再检查调用顺序

## 流式测试
`FakeClient` 支持 sync、async、stream、astream。测试 streaming 时，预置最终模型，再断言 `.stream()` / `.astream()` 产生的 partial 序列。

## 集成测试
真实 LLM 烟雾测试放在 `tests/integration/`。没有 `OPENROUTER_API_KEY` 时测试会 skip。

---

- 完整签名：[API：pyxis.client](../api/client.md)
