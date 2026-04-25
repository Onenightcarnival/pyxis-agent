# pyxis-agent

**声明式思维链的 Python agent 框架 —— agent-for-machine 阵营。**

> **`声明式思维链 = code as prompt + schema as workflow`**

**完整文档**：<https://onenightcarnival.github.io/pyxis-agent/>

---

## 一句话

- LLM = 带自然语言理解能力的**结构化数据生成器**
- 每次调用直出一个 Pydantic 实例，下一段 Python 代码直接消费
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
from pydantic import BaseModel
from pyxis import step

client = OpenAI(api_key="sk-...")   # 就是 OpenAI SDK 你已经熟的那个

class Verdict(BaseModel):
    sentiment: str     # 先判情感
    confidence: float  # 再给置信度——字段顺序就是思维链

@step(output=Verdict, model="gpt-4o-mini", client=client)
def classify(text: str) -> str:
    """你是一个情感分类器。判断给定文本的情感倾向，给出置信度。"""
    return text

v = classify("今天简直完美")
assert v.sentiment == "positive"
```

两件事同时发生：

- **code as prompt** — 函数 docstring = system prompt，返回值 = user message
- **schema as workflow** — `Verdict` 字段顺序（`sentiment` 在 `confidence` 前）= LLM 的思维链

## 继续读

- [文档站首页](https://onenightcarnival.github.io/pyxis-agent/)——核心概念、
  可观测性、MCP 接入
- [哲学与定位](https://onenightcarnival.github.io/pyxis-agent/concepts/philosophy/)——
  完整的"故意不做"清单
- [Cookbook](https://onenightcarnival.github.io/pyxis-agent/cookbook/)——
  `examples/` 里每个脚本对应一种使用姿势
- [Demos](https://onenightcarnival.github.io/pyxis-agent/demos/)——
  `apps/` 里两个带前端的可视化应用

## 仓库结构 ↔ 文档站

| 目录            | 是什么                                         | 在文档站的位置                    |
|-----------------|------------------------------------------------|-----------------------------------|
| `src/pyxis/`    | 库本体                                         | [**API 参考**](https://onenightcarnival.github.io/pyxis-agent/api/step/) 自动从 docstring 生成 |
| `examples/`     | 单文件可跑脚本——每个核心能力一个               | [**Cookbook**](https://onenightcarnival.github.io/pyxis-agent/cookbook/) 自动渲染 |
| `apps/`         | 带前端的示例应用（`chat-demo`、`mcp-demo`）     | [**Demos**](https://onenightcarnival.github.io/pyxis-agent/demos/) |
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
