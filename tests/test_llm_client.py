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
    "LLM_TEMPERATURE",
    "LLM_TIMEOUT_SECONDS",
]


def _clear_llm_env(monkeypatch):
    for key in LLM_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _set_complete_env(monkeypatch, api_key: str = "valid_test_key"):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "volcengine")
    monkeypatch.setenv("ARK_API_KEY", api_key)
    monkeypatch.setenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3")
    monkeypatch.setenv("ARK_MODEL", "model-for-test")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "60")


def test_missing_env_file_does_not_error(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_client, "PROJECT_ROOT", tmp_path)
    _clear_llm_env(monkeypatch)
    config = load_llm_config()
    assert config.enabled is False
    assert is_llm_available() is False


def test_llm_disabled_is_unavailable(monkeypatch):
    _set_complete_env(monkeypatch)
    monkeypatch.setenv("LLM_ENABLED", "false")
    assert is_llm_available() is False


def test_placeholder_api_key_is_unavailable(monkeypatch):
    _set_complete_env(monkeypatch, api_key="your_ark_api_key_here")
    assert is_llm_available() is False


def test_complete_config_is_available(monkeypatch):
    _set_complete_env(monkeypatch)
    assert is_llm_available() is True


def test_explain_llm_config_status_fields(monkeypatch):
    _set_complete_env(monkeypatch)
    status = explain_llm_config_status()
    assert {"available", "mode", "provider", "base_url", "model", "missing_fields", "message"}.issubset(status)
    assert status["available"] is True
    assert status["mode"] == "Volcengine Ark LLM Agent"


def test_call_llm_unavailable_does_not_leak_key(monkeypatch):
    fake_key = "valid_test_key"
    _set_complete_env(monkeypatch, api_key=fake_key)
    monkeypatch.setenv("LLM_ENABLED", "false")
    with pytest.raises(LLMCallError) as exc:
        call_llm([{"role": "user", "content": "test"}])
    assert fake_key not in str(exc.value)


def test_call_llm_sdk_error_does_not_leak_key(monkeypatch):
    fake_key = "valid_test_key"
    _set_complete_env(monkeypatch, api_key=fake_key)

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
    assert "provider=volcengine" in message
    assert "model=model-for-test" in message
