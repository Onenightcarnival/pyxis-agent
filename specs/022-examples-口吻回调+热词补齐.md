# 022 examples 口吻回调 + 热词补齐

## 目的

- 021 补了五份 examples，但 docstring 里"原语 / punchline / 没有 X 抽象"
  这类翻译腔 + 自证式口吻不少，与 018-020 的全站口吻约定不一致。
- 021 说"这轮覆盖度够了"，用户回复"不止五个热词，全部补了呗"——
  router / memory / multi-agent / guardrails 一起补齐。

## 口吻规则（所有 examples docstring 对齐）

禁用：

- `原语` → 用具体名字（`@step` / `Tool` / `flow` / `Trace`）
- `punchline：……` → 直接陈述
- `没有 X 抽象 / 不引入新原语 / 不需要这一套` 这类自证式否认
- `### 小节` 多层 header（docstring 不是文档站页）
- 粗体自吹（`**pyxis 做到了 X**`）
- `本 demo 展示……`开场

写法：

- 首句陈述这份示例做什么（≤ 20 字）
- 中段讲 pyxis 里怎么组合（用 API 名，不空谈哲学）
- 末尾一段是跑法
- 整份 docstring 控制 15-25 行

## 动作

- **存量 + 新增 13 份** docstring 全扫一遍，命中禁用词就改
- 新增 4 份示例：
  - `router_dispatch`  一个 `@step` 出 `Literal[...]` 标签；Python `match` 分派到子 flow
  - `memory_kv`        短期=messages 拼接；长期=一个 dict + 两个 `Tool`（记忆/回忆）
  - `multi_agent`      Researcher flow 被 Editor flow 调用——就是函数调用
  - `guardrails`       `StepHook` 的 on_start 前置校验 + Pydantic validator 后置校验
- 每份新示例用 `uv run --env-file .env python examples/XXX.py` 真跑一次

## 验收

- 13 份 docstring 不出现 `原语` / `punchline` / `没有 X 抽象` 等禁用词
- 4 份新示例 stdout 可读、能真实完成任务
- `gen_cookbook.py` RECIPES 更新、`mkdocs.yml` nav 更新
- `ruff format && ruff check && pytest && mkdocs build --strict` 全绿

## 不做

- 不动示例的**代码逻辑**（除非去 AI 味顺便发现 bug）——这轮是 docstring + 补
- 不加 deep-research / tool-generation 等营销热词示例
- 不修 `src/` API
