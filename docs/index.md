# pyxis-agent
**用 Python 函数和 Pydantic schema 写 agent。**
> schema as workflow

---

## 适用场景
pyxis 让 LLM 输出 Pydantic 实例，再交给下一段 Python 代码处理。页面、气泡、报告等给人看的内容，由应用层从字段里渲染。
适合：

- 数据 pipeline 里的 LLM 节点
- 需要回归测试的业务 agent
- 多个 agent 之间的结构化协作
- LLM 产出需要入库、统计或审计的场景
如果主要需求是聊天界面的流畅体验、prompt 自动调优或图式工作流，可以先看 [与其他框架对比](comparison.md)。

---

## 安装
```bash
uv add pyxis-agent
# 或
pip install pyxis-agent
```
Python 3.12+。

---

## 30 秒看懂
```python
from openai import OpenAI
from pydantic import BaseModel, Field
from pyxis import step

client = OpenAI(api_key="sk-...")


class Verdict(BaseModel):
    """情感判定结果。字段顺序就是单次调用内部的生成顺序。"""

    sentiment: str = Field(description="判断文本情感：positive / negative / neutral")
    confidence: float = Field(description="给出 0-1 之间的置信度")


@step(output=Verdict, model="gpt-4o-mini", client=client)
def classify(text: str) -> str:
    return f"请判断这段文本的情感倾向：{text}"


v = classify("今天简直完美")
assert v.sentiment == "positive"
```
这个函数会生成一次结构化 LLM 调用：

- `Verdict` 是结构化契约，字段顺序决定输出顺序
- 函数体是 input builder，`-> str` 表示它只负责加工本次调用的 user message
- 被 `@step` 装饰后，`classify` 绑定到 `Step[Verdict]`；调用 `classify(...)`
  会完成 LLM 调用，返回 `Verdict` 实例

- 函数 docstring 只用于 Python 文档，不进入 LLM 上下文

---

## 两层编排

| 范围 | 机制 | 职责 |
|---|---|---|
| 单次 LLM 调用 | `@step` + Pydantic schema | 生成结构化输出 |
| 多次 LLM 调用 | 普通 Python 函数 | 组合、分支、循环 |
多步逻辑直接写 Python：
```python
def triage(text: str) -> str:
    v = classify(text)
    if v.confidence < 0.6:
        return escalate(text)  # 另一个 @step
    return auto_reply(v.sentiment, text)  # 另一个 @step
```

---

## 核心概念一览

| 概念 | 做什么 | 详见 |
|---|---|---|
| `@step` | 一次 LLM 调用（同步 / 异步 / 流式都有） | [概念](concepts/step.md) · [API](api/step.md) |
| `Tool` / `@tool` | 工具 = `BaseModel` + `run() -> str` | [概念](concepts/tool.md) · [API](api/tool.md) |
| Interrupt / `ask_interrupt` | 生成器挂起，等待外部输入后继续 | [Cookbook](cookbook/interrupt.md) · [API](api/interrupt.md) |
| `mcp_toolset` | MCP 远端工具翻成本地 `Tool` 子类 | [Cookbook](cookbook/mcp.md) · [API](api/mcp.md) |
| 可观测性 | 接 Langfuse / OTel / APM；测试用 `FakeClient` | [Cookbook](cookbook/observability.md) |

---

## 下一步

| 想做的事 | 去 |
|---|---|
| 找可运行示例 | [Cookbook](cookbook/index.md) |
| 了解核心 API | [概念](concepts/index.md) |
| 看设计边界 | [哲学与定位](concepts/philosophy.md) |
| 查类型和签名 | [API 参考](api/step.md) |
