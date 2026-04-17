"""Tool 原语：把动作声明成 schema。

一个 `Tool` 就是一个 `BaseModel`：它的字段**就是**动作的参数，它的 `run()`
**就是**动作的实现。LLM 通过在 Step 输出 schema 的 `action` 字段里填入
一个判别式联合成员来选择工具（典型做法是加一个 `Literal` 的 `kind` 字段）；
Python 用 `isinstance` / `action.run()` 分派。

框架**不**内置 function-calling 协议适配——schema 本身就是接口。
"""

from __future__ import annotations

from pydantic import BaseModel


class Tool(BaseModel):
    """LLM 可以发出的动作基类。

    使用方式：
    1. 继承 `Tool`，添加 Pydantic 字段（就是工具的参数）；
    2. 覆盖 `run()`，返回一个字符串作为观测值；
    3. 若要放进判别式联合，加一个 `Literal["..."] = "..."` 的 `kind` 字段。
    """

    def run(self) -> str:
        raise NotImplementedError(f"Tool 子类 {type(self).__name__!r} 必须覆盖 run()")
