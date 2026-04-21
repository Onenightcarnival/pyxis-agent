"""给 agent 一组文件操作工具 + 一个 while 循环，让它多轮自主完成任务。

结构和 `examples/agent_tool_use.py` 同源，只是工具从算数换成了 ls /
read / write / finish 四个。换任务只改 Tool 定义和 decide 的 prompt。

- `LsFiles / ReadFile / WriteFile / Finish` 是 `Tool` 子类，判别式联合
  作"工具表"。
- `@step decide` 输出 `Decision(thought, action)`，每轮出一次调用。
- `@flow harness` 就是 while 循环，带 max_steps 防失控；遇到 `Finish`
  就停。

这里的"文件系统"是一个内存 dict，聚焦讲多轮 + 工具 + 自停止这条主线；
换成真磁盘只要把 `_FS` 的读写换成 `pathlib.Path`，agent loop 不用动。

跑起来：
    OPENROUTER_API_KEY=... uv run --env-file .env python examples/coding_harness.py
"""

from __future__ import annotations

import os
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from pyxis import Tool, flow, set_default_client, step, trace
from pyxis.providers import openrouter_client

MODEL = "openai/gpt-5.4-nano"


# ---- "虚拟磁盘"：就是一个 dict，换成真磁盘只改这里 ----

_FS: dict[str, str] = {
    "todo.txt": "- buy milk\n- walk dog\n- write email\n",
    "readme.md": "# My Project\n\n这是一个实验性的待办清单工具。\n",
}


# ---- 工具：每个都是 Tool 子类，schema 里就告诉 LLM 怎么用 ----


class LsFiles(Tool):
    """列出当前目录下所有文件名。没有入参。"""

    kind: Literal["ls"] = "ls"

    def run(self) -> str:
        return "\n".join(sorted(_FS)) or "(空)"


class ReadFile(Tool):
    """读一个已存在文件的完整内容。"""

    kind: Literal["read"] = "read"
    path: str = Field(description="要读的文件路径")

    def run(self) -> str:
        if self.path not in _FS:
            return f"ERROR: 文件不存在：{self.path}"
        return _FS[self.path]


class WriteFile(Tool):
    """覆盖写入一个文件的完整内容（不存在就创建）。"""

    kind: Literal["write"] = "write"
    path: str = Field(description="要写的文件路径")
    content: str = Field(description="文件的**完整**新内容；这会覆盖原内容")

    def run(self) -> str:
        _FS[self.path] = self.content
        return f"OK: 已写入 {self.path}（{len(self.content)} 字符）"


class Finish(Tool):
    """任务完成后用此工具停止并汇报给用户。"""

    kind: Literal["finish"] = "finish"
    summary: str = Field(description="一句话总结这轮你改了什么")

    def run(self) -> str:
        return self.summary


Action = Annotated[LsFiles | ReadFile | WriteFile | Finish, Field(discriminator="kind")]


class Decision(BaseModel):
    """schema-as-CoT：每轮先想一下，再发恰好一次工具调用。"""

    thought: str = Field(description="简短推理：当前观察到什么、接下来要做什么")
    action: Action = Field(description="这一步调用的工具")


@step(output=Decision, model=MODEL)
def decide(task: str, history: str) -> str:
    """你是一个能读写文件的编码 agent。每轮**恰好**发一次工具调用。

    严格遵守：
    - 历史区每条的"OBSERVATION"就是工具的实际返回值，视为 ground truth；
      不要怀疑"还没读到"——读过就是读过。
    - 一个文件**最多 read 一次**；再读一次视为错误。
    - 修改用 `write`——它会**整体覆盖**，所以 `content` 必须是包含了旧内容
      在内的**完整新文件**，不是 diff、不是追加片段。
    - 看到 `OK: 已写入 ...` 就**立刻** `finish`，不要再 read 验证。"""
    return f"任务：{task}\n\n=== 历史 ===\n{history or '（还没开始——先决定第一步）'}"


# ---- harness 的主驱动：就是一个 @flow 包起来的 while 循环 ----


def _format_turn(i: int, d: Decision, obs: str) -> str:
    args = d.action.model_dump(exclude={"kind"})
    call = f"{d.action.kind}({', '.join(f'{k}={v!r}' for k, v in args.items())})"
    return (
        f"[轮次 {i}]\n"
        f"  THOUGHT: {d.thought}\n"
        f"  CALL: {call}\n"
        f"  OBSERVATION:\n    {obs.replace(chr(10), chr(10) + '    ')}"
    )


@flow
def harness(task: str, max_steps: int = 10) -> str:
    history: list[str] = []
    for step_i in range(1, max_steps + 1):
        d = decide(task, "\n\n".join(history))
        obs = d.action.run()
        history.append(_format_turn(step_i, d, obs))
        if isinstance(d.action, Finish):
            return obs
    raise RuntimeError(f"{max_steps} 轮未完成")


def _dump_trace(t) -> None:
    for i, rec in enumerate(t.records, 1):
        d: Decision = rec.output
        args = d.action.model_dump(exclude={"kind"})
        args_str = ", ".join(f"{k}={str(v)[:50]!r}" for k, v in args.items())
        print(f"[{i}] {d.action.kind}({args_str})")
        print(f"    thought: {d.thought[:100]}")


def main() -> None:
    set_default_client(openrouter_client(api_key=os.environ["OPENROUTER_API_KEY"]))

    task = "打开 todo.txt，在末尾追加一行 '- check PR #42'，保存，然后结束。"
    print(f"任务：{task}\n")

    before = _FS["todo.txt"]
    try:
        with trace() as t:
            result = harness(task)
    except RuntimeError as e:
        print(f"[未收敛] {e}\n=== 轮次回放 ===")
        _dump_trace(t)
        raise

    print("=== 轮次详情 ===")
    _dump_trace(t)
    print("\n=== 文件改动 ===")
    print(f"todo.txt（前）：\n{before}")
    print(f"todo.txt（后）：\n{_FS['todo.txt']}")
    print(f"\n=== agent 汇报 ===\n{result}")
    print(f"\n=== 成本 ===\n{len(t.records)} 轮；{t.total_usage().total_tokens} tokens")


if __name__ == "__main__":
    main()
