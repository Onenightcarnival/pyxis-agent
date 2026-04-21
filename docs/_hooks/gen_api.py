"""mkdocs-gen-files 钩子：为 pyxis 每个模块生成 API 参考页和导航。

每个模块一页，内容就一行 `::: pyxis.<module>`，mkdocstrings 会把
docstring 渲染成完整的 API 参考。
"""

from __future__ import annotations

import mkdocs_gen_files

# 顺序就是 CLAUDE.md 里介绍各概念的顺序——读者顺着看下来就是一条自然路径。
MODULES: list[tuple[str, str]] = [
    ("step", "Step / AsyncStep + @step"),
    ("flow", "Flow / AsyncFlow + @flow"),
    ("tool", "Tool 基类 + @tool 装饰器"),
    ("client", "Client 协议 / FakeClient / InstructorClient"),
    ("providers", "OpenRouter / OpenAI 便捷工厂"),
    ("trace", "trace() / TraceRecord"),
    ("hooks", "StepHook 观察者中间件"),
    ("human", "human-in-the-loop：让 agent 停下来等人回应"),
    ("mcp", "MCP 适配层"),
]

for name, subtitle in MODULES:
    page_path = f"api/{name}.md"
    with mkdocs_gen_files.open(page_path, "w") as fd:
        fd.write(f"# `pyxis.{name}`\n\n")
        fd.write(f"> {subtitle}\n\n")
        fd.write(f"::: pyxis.{name}\n")
    mkdocs_gen_files.set_edit_path(page_path, f"src/pyxis/{name}.py")
