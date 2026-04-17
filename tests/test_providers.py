"""Provider 工厂的测试 —— 规格 008。"""

from __future__ import annotations

import pytest

from pyxis import InstructorClient
from pyxis.providers import openai_client, openrouter_client


def test_openrouter_client_uses_explicit_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    c = openrouter_client(api_key="sk-or-test")
    assert isinstance(c, InstructorClient)


def test_openrouter_client_reads_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-env")
    c = openrouter_client()
    assert isinstance(c, InstructorClient)


def test_openrouter_client_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        openrouter_client()


def test_openai_client_uses_explicit_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    c = openai_client(api_key="sk-oai-test")
    assert isinstance(c, InstructorClient)


def test_openai_client_reads_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-oai-env")
    c = openai_client()
    assert isinstance(c, InstructorClient)


def test_openai_client_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        openai_client()


def test_openrouter_client_custom_base_url():
    c = openrouter_client(api_key="k", base_url="https://example.test/v1")
    assert isinstance(c, InstructorClient)
    # sync 与 async client 均已在构造时塞入，懒获取会直接返回它们
    assert c._sync is not None
    assert c._async is not None


def test_openai_client_base_url_optional():
    # 不传 base_url 时不会炸
    c = openai_client(api_key="k")
    assert isinstance(c, InstructorClient)
    assert c._sync is not None
    assert c._async is not None
