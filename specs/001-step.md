# 001：Step —— 单次 LLM 调用 + 结构即思维链

## 目的

`Step` 封装一次 LLM 调用。它的推理过程由 Pydantic 输出模型的字段顺序声明
（隐式 CoT）；函数的 docstring 是 system prompt，返回值是 user message
（code-as-prompt）。

## API 草图

```python
from pydantic import BaseModel, Field
from pyxis import step, FakeClient, set_default_client

class Plan(BaseModel):
    goal: str = Field(description="复述用户请求")
    subtasks: list[str] = Field(description="拆成具体子任务")
    next_action: str = Field(description="挑出第一步要执行的")

@step(output=Plan)
def plan(request: str) -> str:
    """你是严谨的规划者，产出 JSON 格式的计划。"""
    return f"Request: {request}"

# 生产
set_default_client(InstructorClient())  # 默认 OpenAI 后端
result: Plan = plan("搭一个 todo app")

# 测试
fake = FakeClient([Plan(goal="g", subtasks=[], next_action="a")])
result = plan_with_fake("搭个 x")       # 装饰器传入 client=fake
assert fake.calls[0].messages[0]["role"] == "system"
```

## 验收标准

- `@step(output=M)` 把函数包成可调用对象，返回类型为 `M`。
- 被包装的 callable 保留原函数的 `__name__` 与 `__doc__`。
- 调用时消息构造顺序：`system` = 去空白 docstring（空则省略）；`user` =
  函数返回的字符串。顺序固定。
- Client 解析优先级：`@step(client=...)` > `set_default_client` 设置的全局
  默认 > 懒构造的 `InstructorClient()`（需要 OpenAI 环境变量）。
- `FakeClient(responses=[...])` 行为：
  - 按队列顺序返回预置响应；
  - 每次调用都写入 `.calls`（messages, response_model, model）；
  - 用尽后抛 `RuntimeError`；
  - 预置响应与目标模型不匹配抛 `TypeError`。
- `@step(model=...)` 转发给 client；默认 `"gpt-4o-mini"`。

## 不做（留给后续迭代）

- 流式、异步、工具调用、重试、成本核算、消息列表形式的 prompt。
