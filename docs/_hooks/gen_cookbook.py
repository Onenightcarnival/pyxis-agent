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
    # --- 入门：先看一次调用、流式输出和批处理 ---
    (
        "research",
        "两步结构化调用",
        "用两个 step 串起分析和规划。",
    ),
    (
        "streaming_demo",
        "字段流式输出",
        "用 `.stream()` 逐步接收 partial 模型。",
    ),
    (
        "batch_extraction",
        "批量结构化抽取",
        "把多段非结构化文本抽成 Pydantic 模型。",
    ),
    # --- 编排：普通 Python 控制流负责多步组合 ---
    (
        "plan_then_execute",
        "计划后执行",
        "先产出计划，再逐步执行计划。",
    ),
    (
        "router_dispatch",
        "意图路由",
        "用 `Literal` 标签和 `match` 分派子流程。",
    ),
    (
        "reflect_and_revise",
        "自我检查与改写",
        "用 while 循环完成 draft、critique、revise。",
    ),
    (
        "interrupt_review",
        "人工审阅节点",
        "用 `ask_interrupt` 在生成器流程中等待审阅结果。",
    ),
    # --- 数据和状态：外部材料、记忆、多 agent 协作 ---
    (
        "rag_minimal",
        "检索增强问答",
        "一个检索函数加一个回答 step。",
    ),
    (
        "memory_kv",
        "轻量记忆",
        "用 dict 保存记忆，一个 step 抽事实，一个 step 作答。",
    ),
    (
        "multi_agent",
        "双 agent 协作",
        "Researcher 函数调用 Editor 函数。",
    ),
    # --- 工具和外部系统 ---
    (
        "agent_tool_use",
        "本地工具调用循环",
        "用 for 循环和判别式联合写 agent loop。",
    ),
    (
        "coding_harness",
        "文件工具任务循环",
        "用读、写、列目录三个工具组成代码任务循环。",
    ),
    (
        "mcp_tool_use",
        "MCP 工具接入",
        "把 FastMCP server 工具和本地 Tool 放进同一个联合类型。",
    ),
    # --- 工程化：测试、评测、观测、护栏 ---
    (
        "guardrails",
        "输入输出护栏",
        "用 Python 正则和 Pydantic validator 做输入输出校验。",
    ),
    (
        "with_langfuse",
        "Langfuse 接入",
        "用 Langfuse OpenAI client 记录 step 调用。",
    ),
    (
        "evals",
        "小数据集评测",
        "用 dataset、for 循环和 JSONL 记录评测结果。",
    ),
]

CATEGORIES: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "入门",
        [
            next(item for item in RECIPES if item[0] == "research"),
            next(item for item in RECIPES if item[0] == "streaming_demo"),
            next(item for item in RECIPES if item[0] == "batch_extraction"),
        ],
    ),
    (
        "多步编排",
        [
            next(item for item in RECIPES if item[0] == "plan_then_execute"),
            next(item for item in RECIPES if item[0] == "router_dispatch"),
            next(item for item in RECIPES if item[0] == "reflect_and_revise"),
            next(item for item in RECIPES if item[0] == "interrupt_review"),
            ("interrupt", "Interrupt 接入说明", "用生成器流程等待外部输入。"),
        ],
    ),
    (
        "数据和状态",
        [
            next(item for item in RECIPES if item[0] == "rag_minimal"),
            next(item for item in RECIPES if item[0] == "memory_kv"),
            next(item for item in RECIPES if item[0] == "multi_agent"),
        ],
    ),
    (
        "工具和外部系统",
        [
            next(item for item in RECIPES if item[0] == "agent_tool_use"),
            next(item for item in RECIPES if item[0] == "coding_harness"),
            ("mcp", "MCP 接入说明", "把远端工具服务转成本地 `Tool` 子类。"),
            next(item for item in RECIPES if item[0] == "mcp_tool_use"),
        ],
    ),
    (
        "工程化",
        [
            (
                "testing",
                "单元测试",
                "用预置响应和 `.calls` 写单元测试。",
            ),
            next(item for item in RECIPES if item[0] == "evals"),
            (
                "observability",
                "可观测接入说明",
                "Langfuse、OpenTelemetry 和 APM 接在 OpenAI SDK 层。",
            ),
            next(item for item in RECIPES if item[0] == "with_langfuse"),
            next(item for item in RECIPES if item[0] == "guardrails"),
        ],
    ),
]

