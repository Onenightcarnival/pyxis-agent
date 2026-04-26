# Tool：action 即 schema
pyxis 的工具是带 `run()` 方法的 Pydantic 模型。字段是参数，`run()` 执行动作。

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
每个 `Tool` 子类对应一个动作。

## 在 @step 里用
```python
from pydantic import BaseModel, Field
from typing import Annotated
class PlanStep(BaseModel):
    thought: str
    action: Annotated[SearchWeb | ReadFile, Field(discriminator="kind")]
@step(output=PlanStep)
def plan(task: str) -> str:
    return f"请为这个任务选择下一步动作：{task}"
step_out = plan("今天巴塞罗那天气")
print(step_out.action.run())   # isinstance / 方法分派
```

- LLM 通过 `kind` 选择工具
- Python 调用 `action.run()` 执行动作
- 工具通过普通 Python import 使用

## `@tool` 装饰器：省样板
简单函数可以用 `@tool` 转成工具类：
```python
from pyxis import tool
@tool
def search_web(query: str) -> str:
    """搜索网页"""
    return do_search(query)
# search_web 已是 Tool 子类：kind = "search_web"，字段 = (query: str)
```
生成的 `search_web` 可以直接放进判别式联合。

## 工具来自哪里

- 本地 `Tool` 子类
- `@tool` 装饰的
- [MCP 远端工具](../cookbook/mcp.md) — `mcp_toolset` 把远端 schema 翻成本地 `Tool` 子类
本地工具和 MCP 工具可以放在同一个联合类型里：
```python
class Action(BaseModel):
    action: Annotated[
        NativeTool | FirstMcpTool | SecondMcpTool,
        Field(discriminator="kind"),
    ]
```
然后传给 `@step(output=...)`。

---

- 可跑示例：[examples/agent_tool_use.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/agent_tool_use.py) · [examples/plan_then_execute.py](https://github.com/Onenightcarnival/pyxis-agent/blob/main/examples/plan_then_execute.py)
- 完整签名：[API：pyxis.tool](../api/tool.md)
