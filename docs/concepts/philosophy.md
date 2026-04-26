# 哲学与定位

## 基本设定
pyxis 从函数式思想的视角看待 LLM 调用：把大模型视为一个带自然语言理解能力的函数，输入是一段任务说明，输出是一个 Pydantic 实例。后续逻辑继续用 Python 代码处理这个实例。

## 设计要求
这个设定带来四个要求：

- 输出用 Pydantic 表达
- 测试可以用 `FakeClient` 预置响应并断言结果
- Pydantic schema 是单次调用的主契约，字段顺序表示输出步骤
- 被装饰函数是 input builder，返回值是本次调用的输入消息；装饰后的 step callable 返回 Pydantic 实例；函数 docstring 不进入 LLM 上下文

## schema 不是 prompt 的翻译稿
不要把一段口水 prompt 换个地方放。输出契约应该写成代码。

字段名、字段类型、`Field(description=...)` 和字段顺序，已经说明了要产出什么、先产出什么、可选值是什么。input builder 只放本次调用才有的内容，比如用户原文、业务背景、少量角色设定。不要再用自然语言把 response model 复述一遍：

```python
class Feedback(BaseModel):
    summary: str = Field(description="一句话还原用户说的是什么")
    sentiment: Literal["positive", "neutral", "negative"] = Field(description="用户的情感倾向")
    topic: Literal["shipping", "quality", "app_bug", "price", "service", "other"]
    severity: Literal["low", "medium", "high"] = Field(
        description="阻塞下单/封号 high；体验抱怨 medium；一般吐槽 low"
    )
```

```python
@step(output=Feedback, model=MODEL, client=openrouter)
def extract(text: str) -> str:
    return f"客户反馈原文：{text}"
```

`summary -> sentiment -> topic -> severity` 这条顺序由 schema 声明，不需要在 prompt 里再写“先总结，再判断情感、话题和严重度”。长期生效的规则放字段定义；本次输入的材料放函数返回值。

## 函数式视角
在 pyxis 里，一次 LLM 调用被写成一个函数调用。这个函数边界可组合、可替换，也方便测试。

`@step` 装饰前，函数是普通的 input builder：应用层输入进去，返回本次调用的
user message。`@step` 装饰后，同一个名字绑定到 `Step[T]`：调用它会执行一次
LLM 调用，并返回类型化的 Pydantic 实例。

一次调用的契约由几部分组成：

- 函数签名声明应用层输入
- 函数体声明本次调用的输入文本
- Pydantic schema 声明返回类型和单次调用内部的生成顺序
- 多步 workflow 由 Python 函数组合完成，用 `if` / `for` / 函数组合表达分支和循环
- `FakeClient` 可以把这次 LLM 调用替换成确定性返回，用于单元测试

LLM 的不确定性留在 step 里；step 之外还是普通 Python。

## 范围
下面这些能力交给应用层或其他工具：

- 图式 DSL / YAML pipeline / 节点编辑器
- 通用 agent loop（ReAct、Plan-and-Execute）
- function-calling 协议适配层（pyxis 用 Pydantic 判别式联合表达工具选择）
- 内置 memory / vector store 抽象
- prompt 模板语言
- 全局 registry（显式 import 够用）
- 手写 messages 列表的入口
- client 封装。`@step(client=...)` 使用 `openai.OpenAI` / `AsyncOpenAI`
  或 `instructor.from_openai(...)` 的实例
- 观测体系（trace / usage / hook）。接 Langfuse / OpenTelemetry / APM，
  见 [可观测](../cookbook/observability.md)

多轮对话、assistant 轮次控制、图式编排、长期状态管理，可以使用 OpenAI SDK、LangGraph、Temporal 或业务系统。
