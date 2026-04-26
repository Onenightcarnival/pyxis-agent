"""错误传播的测试——原规格 009 围绕 `trace()` 捕获 error 展开；收敛后
pyxis 不做可观测，所以这里只断言"异常原样重抛"。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from pyxis import FakeClient, step


class Plan(BaseModel):
    goal: str
    next_action: str


class _BoomClient:
    """永远抛自定义异常的 client，用来触发任意 Exception 路径。"""

    def complete(self, messages, response_model, model, *, max_retries=0, params=None):
        raise RuntimeError("外部服务炸了")

    def stream(self, messages, response_model, model, *, max_retries=0, params=None):
        raise RuntimeError("外部服务炸了")

    async def acomplete(self, messages, response_model, model, *, max_retries=0, params=None):
        raise RuntimeError("外部服务炸了")

    async def astream(self, messages, response_model, model, *, max_retries=0, params=None):
        raise RuntimeError("外部服务炸了")
        yield  # pragma: no cover


def test_fake_client_exhaustion_reraises():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    def plan(x: str) -> str:
        """规划。"""
        return x

    with pytest.raises(RuntimeError, match="耗尽"):
        plan("x")


def test_arbitrary_backend_exception_reraises_unchanged():
    @step(output=Plan, client=_BoomClient())
    def plan(x: str) -> str:
        return x

    with pytest.raises(RuntimeError, match="外部服务炸了"):
        plan("x")


async def test_async_path_also_reraises():
    fake = FakeClient([])

    @step(output=Plan, client=fake)
    async def plan(x: str) -> str:
        return x

    with pytest.raises(RuntimeError, match="耗尽"):
        await plan("x")
