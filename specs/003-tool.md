# 003：Tool —— 把动作声明成 schema

## 目的

`Tool` 是一个 `BaseModel`：它的**字段**就是动作的参数，它的 `run()`
就是动作的实现。LLM 通过在 Step 输出 schema 的 `action` 字段里填入一个
判别式联合（discriminated union）成员来选择工具；Python 通过 `isinstance`
+ `.run()` 分派。框架**不**引入 function-calling 协议适配——schema 本身
就是接口，代码负责执行。

这样两层编排不破：
- 隐式：schema 告诉 LLM"下一步必须是这些工具类型之一"；
- 显式：普通 Python 驱动循环，调用 `.run()`，决定继续或停止。

## API 草图

```python
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from pyxis import Tool, step

class SearchWeb(Tool):
    """在网上搜索一个查询。"""
    kind: Literal["search"] = "search"
    query: str

    def run(self) -> str:
        return f"results for {self.query}"

class Finish(Tool):
    """停止并返回最终答案。"""
    kind: Literal["finish"] = "finish"
    answer: str

    def run(self) -> str:
        return self.answer

Action = Annotated[SearchWeb | Finish, Field(discriminator="kind")]

class Decision(BaseModel):
    thought: str
    action: Action

@step(output=Decision)
def decide(question: str, scratch: str) -> str:
    """你是一个 agent，先思考，再挑工具。"""
    return f"Q: {question}\nSCRATCH:\n{scratch}"

# 显式循环 —— 就是 Python：
scratch: list[str] = []
for _ in range(10):
    d = decide(question, "\n".join(scratch))
    scratch.append(f"thought: {d.thought}")
    obs = d.action.run()
    scratch.append(f"obs: {obs}")
    if isinstance(d.action, Finish):
        return obs
```

## 验收标准

- `Tool` 是 `BaseModel` 子类。子类添加字段，覆盖 `run()`。
- 如果子类没有覆盖就调用 `run()`（或直接实例化基类并调用），抛
  `NotImplementedError`，消息里带子类类名。
- `Tool.run()` 返回 `str`（约定，不做运行时强校验）。
- Tool 子类参与判别式联合时，用 `Literal` 类型的 `kind` 字段区分；
  这是标准 Pydantic，框架无需额外魔法。
- Tool 实例出现在某个 Pydantic schema 里时，经 `FakeClient` + `@step`
  可以无损往返。

## 不做（留给后续迭代）

- 从普通 Python 函数自动生成 Tool 子类（iter 9 的 `@tool` 糖会做）。
- 异步工具执行（iter 5 的 async 总体会覆盖）。
- 内置的 agent 循环助手——循环就是用户自己的 `@flow`。
