from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


@dataclass
class LLMConfig:
    enabled: bool
    provider: str
    api_key: str | None
    base_url: str
    model: str
    temperature: float
    timeout_seconds: int
    api_key_field: str
    base_url_field: str
    model_field: str


PROVIDER_SETTINGS = {
    "volcengine": {
        "api_key_field": "ARK_API_KEY",
        "base_url_field": "ARK_BASE_URL",
        "model_field": "ARK_MODEL",
        "default_base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "default_model": "your_model_or_endpoint_id_here",
        "mode": "Volcengine Ark LLM Agent",
        "message": "LLM 配置完整，可使用火山方舟增强模式。",
    },
    "deepseek": {
        "api_key_field": "DEEPSEEK_API_KEY",
        "base_url_field": "DEEPSEEK_BASE_URL",
        "model_field": "DEEPSEEK_MODEL",
        "default_base_url": "https://api.deepseek.com",
        "default_model": "deepseek-v4-flash",
        "mode": "DeepSeek LLM Agent",
        "message": "LLM 配置完整，可使用 DeepSeek 增强模式。",
    },
}

PLACEHOLDER_KEYS = {
    "",
    "your_key",
    "your_key_here",
    "your_ark_api_key_here",
    "your_deepseek_api_key_here",
    "changeme",
    "placeholder",
    "replace_me",
}
PLACEHOLDER_MODELS = {"", "your_model_or_endpoint_id_here", "your_model_id_here"}


class LLMCallError(RuntimeError):
    def __init__(
        self,
        message: str,
        provider: str = "",
        base_url: str = "",
        model: str = "",
        error_type: str = "",
    ):
        self.provider = provider
        self.base_url = base_url
        self.model = model
        self.error_type = error_type
        self.error_summary = message
        detail = (
            f"provider={provider or 'unknown'}; "
            f"base_url={base_url or 'unknown'}; "
            f"model={model or 'unknown'}; "
            f"error_type={error_type or 'unknown'}; "
            f"error_summary={message}"
        )
        super().__init__(detail)


def _as_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _secret_value(key: str) -> str | None:
    try:
        import streamlit as st

        value = st.secrets.get(key)  # type: ignore[attr-defined]
        if value is None:
            return None
        return str(value)
    except Exception:
        return None


def _setting(key: str, default: str | None = None) -> str | None:
    env_value = os.getenv(key)
    if env_value is not None and str(env_value).strip() != "":
        return str(env_value)
    secret = _secret_value(key)
    if secret is not None and str(secret).strip() != "":
        return str(secret)
    return default


def _is_placeholder(api_key: str | None) -> bool:
    normalized = (api_key or "").strip().lower()
    return normalized in PLACEHOLDER_KEYS


def _is_placeholder_model(model: str | None) -> bool:
    normalized = (model or "").strip().lower()
    return normalized in PLACEHOLDER_MODELS


def _safe_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _sanitize_summary(summary: str, api_key: str | None) -> str:
    cleaned = str(summary).replace("\n", " ").strip()
    if api_key:
        cleaned = cleaned.replace(api_key, "[REDACTED]")
    return cleaned[:500]


def load_llm_config() -> LLMConfig:
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
    provider = (_setting("LLM_PROVIDER", "volcengine") or "volcengine").strip().lower()
    provider_meta = PROVIDER_SETTINGS.get(provider, PROVIDER_SETTINGS["volcengine"])
    api_key_field = provider_meta["api_key_field"]
    base_url_field = provider_meta["base_url_field"]
    model_field = provider_meta["model_field"]
    return LLMConfig(
        enabled=_as_bool(_setting("LLM_ENABLED", "false")),
        provider=provider,
        api_key=(_setting(api_key_field, "") or "").strip() or None,
        base_url=(_setting(base_url_field, provider_meta["default_base_url"]) or "").strip(),
        model=(_setting(model_field, provider_meta["default_model"]) or "").strip(),
        temperature=_safe_float(_setting("LLM_TEMPERATURE", "0.2"), 0.2),
        timeout_seconds=_safe_int(_setting("LLM_TIMEOUT_SECONDS", "60"), 60),
        api_key_field=api_key_field,
        base_url_field=base_url_field,
        model_field=model_field,
    )


def is_llm_available() -> bool:
    return bool(explain_llm_config_status()["available"])


def explain_llm_config_status() -> dict:
    config = load_llm_config()
    if not config.enabled:
        return {
            "available": False,
            "mode": "Deterministic Agent Mode",
            "provider": config.provider,
            "base_url": config.base_url,
            "model": config.model,
            "missing_fields": [],
            "message": "LLM_ENABLED=false，当前使用确定性 Agent 模式。",
            "api_key_configured": bool(config.api_key and not _is_placeholder(config.api_key)),
        }

    missing_fields = []
    provider_meta = PROVIDER_SETTINGS.get(config.provider)
    if provider_meta is None:
        missing_fields.append("LLM_PROVIDER")
    if not config.api_key or _is_placeholder(config.api_key):
        missing_fields.append(config.api_key_field)
    if not config.base_url:
        missing_fields.append(config.base_url_field)
    if not config.model or _is_placeholder_model(config.model):
        missing_fields.append(config.model_field)

    available = not missing_fields
    mode = provider_meta["mode"] if available and provider_meta else "Deterministic Agent Mode"
    message = (
        provider_meta["message"]
        if available and provider_meta
        else f"LLM 配置不完整，缺失或无效字段：{', '.join(missing_fields)}。"
    )
    return {
        "available": available,
        "mode": mode,
        "provider": config.provider,
        "base_url": config.base_url,
        "model": config.model,
        "missing_fields": missing_fields,
        "message": message,
        "api_key_configured": bool(config.api_key and not _is_placeholder(config.api_key)),
    }


def call_llm(messages: list[dict], system_prompt: str | None = None) -> str:
    config = load_llm_config()
    if not is_llm_available():
        status = explain_llm_config_status()
        raise LLMCallError(
            status["message"],
            provider=config.provider,
            base_url=config.base_url,
            model=config.model,
            error_type="ConfigUnavailable",
        )

    prepared_messages = list(messages)
    if system_prompt:
        prepared_messages = [{"role": "system", "content": system_prompt}] + prepared_messages

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )
        response = client.chat.completions.create(
            model=config.model,
            messages=prepared_messages,
            temperature=config.temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        if isinstance(exc, LLMCallError):
            raise
        raise LLMCallError(
            _sanitize_summary(str(exc), config.api_key),
            provider=config.provider,
            base_url=config.base_url,
            model=config.model,
            error_type=type(exc).__name__,
        ) from exc
