"""llm_client.py — Unified LLM access layer with retry + fallback.

Call hierarchy:
  call_llm(prompt, model) → result string
    retry on Gemini 429 with exponential backoff (1s, 2s, 4s)
    fallback to Groq after MAX_GEMINI_RETRIES exhausted
    deterministic SQL templates are the final fallback (handled upstream)

This module is the ONLY place that knows about LLM HTTP calls.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .observability import log_event
from .runtime_config import get_runtime_config

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Retry config for Gemini quota errors (429 / ResourceExhausted)
MAX_GEMINI_RETRIES = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)

_RATE_LIMIT_PHRASES = (
    "429",
    "resource_exhausted",
    "resourceexhausted",
    "quota",
    "rate limit",
    "too many requests",
)


class ModelResponse:
    """Unified response wrapper — same interface for Gemini and Groq."""

    def __init__(self, text: str, provider: str = "gemini") -> None:
        self.text = text
        self.provider = provider


class GroqModel:
    """Minimal Groq client that speaks the same generate_content() interface as Gemini."""

    provider = "groq"

    def __init__(self, api_key: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def _to_messages(self, prompt: Any) -> list[dict[str, str]]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]

        if isinstance(prompt, list):
            out: list[dict[str, str]] = []
            for item in prompt:
                if not isinstance(item, dict):
                    continue
                role = item.get("role", "user")
                if role == "model":
                    role = "assistant"
                parts = item.get("parts")
                if isinstance(parts, list):
                    chunks: list[str] = [
                        str(p.get("text", "")) if isinstance(p, dict) else str(p)
                        for p in parts
                        if p
                    ]
                    content = "\n".join(c for c in chunks if c).strip()
                else:
                    content = str(item.get("content", "")).strip()
                if content:
                    out.append({"role": role, "content": content})
            if out:
                return out

        return [{"role": "user", "content": str(prompt)}]

    def generate_content(
        self,
        prompt: Any,
        request_options: dict[str, Any] | None = None,
    ) -> ModelResponse:
        timeout = (request_options or {}).get(
            "timeout", get_runtime_config().llm_timeout_seconds
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": self._to_messages(prompt),
            "temperature": 0,
        }
        response = httpx.post(
            GROQ_API_URL, headers=headers, json=payload, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        text = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        return ModelResponse(text or "", provider="groq")


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(phrase in msg for phrase in _RATE_LIMIT_PHRASES)


def call_llm_with_retry(
    prompt: Any,
    primary_model: Any,
    fallback_model: GroqModel | None,
    trace_id: str,
    request_options: dict[str, Any] | None = None,
) -> str:
    """Call primary (Gemini) with exponential backoff on 429; fall back to Groq.

    Returns the text string from the LLM.
    Raises LLMUnavailableError if all providers exhausted.
    """
    last_error: Exception | None = None

    # ── Gemini with retry ────────────────────────────────────────────────────
    if primary_model is not None:
        for attempt in range(MAX_GEMINI_RETRIES):
            try:
                response = primary_model.generate_content(
                    prompt, request_options=request_options
                )
                # Gemini returns an object with .text; Groq returns ModelResponse
                text = getattr(response, "text", None) or ""
                if text:
                    log_event(
                        trace_id,
                        "llm_success",
                        {"provider": "gemini", "attempt": attempt + 1},
                    )
                    return text
            except Exception as exc:
                last_error = exc
                if _is_rate_limit_error(exc):
                    wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
                    log_event(
                        trace_id,
                        "llm_rate_limit",
                        {
                            "provider": "gemini",
                            "attempt": attempt + 1,
                            "wait_s": wait,
                            "error": str(exc)[:120],
                        },
                    )
                    time.sleep(wait)
                else:
                    # Non-quota error (auth, network) — skip retries, go to fallback
                    log_event(
                        trace_id,
                        "llm_error",
                        {"provider": "gemini", "error": str(exc)[:200]},
                    )
                    break

    # ── Groq fallback ────────────────────────────────────────────────────────
    if fallback_model is not None:
        try:
            log_event(trace_id, "llm_fallback_attempt", {"provider": "groq"})
            response = fallback_model.generate_content(
                prompt, request_options=request_options
            )
            text = getattr(response, "text", None) or ""
            if text:
                log_event(trace_id, "llm_success", {"provider": "groq"})
                return text
        except Exception as exc:
            last_error = exc
            log_event(
                trace_id,
                "llm_error",
                {"provider": "groq", "error": str(exc)[:200]},
            )

    raise LLMUnavailableError(
        "All LLM providers are temporarily unavailable."
    ) from last_error


class LLMUnavailableError(RuntimeError):
    """Raised when both Gemini and Groq have failed."""
