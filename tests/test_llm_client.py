import sys
from types import SimpleNamespace

import pytest

import src.llm_client as llm_client
from src.llm_client import LLMCallError, call_llm, explain_llm_config_status, is_llm_available, load_llm_config


LLM_ENV_KEYS = [
    "LLM_ENABLED",
    "LLM_PROVIDER",
    "ARK_API_KEY",
    "ARK_BASE_URL",
    "ARK_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "LLM_TEMPERATURE",
    "LLM_TIMEOUT_SECONDS",
]


def _clear_llm_env(monkeypatch):
    for key in LLM_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _set_volcengine_env(monkeypatch, api_key: str = "valid_test_key"):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "volcengine")
    monkeypatch.setenv("ARK_API_KEY", api_key)
    monkeypatch.setenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3")
    monkeypatch.setenv("ARK_MODEL", "model-for-test")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "60")


def _set_deepseek_env(monkeypatch, api_key: str = "valid_deepseek_test_key"):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "60")


def test_missing_env_file_does_not_error(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_client, "PROJECT_ROOT", tmp_path)
    _clear_llm_env(monkeypatch)
    config = load_llm_config()
    assert config.enabled is False
    assert is_llm_available() is False


def test_llm_disabled_is_unavailable_without_config_error(monkeypatch):
    _set_deepseek_env(monkeypatch)
    monkeypatch.setenv("LLM_ENABLED", "false")
    assert is_llm_available() is False
    status = explain_llm_config_status()
    assert status["mode"] == "Deterministic Agent Mode"
    assert status["missing_fields"] == []


def test_deepseek_missing_api_key_reports_field(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    status = explain_llm_config_status()
    assert status["available"] is False
    assert "DEEPSEEK_API_KEY" in status["missing_fields"]


def test_deepseek_complete_config_is_available(monkeypatch):
    _set_deepseek_env(monkeypatch)
    status = explain_llm_config_status()
    assert is_llm_available() is True
    assert status["mode"] == "DeepSeek LLM Agent"
    assert status["base_url"] == "https://api.deepseek.com"


def test_volcengine_complete_config_still_available(monkeypatch):
    _set_volcengine_env(monkeypatch)
    status = explain_llm_config_status()
    assert is_llm_available() is True
    assert status["mode"] == "Volcengine Ark LLM Agent"
    assert status["base_url"] == "https://ark.cn-beijing.volces.com/api/coding/v3"


def test_call_llm_unavailable_does_not_leak_key(monkeypatch):
    fake_key = "valid_deepseek_test_key"
    _set_deepseek_env(monkeypatch, api_key=fake_key)
    monkeypatch.setenv("LLM_ENABLED", "false")
    with pytest.raises(LLMCallError) as exc:
        call_llm([{"role": "user", "content": "test"}])
    assert fake_key not in str(exc.value)


def test_call_llm_uses_provider_specific_config(monkeypatch):
    fake_key = "valid_deepseek_test_key"
    _set_deepseek_env(monkeypatch, api_key=fake_key)
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    assert call_llm([{"role": "user", "content": "test"}]) == "ok"
    assert captured["api_key"] == fake_key
    assert captured["base_url"] == "https://api.deepseek.com"
    assert captured["model"] == "deepseek-v4-flash"


def test_call_llm_sdk_error_does_not_leak_key(monkeypatch):
    fake_key = "valid_deepseek_test_key"
    _set_deepseek_env(monkeypatch, api_key=fake_key)

    class FakeCompletions:
        def create(self, **kwargs):
            raise RuntimeError(f"upstream rejected credential {fake_key}")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    with pytest.raises(LLMCallError) as exc:
        call_llm([{"role": "user", "content": "test"}])
    message = str(exc.value)
    assert fake_key not in message
    assert "provider=deepseek" in message
    assert "model=deepseek-v4-flash" in message
