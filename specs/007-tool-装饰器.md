# 007：`@tool` 装饰器 —— 从函数生成 Tool 子类

## 目的

手写一个 Tool 子类（字段 + `kind` + `run()`）对小工具太啰嗦。`@tool`
把一个普通 Python 函数转成 Tool 子类：

- 类名由函数名 `snake_case → PascalCase` 生成；
- `kind: Literal["..."] = "..."` 以函数名为值自动加上（判别式联合必备）；
- Pydantic 字段从函数签名（类型注解 + 默认值）推出；
- `run()` 直接调用原函数，参数从 `self` 的字段里取。

这让工具的定义与使用回到它本应有的重量：一个函数。

## API 草图

```python
from pyxis import tool

@tool
def search_web(query: str, max_results: int = 10) -> str:
    """在网上搜索一个查询。"""
    return f"搜索 {query}（前 {max_results} 条）"

# search_web 现在是一个 Tool 子类，等价于：
#
#   class SearchWeb(Tool):
#       """在网上搜索一个查询。"""
#       kind: Literal["search_web"] = "search_web"
#       query: str
#       max_results: int = 10
#
#       def run(self) -> str:
#           return f"搜索 {self.query}（前 {self.max_results} 条）"

# 直接拿来跟其他工具组 discriminated union：
from pydantic import Field
from typing import Annotated

@tool
def finish(answer: str) -> str:
    """停止并返回最终答案。"""
    return answer

Action = Annotated[search_web | finish, Field(discriminator="kind")]
```

## 验收标准

- `@tool` 不带括号直接装饰函数时，返回一个 `Tool` 的子类：
  - `__name__` 等于函数名的 PascalCase 形式；
  - `__doc__` 继承自原函数；
  - 含字段 `kind: Literal[fn_name] = fn_name`；
  - 每个函数参数变成 Pydantic 字段；无默认值的为必选，带默认值的沿用默认；
  - 函数参数的类型注解直接成为字段类型；未标注的默认 `str`。
- 实例化后 `run()` 调用原函数，把 `self` 上对应字段作为关键字参数传入。
- `run()` 返回值必须是 `str`；如果原函数返回了其他类型，`run` 用 `str()` 转换。
- 能参与 Pydantic 的 `Annotated[X | Y, Field(discriminator="kind")]` 判别式联合，
  LLM 产出的 JSON 能正确反序列化到对应的 Tool 子类。
- 带 `*args` / `**kwargs` 的函数、positional-only / keyword-only 参数混用的函数：
  目前**不支持**（iter 9 仅覆盖"全普通参数"的函数）；遇到这类签名时
  `@tool` 抛 `TypeError` 并指向官方 `Tool` 子类写法。

## 不做（留给后续迭代）

- `@tool(name=..., kind=...)` 参数化版本。
- 异步工具（`async def` 函数）——由 iter 5 的 `AsyncStep` 体系延伸处理。
- 从 `*args` / `**kwargs` 推字段。
- 自动把工具列表合成 `Action` union（用户自己写 `Annotated[A | B | ..., Field(discriminator="kind")]`，一行而已）。
