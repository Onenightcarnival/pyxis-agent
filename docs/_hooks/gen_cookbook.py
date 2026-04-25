"""mkdocs-gen-files 钩子：把 examples/*.py 渲染成 Cookbook 页。

每份 recipe 的文件顶部 docstring 作为 intro；其余代码原样嵌进页面。
"""

from __future__ import annotations

import re
from pathlib import Path

import mkdocs_gen_files

ROOT = Path(__file__).resolve().parents[2]
GH_BLOB = "https://github.com/Onenightcarnival/pyxis-agent/blob/main"

# 手工编排顺序 + 中文标题 + 一句话说明（RECIPES 的顺序 = cookbook 生成顺序）。
RECIPES: list[tuple[str, str, str]] = [
    # --- 入门：各核心概念逐个登场 ---
    (
        "research",
        "端到端：分析 + 规划",
        "用两个 step 完成分析和规划。",
    ),
    (
        "streaming_demo",
        "流式输出",
        "用 `.stream()` 逐步接收 partial 模型。",
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
        "一个检索函数加一个回答 step。",
    ),
    (
        "batch_extraction",
        "批量结构化抽取",
        "把多段非结构化文本抽成 Pydantic 模型。",
    ),
    (
        "router_dispatch",
        "Router / 意图分派",
        "用 `Literal` 标签和 `match` 分派子流程。",
    ),
    (
        "memory_kv",
        "长期记忆：抽事实 + 查记忆",
        "用 dict 保存记忆，一个 step 抽事实，一个 step 作答。",
    ),
    (
        "multi_agent",
        "两个 agent 协作",
        "Researcher flow 调用 Editor flow。",
    ),
    (
        "reflect_and_revise",
        "Reflection / critic-refiner",
        "用 while 循环完成 draft、critique、revise。",
    ),
    # --- 工具调用家族 ---
    (
        "agent_tool_use",
        "ReAct 风格 agent + 工具调用",
        "用 for 循环和判别式联合写 agent loop。",
    ),
    (
        "coding_harness",
        "Agentic harness / scaffolding",
        "用读、写、列目录三个工具组成代码任务循环。",
    ),
    (
        "mcp_tool_use",
        "MCP：混合 native 工具与远端 server",
        "把 FastMCP server 工具和本地 Tool 放进同一个联合类型。",
    ),
    # --- 工程化：人机协作 + 观测 + 评测 + 合规 ---
    (
        "interrupt_review",
        "Interrupt review",
        "用 `ask_interrupt` 在 flow 中等待审阅结果。",
    ),
    (
        "guardrails",
        "输入 gate + 输出 validator",
        "用 Python 正则和 Pydantic validator 做输入输出校验。",
    ),
    (
        "with_langfuse",
        "接入 Langfuse 可观测性",
        "用 Langfuse OpenAI client 记录 step 调用。",
    ),
    (
        "evals",
        "Evals 一把梭",
        "用 dataset、for 循环和 JSONL 记录评测结果。",
    ),
]

CATEGORIES: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "测试",
        [
            (
                "testing",
                "FakeClient 与断言",
                "用预置响应和 `.calls` 写单元测试。",
            ),
            next(item for item in RECIPES if item[0] == "evals"),
        ],
    ),
    (
        "可观测",
        [
            (
                "observability",
                "可观测总览",
                "Langfuse、OpenTelemetry 和 APM 接在 OpenAI SDK 层。",
            ),
            next(item for item in RECIPES if item[0] == "with_langfuse"),
        ],
    ),
    (
        "MCP",
        [
            ("mcp", "MCP 总览", "把远端工具服务转成本地 `Tool` 子类。"),
            next(item for item in RECIPES if item[0] == "mcp_tool_use"),
        ],
    ),
    (
        "Interrupt",
        [
            (
                "interrupt",
                "Interrupt 总览",
                "用生成器 flow 等待外部输入。",
            ),
            next(item for item in RECIPES if item[0] == "interrupt_review"),
        ],
    ),
    (
        "Agent 模式",
        [
            item
            for item in RECIPES
            if item[0] not in {"evals", "with_langfuse", "mcp_tool_use", "interrupt_review"}
        ],
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

    - `](../docs/XXX.md)` 改成 `](../XXX.md)`：`docs/` 在站点是根，cookbook 页的
      相对路径同层。
    """
    return re.sub(r"\]\(\.\./docs/", "](../", text)


# ---- Cookbook index 页 ----
index_lines = [
    "# Cookbook",
    "",
    "这里按主题整理可运行示例和接入说明。",
    "",
    "带源码的 recipe 来自 `examples/` 下的单文件。运行这些示例通常需要 `OPENROUTER_API_KEY`，也可以把 `OpenAI(base_url=..., api_key=...)` 改成其他 OpenAI-compatible provider。",
    "",
]
for category, recipes in CATEGORIES:
    index_lines.extend(
        [
            f"## {category}",
            "",
            "| Recipe | 讲什么 |",
            "|---|---|",
        ]
    )
    for name, title, subtitle in recipes:
        index_lines.append(f"| [{title}]({name}.md) | {subtitle} |")
    index_lines.append("")
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
