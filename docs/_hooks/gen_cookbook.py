"""mkdocs-gen-files 钩子：把 examples/*.py 渲染成 Cookbook 页。

每份 recipe 的文件顶部 docstring 就是 intro；其余代码原样嵌进页面。
"文件本身就是 recipe"——不写第二份营销文案，改一处代码就是改一处 cookbook。
"""

from __future__ import annotations

import re
from pathlib import Path

import mkdocs_gen_files

ROOT = Path(__file__).resolve().parents[2]
GH_BLOB = "https://github.com/Onenightcarnival/pyxis-agent/blob/main"

# 手工编排顺序 + 中文标题 + 一句话说明（RECIPES 的顺序 = 侧边栏顺序）。
# 以底部装饰条 cookbook/index.md 里的表格顺序也跟这个列表走。
RECIPES: list[tuple[str, str, str]] = [
    # --- 入门：各核心概念逐个登场 ---
    (
        "research",
        "端到端：分析 + 规划",
        "隐式思维链（字段顺序）+ 显式编排（Python 多步）两条轴同时展示。",
    ),
    (
        "streaming_demo",
        "流式输出",
        "看 schema 字段一个个被填满——schema-as-CoT 的最直观呈现。",
    ),
    (
        "plan_then_execute",
        "Plan-then-execute",
        "先让 LLM 出计划，再让另一个 Step 逐步执行。",
    ),
    # --- 热词翻译：行业概念落到 pyxis 的具体 API ---
    (
        "rag_minimal",
        "RAG 最小版",
        "检索一个函数 + 作答一个 step，整个 RAG 骨架就 30 行。",
    ),
    (
        "batch_extraction",
        "批量结构化抽取",
        "非结构化文本批量抽成 Pydantic + Trace 聚合成本与失败。",
    ),
    (
        "router_dispatch",
        "Router / 意图分派",
        "一个 step 出 `Literal` 标签，Python `match` 分派到子 flow。",
    ),
    (
        "memory_kv",
        "长期记忆：抽事实 + 查记忆",
        "一个 dict 当 KV，一个 step 抽事实、一个 step 作答。",
    ),
    (
        "multi_agent",
        "两个 agent 协作",
        "Researcher flow 调 Editor flow——函数调函数，没有 graph。",
    ),
    (
        "reflect_and_revise",
        "Reflection / critic-refiner",
        "draft → critique → revise 的 while 循环；字段顺序防先打分后编理由。",
    ),
    # --- 工具调用家族 ---
    (
        "agent_tool_use",
        "ReAct 风格 agent + 工具调用",
        "显式 for 循环的 agent loop；判别式联合当工具表。",
    ),
    (
        "coding_harness",
        "Agentic harness / scaffolding",
        "读 / 写 / 列 三工具 + while 循环 + 自停止。",
    ),
    (
        "mcp_tool_use",
        "MCP：混合 native 工具与远端 server",
        "FastMCP server 的工具与本地 Tool 拼进同一个判别式联合。",
    ),
    # --- 工程化：人机协作 + 观测 + 评测 + 合规 ---
    (
        "interrupt_review",
        "Interrupt review",
        "生成器 flow + `ask_interrupt` 挂起；人工审阅是 interrupt 的一种来源。",
    ),
    (
        "guardrails",
        "输入 gate + 输出 validator",
        "Python 正则前置 + Pydantic validator 后置，guardrail 逻辑原地写。",
    ),
    (
        "with_langfuse",
        "接入 Langfuse 可观测性",
        "零侵入——换一个 `OpenAI` 的 import 就启用。",
    ),
    (
        "evals",
        "Evals 一把梭",
        "dataset + for 循环 + 手写 JSONL 落盘；聚合指标是普通 Python。",
    ),
]

_DOCSTRING_RE = re.compile(r'^"""(.*?)"""\s*\n', re.DOTALL)


def _split_docstring(source: str) -> tuple[str, str]:
    """提取文件顶部的三引号 docstring 做 intro，返回 (intro, 剩余代码)。"""
    m = _DOCSTRING_RE.match(source)
    if not m:
        return "", source
    intro = m.group(1).strip()
    body = source[m.end() :].lstrip("\n")
    return intro, body


def _rewrite_intro_links(text: str) -> str:
    """examples/ 里的相对链接换算到 cookbook/ 下。

    - `](../docs/XXX.md)` → `](../XXX.md)`：`docs/` 在站点是根，cookbook 页的
      相对路径同层。
    """
    return re.sub(r"\]\(\.\./docs/", "](../", text)


# ---- Cookbook index 页 ----
index_lines = [
    "# Cookbook",
    "",
    "可以直接跑起来的案例。每个 recipe 都是 `examples/` 下的一个单文件，复制改改就能当脚手架用。",
    "",
    "需要 `OPENROUTER_API_KEY`（或改一下 `OpenAI(base_url=..., api_key=...)` 指向别的 OpenAI 兼容 provider）。",
    "",
    "| Recipe | 讲什么 |",
    "|---|---|",
]
for name, title, subtitle in RECIPES:
    index_lines.append(f"| [{title}]({name}.md) | {subtitle} |")
index_lines.append("")

with mkdocs_gen_files.open("cookbook/index.md", "w") as fd:
    fd.write("\n".join(index_lines))


# ---- 每个 recipe 一页 ----
for name, title, subtitle in RECIPES:
    src_path = ROOT / "examples" / f"{name}.py"
    if not src_path.exists():
        raise FileNotFoundError(f"cookbook recipe 缺源码：{src_path}")

    source = src_path.read_text(encoding="utf-8")
    intro, body = _split_docstring(source)

    page = [
        f"# {title}",
        "",
        f"> {subtitle}",
        "",
    ]
    if intro:
        page.append(_rewrite_intro_links(intro))
        page.append("")
    page.append(f"源码：[examples/{name}.py]({GH_BLOB}/examples/{name}.py)")
    page.append("")
    page.append("```python")
    page.append(body.rstrip() + "\n")
    page.append("```")
    page.append("")

    page_path = f"cookbook/{name}.md"
    with mkdocs_gen_files.open(page_path, "w") as fd:
        fd.write("\n".join(page))
    mkdocs_gen_files.set_edit_path(page_path, f"examples/{name}.py")
