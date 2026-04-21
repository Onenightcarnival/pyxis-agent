"""语言政策合规测试 —— 规约 006。

这些测试确保项目核心文档与源码 docstring 不会在未来迭代里意外回退成英文。
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIN_CJK = 100


def _count_cjk(text: str) -> int:
    return sum(1 for c in text if "\u4e00" <= c <= "\u9fff")


def _targets() -> list[Path]:
    paths: list[Path] = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "CLAUDE.md",
        PROJECT_ROOT / "ROADMAP.md",
    ]
    paths.extend(sorted((PROJECT_ROOT / "specs").glob("*.md")))
    paths.extend(sorted((PROJECT_ROOT / "src" / "pyxis").glob("*.py")))
    return paths


@pytest.mark.parametrize("path", _targets(), ids=lambda p: str(p.relative_to(PROJECT_ROOT)))
def test_file_contains_sufficient_chinese(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    count = _count_cjk(text)
    assert count >= MIN_CJK, (
        f"{path.relative_to(PROJECT_ROOT)} 中文字符数 {count} < {MIN_CJK}，疑似未按规约 006 中文化"
    )
