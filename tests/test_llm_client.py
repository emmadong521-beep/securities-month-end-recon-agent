import pytest

from src.llm_client import call_llm, is_llm_available, load_llm_config


def test_llm_disabled_is_unavailable(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "volcengine")
    monkeypatch.setenv("ARK_API_KEY", "fake_key_value_for_test_only")
    monkeypatch.setenv("ARK_MODEL", "model-for-test")
    assert is_llm_available() is False


def test_empty_api_key_is_unavailable(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "volcengine")
    monkeypatch.setenv("ARK_API_KEY", "")
    monkeypatch.setenv("ARK_MODEL", "model-for-test")
    assert is_llm_available() is False


def test_placeholder_api_key_is_unavailable(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "volcengine")
    monkeypatch.setenv("ARK_API_KEY", "your_ark_api_key_here")
    monkeypatch.setenv("ARK_MODEL", "model-for-test")
    assert is_llm_available() is False


def test_load_llm_config(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "volcengine")
    monkeypatch.setenv("ARK_API_KEY", "fake_key_value_for_test_only")
    monkeypatch.setenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    monkeypatch.setenv("ARK_MODEL", "model-for-test")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "60")
    config = load_llm_config()
    assert config.enabled is True
    assert config.provider == "volcengine"
    assert config.model == "model-for-test"
    assert config.timeout_seconds == 60


def test_call_llm_unavailable_does_not_leak_key(monkeypatch):
    fake_key = "fake_key_value_for_test_only"
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "volcengine")
    monkeypatch.setenv("ARK_API_KEY", fake_key)
    monkeypatch.setenv("ARK_MODEL", "model-for-test")
    with pytest.raises(RuntimeError) as exc:
        call_llm([{"role": "user", "content": "test"}])
    assert fake_key not in str(exc.value)
