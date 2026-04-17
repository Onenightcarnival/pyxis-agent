# 008：Provider 工厂与 JSONL 落盘

## 目的

生产用户每次都要手动凑 `instructor.from_openai(OpenAI(api_key=..., base_url=...))` 的同步与异步两路——样板太多。把常见 provider 包成一行工厂。同时给
`Trace` 加一个 `to_jsonl(path)`，让结构化日志能直接 append 到文件，不
需要用户自己再写一层 pipe。

## API 草图

```python
from pyxis import set_default_client, trace
from pyxis.providers import openrouter_client, openai_client

# 一行拿到同时含 sync + async 的 InstructorClient
set_default_client(openrouter_client(api_key="sk-or-..."))
# 或全部从 env 读
set_default_client(openrouter_client())     # 读 OPENROUTER_API_KEY

# 把一次运行落到本地日志
with trace() as t:
    my_flow("x")
t.to_jsonl("logs/runs.jsonl")
```

## 验收标准

- `pyxis.providers.openrouter_client(*, api_key=None, base_url="https://openrouter.ai/api/v1")`
  返回一个 `InstructorClient`，sync 与 async 两路都已配置。未提供
  `api_key` 时从环境变量 `OPENROUTER_API_KEY` 读；两处都没有则抛
  `RuntimeError`，错误消息里写明缺哪个 env。
- `pyxis.providers.openai_client(*, api_key=None, base_url=None)` 同构。
  未提供时从 `OPENAI_API_KEY` 读。`base_url=None` 不传给 OpenAI SDK
  （走官方默认）。
- `Trace.to_jsonl(path)` 以 **append** 模式打开 `path`（`str | Path`），
  每条 `TraceRecord` 序列化为一行 JSON（`ensure_ascii=False`，末尾换行）。
  文件不存在时自动创建。父目录必须存在（不递归建目录——显式优于隐式）。
  完成后关闭文件；不返回值。
- `to_jsonl` 写出的文件，**每一行** 能被 `json.loads` 回去，且结构与
  `TraceRecord.to_dict()` 一致。

## 不做（留给后续迭代）

- `anthropic_client` 工厂（需要处理 instructor 对 Anthropic 的不同调用面，
  留到 v1.1）。
- 流式落盘（每写一条 flush）——iter 12 流式输出覆盖。
- `to_jsonl` 的覆盖写模式、gzip、轮转——需要时用户自己包一层。
