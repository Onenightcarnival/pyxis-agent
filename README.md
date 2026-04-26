# pyxis-agent

**把大模型调用写成 Python 函数，返回 Pydantic 实例。**

核心概念：**声明式思维链**。稳定规则写进代码，字段顺序就是单次调用里的输出顺序。

**完整文档**：<https://onenightcarnival.github.io/pyxis-agent/>

---

## 一句话

- 把一次 LLM 调用包装成函数：传入文本，返回 Pydantic 对象
- 每次调用返回一个 Pydantic 实例，下一段 Python 代码继续处理
- `@step` 把 input builder 变成可组合、可替换、可测试的调用
- `Tool` / `@tool` 用 Pydantic 描述工具参数，由 Python 执行
- 多步编排继续写普通 Python 函数
- 给人看的内容由应用层从字段里拼

**适合**：数据 pipeline 里的 LLM 节点 · 要回归测试的业务 agent · 多 agent 机器对机器协作。
**不适合**：聊天 UI 优先的产品。

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
    return f"用户原文：{text}"


v = classify("今天简直完美")
assert v.sentiment == "positive"
```

这里有两个约定：

- `Verdict` 的字段顺序就是输出顺序，先填 `sentiment`，再填 `confidence`
- Pydantic 字段、函数签名和函数体返回的输入文本共同定义这次调用；docstring 不进入 LLM 上下文

`sentiment` 和 `confidence` 怎么判断，写在 schema 里；函数返回值只放本次调用的材料。
不要把 response model 再用自然语言复述成一段 prompt。

注意这里有两层类型：`classify` 的函数体是 input builder，`-> str` 表示它
只负责把参数加工成本次调用的 `user` message；经过 `@step` 装饰后，名字
`classify` 绑定到 `Step[Verdict]`，调用 `classify(...)` 会完成 LLM 调用并
返回 `Verdict` 实例。

## 继续读

- [文档站首页](https://onenightcarnival.github.io/pyxis-agent/)——核心概念与场景化 Cookbook
- [项目定位](https://onenightcarnival.github.io/pyxis-agent/concepts/philosophy/)——pyxis 做什么、不做什么

- [Cookbook](https://onenightcarnival.github.io/pyxis-agent/cookbook/)——
  入门、多步编排、数据状态、工具接入和工程化用法

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
