# Tool：action 即 schema

pyxis 里的工具不是装饰器魔法，不是 JSON Schema 清单，也不是 function-calling
的适配层。**工具就是一个带 `run()` 的 Pydantic 模型。**

## 最小例子

```python
from typing import Literal
from pyxis import Tool

class SearchWeb(Tool):
    kind: Literal["search_web"]   # 判别式字段
    query: str

    def run(self) -> str:
        return do_search(self.query)

class ReadFile(Tool):
    kind: Literal["read_file"]
    path: str

    def run(self) -> str:
        return open(self.path).read()
```

工具**就是**这个 `BaseModel` 子类。参数 = 字段；动作 = `run()` 方法。

## 在 @step 里用

```python
from pydantic import BaseModel, Field
from typing import Union

class PlanStep(BaseModel):
    thought: str
    action: SearchWeb | ReadFile = Field(discriminator="kind")

@step(output=PlanStep)
def plan(task: str) -> str:
    """你是一个执行 agent..."""
    return task

step_out = plan("今天巴塞罗那天气")
print(step_out.action.run())   # Python 的 isinstance/方法分派，无需框架介入
```

LLM 在判别式联合里选一个工具（填 `kind` 字段），Python 用 `isinstance` 或者
直接 `action.run()` 来分派。**框架里没有工具注册表**——注册 = `import`。

## `@tool` 装饰器：省样板

手写 `class` + `kind` + 字段有时嫌啰嗦。`@tool` 直接从函数签名生成 `Tool` 子类：

```python
from pyxis import tool

@tool
def search_web(query: str) -> str:
    """搜索网页"""
    return do_search(query)

# search_web 已经是一个 Tool 子类；kind 字面量 = "search_web"；
# 字段 = (query: str)
```

拿到的 `search_web` 可以直接塞进判别式联合里。

## 为什么不用 function-calling 协议？

OpenAI 的 `tools=[...]`、Anthropic 的 `tool_use` 块、Gemini 的 function calling
——每家 provider 协议都不同，格式会变，版本会升。把它们封装成"统一抽象层"
是 LangChain 的路线；pyxis **故意不走**。

因为 Pydantic 判别式联合已经完整表达了"LLM 从 N 个选项里选一个并填参数"这件事。
instructor 帮你把 JSON Schema 给模型；剩下的就是 Python 对象。

好处：

- **跨 provider**：只要 provider 能输出 JSON（现在基本都能），就能跑
- **可测试**：测试里 mock 返回一个 `SearchWeb(kind="search_web", query="x")` 就行
- **可组合**：工具是普通类，继承、组合、类型检查都照常
- **trace 里是对象不是字符串**：`action == SearchWeb(query="x")` 可以直接断言

## 动态工具来自哪里？

- 本地定义的 `Tool` 子类
- `@tool` 装饰出来的
- [MCP 远端工具](mcp.md)——`mcp_toolset` 把远端 schema 翻译成本地 `Tool` 子类

混合注册就是拼 list：

```python
class Action(BaseModel):
    action: NativeTool | FirstMcpTool | SecondMcpTool = Field(discriminator="kind")
```

再传给 `@step(output=...)` 就完事。

完整签名看 [API 参考 → pyxis.tool](../api/tool.md)。
