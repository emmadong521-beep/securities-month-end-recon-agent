from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .config import PROJECT_ROOT


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


def _as_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _is_placeholder(api_key: str | None) -> bool:
    normalized = (api_key or "").strip()
    return normalized.lower() in PLACEHOLDER_KEYS


def load_llm_config() -> LLMConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    return LLMConfig(
        enabled=_as_bool(os.getenv("LLM_ENABLED", "false")),
        provider=os.getenv("LLM_PROVIDER", "volcengine").strip(),
        api_key=(os.getenv("ARK_API_KEY") or "").strip() or None,
        base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").strip(),
        model=os.getenv("ARK_MODEL", "doubao-seed-1-6-250615").strip(),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
        timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
    )


def is_llm_available() -> bool:
    config = load_llm_config()
    return (
        config.enabled
        and config.provider.lower() == "volcengine"
        and bool(config.api_key)
        and not _is_placeholder(config.api_key)
        and bool(config.model)
    )


def call_llm(messages: list[dict], system_prompt: str | None = None) -> str:
    config = load_llm_config()
    if not is_llm_available():
        raise RuntimeError("LLM is not available: check LLM_ENABLED, LLM_PROVIDER, ARK_API_KEY, and ARK_MODEL.")

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
        raise RuntimeError(f"LLM call failed without exposing credentials: {type(exc).__name__}") from exc
