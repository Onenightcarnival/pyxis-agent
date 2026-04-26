# pyxis-agent

**声明式思维链的 Python agent 框架 —— agent-for-machine 阵营。**

> **`声明式思维链 = schema as workflow`**

**完整文档**：<https://onenightcarnival.github.io/pyxis-agent/>

---

## 一句话

- LLM = 带自然语言理解能力的**结构化数据生成器**
- 每次调用直出一个 Pydantic 实例，下一段 Python 代码直接消费
- `@step` 把一次 LLM 调用收束成可组合、可替换、可测试的 **AI 函数**
- `Tool` / `@tool` 把外部动作表达成可被 LLM 选择、可由 Python 执行的 schema
- 多步编排直接写普通 Python 函数
- 给人看的内容由应用层从字段里拼

**适合**：数据 pipeline 里的 LLM 节点 · 要回归测试的业务 agent · 多 agent 机器对机器协作。
**不适合**：丝滑聊天 UI（用 Claude Desktop / ChatGPT 更顺手）。

## 安装
```bash
uv add pyxis-agent
# 或
pip install pyxis-agent
```

Python 3.12+。

## 30 秒上手
```python
from openai import OpenAI
from pydantic import BaseModel, Field
from pyxis import step

client = OpenAI(api_key="sk-...")  # 就是 OpenAI SDK 你已经熟的那个


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

两件事同时发生：

- **schema as workflow** — `Verdict` 字段顺序（`sentiment` 在 `confidence` 前）= LLM 的思维链
- **code as contract** — Pydantic 字段、函数签名和函数体返回的输入文本共同定义这次调用；docstring 不进入 LLM 上下文

注意这里有两层类型：`classify` 的函数体是 input builder，`-> str` 表示它
只负责把参数加工成本次调用的 `user` message；经过 `@step` 装饰后，名字
`classify` 绑定到 `Step[Verdict]`，调用 `classify(...)` 会完成 LLM 调用并
返回 `Verdict` 实例。

## 继续读

- [文档站首页](https://onenightcarnival.github.io/pyxis-agent/)——核心概念与场景化 Cookbook
- [哲学与定位](https://onenightcarnival.github.io/pyxis-agent/concepts/philosophy/)——
  函数式思想、agent-for-machine 定位与完整的"故意不做"清单

- [Cookbook](https://onenightcarnival.github.io/pyxis-agent/cookbook/)——
  测试、可观测、MCP、Interrupt 和 agent 模式的使用姿势

## 仓库结构 ↔ 文档站

| 目录            | 是什么                                         | 在文档站的位置                    |
|-----------------|------------------------------------------------|-----------------------------------|
| `src/pyxis/`    | 库本体                                         | [**API 参考**](https://onenightcarnival.github.io/pyxis-agent/api/step/) 自动从 docstring 生成 |
| `examples/`     | 单文件可跑脚本——每个核心能力一个               | [**Cookbook**](https://onenightcarnival.github.io/pyxis-agent/cookbook/) 自动渲染 |
| `docs/`         | 文档站源（MkDocs Material）                    | 文档站本体 |
| `tests/`        | pytest（单元零网络 + `integration/` 烟雾测试） | 不上站 |
| `CLAUDE.md`     | AI PM 设计笔记（协作模式、决策依据）           | **不上站** |
| `ROADMAP.md`    | "已做 / 近期候选 / 故意不做"                   | **不上站** |

## 开发
```bash
uv sync
uv run ruff format && uv run ruff check
uv run pytest                                        # 单元测试，零网络
uv run --env-file .env pytest tests/integration/     # 真实 LLM 烟雾测试
uv run --group docs mkdocs build --strict            # 文档站验收
```

- 迭代方法：**概念设计改文档，代码设计走 TODO-driven skeleton**；先写真实模块、
  类型、函数签名、docstring 与失败测试，再填实现，迭代结束前清空本轮 TODO

- 变更历史：`git log` + [GitHub Releases](https://github.com/Onenightcarnival/pyxis-agent/releases)
- 待办与"故意不做"：[ROADMAP.md](ROADMAP.md)
- 设计依据：[CLAUDE.md](CLAUDE.md)
