# 017 docs 第二轮编辑打磨

## 目的

规格 016 关掉了结构性错位（Demos 上站、仓库结构对照）之后再审一遍
文档站，三处不够"开源项目水准"的打磨：

1. **`docs/concepts/index.md` 只有一份目录清单**——Material 侧边栏已经
   把所有概念页列出来了，这页不做别的事等于空跑。访客在这里应该拿到
   "这一 tab 讲什么 / 建议怎么读 / 什么时候可以跳过不读"的路径信息。
2. **`docs/_hooks/gen_cookbook.py` 有 pre-existing 的 ruff format 漂移**
   （一个三引号的单引号写法），应该顺手清掉。不然每次 `ruff format
   --check` 都看到一条无关报警，审计噪声累积。
3. **诸如"xxx 在 pyxis 里都是 BaseModel"等措辞在多页重复，但**——这次
   我过了一遍八页概念 + 哲学，实际重复度**可以接受**（各页都是最小
   例子 + 该页专属变体，不是复制粘贴），不改。

## 验收

- `docs/concepts/index.md` 不再是纯目录：有一段说清这一 tab 的读法
  建议、推荐阅读顺序、"哪几页可以按需跳过"的指引；保留一张表作为
  速查，不重复 `docs/index.md` 上已有的"核心概念一览"。
- `uv run ruff format --check` clean。
- `uv run --group docs mkdocs build --strict` 零警告。
- `uv run pytest` 全绿。

## 不做

- 不改 concept 各页内容（已达水准）。
- 不改 demos 页（016 刚落，冷一下）。
- 不动 `src/`。
- 不新增页面。
