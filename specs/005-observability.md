# 005：可观测性 —— 重试 + 用量 + trace 导出

## 目的

生产环境需要三个开关，它们共享同一套基础设施：

- **重试**：结构化输出验证失败时的重试次数（instructor 自己能做，我们
  把旋钮提升到 `@step` 级别）；
- **Token 用量**：每次 LLM 调用的 token 数，用来做成本核算；
- **trace 结构化导出**：日志里能完整带走一次运行。

三者都会动到 `TraceRecord` 和 `Client` 协议的返回类型，所以一并做。

## API 草图

```python
from pyxis import step, trace, Usage

@step(output=Plan, max_retries=2)
def plan(req: str) -> str:
    """..."""
    return req

with trace() as t:
    plan("x")

rec = t.records[0]
assert rec.usage is None or isinstance(rec.usage, Usage)

# 导出给日志
t.to_dict()                # {"records": [{"step": ..., "output": {...}, ...}]}
t.to_json(indent=2)        # str
t.total_usage()            # Usage(prompt_tokens=..., ...)
```

## 验收标准

- `Usage` 是 `@dataclass`，字段 `prompt_tokens: int = 0`、
  `completion_tokens: int = 0`、`total_tokens: int = 0`。
- `CompletionResult[T]` 是 `@dataclass`：`output: T`、`usage: Usage | None = None`。
- `Client.complete` / `AsyncClient.acomplete` 返回 `CompletionResult[T]`，
  接收 `max_retries: int = 0` kwarg。
- `InstructorClient` 同步与异步两路均改用 `create_with_completion`；
  从 raw response 的 `.usage` 字段提取 `Usage`（存在才提）；转发 `max_retries`。
- `FakeClient` 接受可选 `usages: Iterable[Usage | None]`（与 `responses`
  等长或更短，更短时后续调用 usage 为 None）；`FakeCall` 新增
  `max_retries: int` 字段用于断言转发。
- `@step(..., max_retries=N)` 转发给 client；默认 0。
- `TraceRecord.usage: Usage | None = None`，由 `CompletionResult.usage` 填入。
- `Trace.to_dict() -> dict`、`Trace.to_json(**json_kwargs) -> str`、
  `TraceRecord.to_dict() -> dict`；输出模型用 `model_dump(mode="json")` 序列化。
- `Trace.total_usage() -> Usage` 汇总所有非 None 的 usage；没有则返回零 Usage。

## 不做（留给后续迭代）

- 以货币为单位的成本估算。
- 流式 usage 更新。
- 导出时自动脱敏敏感信息（用户自己 post-process `to_dict()` 结果）。
