"""观察者中间件 —— `StepHook`。

在每个 Step 的开始、结束、失败处插入只读观察者，用来打点、日志、告警。
刻意设计成只读：不给 hook 留修改 messages / output / usage 的能力，
"schema as workflow" 不破。
"""

from __future__ import annotations

import contextlib
import warnings

from .client import Message
from .trace import TraceRecord


class StepHook:
    """Step 生命周期的观察者基类。三个方法默认 no-op，按需覆盖。"""

    def on_start(self, step: str, messages: list[Message], model: str) -> None:
        """Step 即将调用底层 client 时触发。约定 messages 只读。"""

    def on_end(self, record: TraceRecord) -> None:
        """TraceRecord 写入 trace 之后触发。record 只读。"""

    def on_error(
        self,
        step: str,
        messages: list[Message],
        model: str,
        error: str,
    ) -> None:
        """底层调用抛异常、error 记录已写入 trace 后触发。"""


_hooks: list[StepHook] = []


def add_hook(hook: StepHook) -> None:
    """注册一个 hook。触发顺序按注册顺序（FIFO）。"""
    _hooks.append(hook)


def remove_hook(hook: StepHook) -> None:
    """注销一个 hook。未注册则静默忽略。"""
    with contextlib.suppress(ValueError):
        _hooks.remove(hook)


def clear_hooks() -> None:
    """清空所有 hook。主要给测试用。"""
    _hooks.clear()


def _safe_call(hook: StepHook, method_name: str, *args: object) -> None:
    """调用单个 hook 的某个方法；吞异常并 warn，保证主流程不断。"""
    method = getattr(hook, method_name)
    try:
        method(*args)
    except Exception as exc:
        warnings.warn(
            f"StepHook {type(hook).__name__}.{method_name} 抛异常：{exc!r}",
            stacklevel=3,
        )


def notify_start(step: str, messages: list[Message], model: str) -> None:
    for hook in list(_hooks):
        _safe_call(hook, "on_start", step, messages, model)


def notify_end(record: TraceRecord) -> None:
    for hook in list(_hooks):
        _safe_call(hook, "on_end", record)


def notify_error(step: str, messages: list[Message], model: str, error: str) -> None:
    for hook in list(_hooks):
        _safe_call(hook, "on_error", step, messages, model, error)
