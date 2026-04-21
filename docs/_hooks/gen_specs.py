"""mkdocs-gen-files 钩子：把 CHANGELOG.md 挂进站点。

specs/ 和 ROADMAP.md 是团队内部资料，不对用户展示，留在仓库里即可。
这里只把 CHANGELOG 作为"更新日志"附录发出去——用户确实会想知道版本间
改了什么。
"""

from __future__ import annotations

import re
from pathlib import Path

import mkdocs_gen_files

ROOT = Path(__file__).resolve().parents[2]
GH_BLOB = "https://github.com/Onenightcarnival/pyxis-agent/blob/main"


def _rewrite_links(text: str) -> str:
    """把相对路径引用改成站点内 URL 或 GitHub blob URL。

    - `docs/langfuse.md` → `langfuse.md`
    - `docs/对比.md` → `comparison.md`
    - `specs/NNN-xxx.md` → GitHub blob URL（用户点进去是源码仓库，不污染站点）
    - `apps/...` / `examples/...` / `src/...` → GitHub blob URL
    """
    text = re.sub(r"\]\(docs/langfuse\.md\)", "](langfuse.md)", text)
    text = re.sub(r"\]\(docs/对比\.md\)", "](comparison.md)", text)

    def to_blob(match: re.Match[str]) -> str:
        path = match.group(1)
        return f"]({GH_BLOB}/{path})"

    for pattern in (
        r"\]\((specs/[^)]+)\)",
        r"\]\((apps/[^)]+)\)",
        r"\]\((examples/[^)]+)\)",
        r"\]\((src/[^)]+)\)",
    ):
        text = re.sub(pattern, to_blob, text)
    return text


src = ROOT / "CHANGELOG.md"
if src.exists():
    with mkdocs_gen_files.open("changelog.md", "w") as fd:
        fd.write(_rewrite_links(src.read_text(encoding="utf-8")))
    mkdocs_gen_files.set_edit_path("changelog.md", "CHANGELOG.md")
