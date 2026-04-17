"""便捷工厂：一行拿到常见 provider 的 `InstructorClient`。

每个工厂都同时构造 sync + async 两路，直接塞给 `InstructorClient`。
api_key 不给时从对应的环境变量读；都没有则抛 `RuntimeError`，错误
消息里显式写明缺哪个环境变量，方便排查。
"""

from __future__ import annotations

import os

import instructor
from openai import AsyncOpenAI, OpenAI

from .client import InstructorClient

OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def _require_key(explicit: str | None, env_var: str) -> str:
    key = explicit or os.environ.get(env_var)
    if not key:
        raise RuntimeError(
            f"未提供 api_key，且环境变量 {env_var} 未设置；"
            f"请在调用时传入 api_key，或在运行前 export {env_var}。"
        )
    return key


def openrouter_client(
    *,
    api_key: str | None = None,
    base_url: str = OPENROUTER_DEFAULT_BASE_URL,
) -> InstructorClient:
    """OpenRouter 的 `InstructorClient`（sync + async 同时就绪）。

    未传 api_key 时从 `OPENROUTER_API_KEY` 读。
    """
    key = _require_key(api_key, "OPENROUTER_API_KEY")
    return InstructorClient(
        instructor_client=instructor.from_openai(OpenAI(api_key=key, base_url=base_url)),
        async_instructor_client=instructor.from_openai(AsyncOpenAI(api_key=key, base_url=base_url)),
    )


def openai_client(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> InstructorClient:
    """OpenAI 的 `InstructorClient`（sync + async 同时就绪）。

    未传 api_key 时从 `OPENAI_API_KEY` 读。`base_url=None` 不传给 SDK
    （走 OpenAI 官方默认地址）。
    """
    key = _require_key(api_key, "OPENAI_API_KEY")
    sync_kwargs: dict[str, str] = {"api_key": key}
    async_kwargs: dict[str, str] = {"api_key": key}
    if base_url is not None:
        sync_kwargs["base_url"] = base_url
        async_kwargs["base_url"] = base_url
    return InstructorClient(
        instructor_client=instructor.from_openai(OpenAI(**sync_kwargs)),
        async_instructor_client=instructor.from_openai(AsyncOpenAI(**async_kwargs)),
    )
