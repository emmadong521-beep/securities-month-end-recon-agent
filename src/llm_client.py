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


PLACEHOLDER_KEYS = {"", "your_ark_api_key_here", "changeme", "placeholder", "replace_me"}


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


def _is_placeholder(api_key: str | None) -> bool:
    normalized = (api_key or "").strip()
    return normalized.lower() in PLACEHOLDER_KEYS


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
    return LLMConfig(
        enabled=_as_bool(os.getenv("LLM_ENABLED", "false")),
        provider=os.getenv("LLM_PROVIDER", "volcengine").strip(),
        api_key=(os.getenv("ARK_API_KEY") or "").strip() or None,
        base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3").strip(),
        model=os.getenv("ARK_MODEL", "your_model_or_endpoint_id_here").strip(),
        temperature=_safe_float(os.getenv("LLM_TEMPERATURE", "0.2"), 0.2),
        timeout_seconds=_safe_int(os.getenv("LLM_TIMEOUT_SECONDS", "60"), 60),
    )


def is_llm_available() -> bool:
    return bool(explain_llm_config_status()["available"])


def explain_llm_config_status() -> dict:
    config = load_llm_config()
    missing_fields = []
    if not config.enabled:
        missing_fields.append("LLM_ENABLED")
    if config.provider.lower() != "volcengine":
        missing_fields.append("LLM_PROVIDER")
    if not config.api_key or _is_placeholder(config.api_key):
        missing_fields.append("ARK_API_KEY")
    if not config.base_url:
        missing_fields.append("ARK_BASE_URL")
    if not config.model:
        missing_fields.append("ARK_MODEL")

    available = not missing_fields
    mode = "Volcengine Ark LLM Agent" if available else "Mock Agent"
    message = "LLM 配置完整，可使用火山方舟增强模式。" if available else f"LLM 配置不完整，缺失或无效字段：{', '.join(missing_fields)}。"
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