MATRIX_ROWS: list[tuple[str, str, str, str]] = [
    ("research", "两次结构化调用怎么串起来", "Step、字段顺序、普通函数组合", "最短主线，先读它"),
    (
        "streaming_demo",
        "前端或 CLI 想边生成边展示",
        "Step.stream、partial model",
        "只讲流式，不讲业务流程",
    ),
    (
        "batch_extraction",
        "一批文本怎么稳定入库或统计",
        "批处理、异常兜底、Counter",
        "比 research 更偏数据 pipeline",
    ),
    (
        "plan_then_execute",
        "计划和执行要不要拆成两次调用",
        "计划 schema、执行 schema、for 循环",
        "比 research 多了逐步上下文累积",
    ),
    (
        "router_dispatch",
        "不同意图走不同处理器",
        "Literal 分类、match 分派",
        "只做分流，不做工具循环",
    ),
    (
        "reflect_and_revise",
        "生成后如何自动检查并改写",
        "critic-refiner、while 控制轮次",
        "适合质量收敛，不适合外部审批",
    ),
    (
        "interrupt_review",
        "流程中间必须等人或外部系统确认",
        "ask_interrupt、run_flow",
        "和 reflect 的区别是外部输入",
    ),
    (
        "rag_minimal",
        "回答前需要先查资料",
        "检索函数、上下文注入、引用字段",
        "检索是 Python 函数，不是 Tool",
    ),
    (
        "memory_kv",
        "短期或轻量记忆怎么接",
        "事实抽取、dict 状态、回答 step",
        "只示范状态读写，不引入向量库",
    ),
    (
        "multi_agent",
        "两个角色怎么交接结构化结果",
        "Researcher / Editor 函数组合",
        "强调机器对机器传 Pydantic",
    ),
    (
        "agent_tool_use",
        "LLM 如何选择并调用本地动作",
        "Tool、判别式联合、agent loop",
        "最基础的工具调用例子",
    ),
    (
        "coding_harness",
        "工具调用如何扩展成文件任务循环",
        "ls/read/write/finish 工具",
        "agent_tool_use 的工程任务版",
    ),
    (
        "mcp_tool_use",
        "远端 MCP 工具如何混进本地工具表",
        "mcp_toolset、动态 Tool 类",
        "只比本地工具多 MCP 接入",
    ),
    ("testing", "单元测试怎么零网络断言", "FakeClient、calls", "先测结构，不测模型能力"),
    ("evals", "真实模型效果怎么小规模回归", "dataset、指标、JSONL", "评测模型，不替代单元测试"),
    ("observability", "生产 trace 接在哪里", "OpenAI SDK 层 instrumentation", "说明接入位置"),
    ("with_langfuse", "Langfuse 具体怎么接", "langfuse.openai.OpenAI", "observability 的可跑版本"),
    (
        "guardrails",
        "输入输出怎么拦危险内容",
        "前置正则、Pydantic validator",
        "护栏写在 Python/schema，不写框架 DSL",
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


def _format_intro_markdown(text: str) -> str:
    """给 example docstring 补 Markdown 段落边界。

    示例文件里的 docstring 首先服务于源码阅读，常常写得比较紧凑；渲染成
    Cookbook 时，如果不补空行，列表和运行命令会挤进同一个段落。
    """
    heading_prefixes = ("跑起来", "运行前需要", "拓扑", "展示两件事", "换生产 MCP server")
    lines = text.splitlines()
    out: list[str] = []

    for line in lines:
        stripped = line.strip()
        previous = out[-1] if out else ""
        previous_stripped = previous.strip()

        if not stripped:
            if previous_stripped:
                out.append("")
            continue

        starts_list = stripped.startswith("- ") or bool(re.match(r"\d+\.\s", stripped))
        starts_code = line.startswith("    ")
        previous_starts_list = previous_stripped.startswith("- ") or bool(
            re.match(r"\d+\.\s", previous_stripped)
        )
        previous_starts_code = previous.startswith("    ")
        starts_heading = any(stripped.startswith(prefix) for prefix in heading_prefixes)

        needs_blank = False
        if out and previous_stripped:
            needs_blank = (
                starts_heading
                or (starts_list and not previous_starts_list)
                or (starts_code and not previous_starts_code)
                or (previous_starts_code and not starts_code)
            )

        if needs_blank:
            out.append("")
        out.append(line)

    return "\n".join(out).strip()


# ---- Cookbook index 页 ----
index_lines = [
    "# Cookbook",
    "",
    "这里按问题来选案例。",
    "",
    "带源码的 recipe 来自 `examples/` 下的单文件。运行这些示例通常需要 `OPENROUTER_API_KEY`，也可以把 `OpenAI(base_url=..., api_key=...)` 改成其他 OpenAI-compatible provider。",
    "",
]
index_lines.extend(
    [
        "## 先看哪几个",
        "",
        "- 想理解 pyxis 的主线：先读 [两步结构化调用](research.md)、[批量结构化抽取](batch_extraction.md)、[本地工具调用循环](agent_tool_use.md)。",
        "- 想接工程能力：看 [单元测试](testing.md)、[小数据集评测](evals.md)、[可观测接入说明](observability.md)。",
        "- 想对接外部工具：看 [本地工具调用循环](agent_tool_use.md)、[MCP 工具接入](mcp_tool_use.md)。",
        "",
        "## 案例矩阵",
        "",
        "| Recipe | 回答的问题 | 主要覆盖 | 和相近案例的区别 |",
        "|---|---|---|---|",
    ]
)
titles = {name: title for name, title, _ in RECIPES}
titles.update(
    {
        "testing": "单元测试",
        "observability": "可观测接入说明",
        "mcp": "MCP 接入说明",
        "interrupt": "Interrupt 接入说明",
    }
)
for name, question, coverage, distinction in MATRIX_ROWS:
    index_lines.append(f"| [{titles[name]}]({name}.md) | {question} | {coverage} | {distinction} |")
index_lines.extend(["", "## 按主题浏览", ""])
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
        page.append(_format_intro_markdown(_rewrite_intro_links(intro)))
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
