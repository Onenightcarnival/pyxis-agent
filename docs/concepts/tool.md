# Tool：action 即 schema

pyxis 里的工具是一个带 `run()` 方法的 Pydantic 模型——参数是字段，动作是
`run()` 方法。

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

工具就是这个 `BaseModel` 子类。

## 在 @step 里用

```python
from pydantic import BaseModel, Field
from typing import Annotated

class PlanStep(BaseModel):
    thought: str
    action: Annotated[SearchWeb | ReadFile, Field(discriminator="kind")]

@step(output=PlanStep)
def plan(task: str) -> str:
    """你是一个执行 agent..."""
    return task

step_out = plan("今天巴塞罗那天气")
print(step_out.action.run())   # Python 的 isinstance/方法分派
```

LLM 在判别式联合里选一个工具（填 `kind`），Python 用 `isinstance` 或者
直接 `action.run()` 分派。框架里没有工具注册表——注册 = `import`。

## `@tool` 装饰器：省样板

手写 `class` + `kind` + 字段有时嫌啰嗦。`@tool` 从函数签名直接生成
`Tool` 子类：

```python
from pyxis import tool

@tool
def search_web(query: str) -> str:
    """搜索网页"""
    return do_search(query)

# search_web 已经是一个 Tool 子类，kind = "search_web"，字段 = (query: str)
```

拿到的 `search_web` 可以直接塞进判别式联合。

## 工具来自哪里

- 本地定义的 `Tool` 子类
- `@tool` 装饰出来的
- [MCP 远端工具](mcp.md)——`mcp_toolset` 把远端 schema 翻译成本地 `Tool` 子类

混合注册就是拼 list：

```python
class Action(BaseModel):
    action: Annotated[
        NativeTool | FirstMcpTool | SecondMcpTool,
        Field(discriminator="kind"),
    ]
```

再传给 `@step(output=...)` 就完事。

可跑示例：
[examples/agent_tool_use.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/agent_tool_use.py)、
[examples/plan_then_execute.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/plan_then_execute.py)。
完整签名见 [API 参考 → pyxis.tool](../api/tool.md)。
