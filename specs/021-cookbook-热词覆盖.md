# 021 Cookbook 扩容：行业热词翻译成 pyxis 原语

## 目的

用户反馈 cookbook 偏"原语逐个亮相"，缺行业热词场景的落地。本迭代补一批
示例，把 **RAG / agentic harness / reflection / batch extraction / evals**
这些词翻译成 pyxis 已有的原语——**不引入新抽象**，punchline 是"这些热词
在 pyxis 里就是 step + flow + tool 的组合"。

## 新增示例

| 文件 | 热词 | punchline |
|---|---|---|
| `rag_minimal.py`        | RAG                   | 检索是 Tool（或普通函数），生成 step 把结果塞进 prompt 字符串——两个 step 而已 |
| `batch_extraction.py`   | 结构化抽取 pipeline    | agent-for-machine 主场：批量抽 Pydantic + Trace 聚合成功率/tokens |
| `coding_harness.py`     | agentic harness        | read/write/ls 三 tool + `while` loop + 自停止 = harness；没有新原语 |
| `reflect_and_revise.py` | reflection / self-correct | `while score<阈值` + critique step；老模式新词 |
| `evals_with_trace.py`   | evals                  | 小 dataset + Trace → JSONL eval log + 聚合指标 |

## 验收

- 5 个示例文件落地；每个单文件可独立跑，顶部 docstring 含"是什么 / 为什么 /
  怎么跑"三段，且**显式点出"pyxis 视角下它就是 X + Y 的组合"**。
- **每个示例都用 `uv run --env-file .env python examples/XXX.py` 实跑过一次**，
  真 LLM 回应，stdout 可读。
- `gen_cookbook.py` 的 `RECIPES` 加入这 5 条，顺序合理（入门 → 场景 → 工程化）。
- `uv run ruff format && uv run ruff check && uv run pytest` 全绿。
- `uv run --group docs mkdocs build --strict` 零警告。
- 新示例**不引入新库依赖**（retrieval 用内存 dict + 关键词匹配，coding
  harness 用内存"虚拟文件系统"，不真的执行任意代码）。

## 不做

- 不加真 vector DB / embedding（换成内存关键词匹配够讲清楚原理；接真
  vector DB 是应用层的事）。
- 不让 harness 真执行 shell / Python（安全考量；用内存 FS 讲结构即可）。
- 不在 `src/` 加任何 API（框架够用了；这次只是示例）。
- 不碰现有 7 个示例（独立迭代；真要重写 docstring 再单开 spec）。
- 不加 multi-agent / router / guardrails 示例——这轮覆盖度够了，贪多就稀。
