"""Tool 原语：把动作声明成 schema。

一个 `Tool` 就是一个 `BaseModel`：它的字段**就是**动作的参数，它的 `run()`
**就是**动作的实现。LLM 通过在 Step 输出 schema 的 `action` 字段里填入
一个判别式联合成员来选择工具（典型做法是加一个 `Literal` 的 `kind` 字段）；
Python 用 `isinstance` / `action.run()` 分派。

`@tool` 装饰器把一个普通 Python 函数自动转成 Tool 子类，参数推为字段、
函数名推为 `kind` 字面量、函数本体接管 `run()` —— 小工具的定义成本降到
"就是一个函数"。
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, create_model


class Tool(BaseModel):
    """LLM 可以发出的动作基类。

    使用方式：
    1. 继承 `Tool`，添加 Pydantic 字段（就是工具的参数）；
    2. 覆盖 `run()`，返回一个字符串作为观测值；
    3. 若要放进判别式联合，加一个 `Literal["..."] = "..."` 的 `kind` 字段。

    如果工具的形态就是"一个普通函数"，直接用 `@tool` 装饰器更省事。
    """

    def run(self) -> str:
        raise NotImplementedError(f"Tool 子类 {type(self).__name__!r} 必须覆盖 run()")


def _snake_to_pascal(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


def tool(fn: Callable[..., Any]) -> type[Tool]:
    """把一个普通函数转成 Tool 子类。

    - 类名：函数名的 PascalCase 形式。
    - `kind`：`Literal[函数名] = 函数名` 自动加上，判别式联合开箱即用。
    - 字段：函数的每个普通参数变成一个 Pydantic 字段；无默认值 → 必选，
      有默认值 → 沿用；无类型注解 → 按 `str` 推断。
    - `run()`：实例化后的 `.run()` 直接调原函数；非字符串返回用 `str()` 转。

    目前不支持 `*args` / `**kwargs`，遇到会抛 `TypeError` 指向手写 `Tool` 子类。
    """
    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn)

    fields: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise TypeError(
                f"@tool 不支持 *args / **kwargs 形参（函数 {fn.__name__!r}）；"
                f"请直接继承 Tool 手写字段。"
            )
        annotation = hints.get(name, str)
        default = param.default if param.default is not inspect.Parameter.empty else ...
        fields[name] = (annotation, default)

    kind_value = fn.__name__
    fields["kind"] = (Literal[kind_value], kind_value)  # type: ignore[valid-type]

    class_name = _snake_to_pascal(fn.__name__)
    param_names = [
        n
        for n, p in sig.parameters.items()
        if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]

    def run(self: Tool) -> str:
        kwargs = {n: getattr(self, n) for n in param_names}
        result = fn(**kwargs)
        return result if isinstance(result, str) else str(result)

    tool_cls = create_model(class_name, __base__=Tool, **fields)
    tool_cls.run = run  # type: ignore[method-assign]
    tool_cls.__doc__ = fn.__doc__
    return tool_cls
