"""Unified LLM failover executor for all execution paths.

Provides a shared failover policy across chat/channel/background paths:
1. Try primary if available
2. If primary missing/unavailable, use fallback directly
3. If primary fails with retryable error, retry once on fallback
4. If error is non-retryable (auth/validation/schema), do not switch
5. Max attempts per request: 2 (primary + fallback)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, TypeVar

from loguru import logger

from app.services.llm_client import LLMError, LLMMessage, LLMResponse
from app.services.llm_utils import create_llm_client, get_max_tokens


class FailoverErrorType(Enum):
    """Classification of LLM errors for failover decisions."""

    RETRYABLE = "retryable"  # Network timeout, 429, 5xx, transient errors
    NON_RETRYABLE = "non_retryable"  # Auth, validation, schema errors
    UNKNOWN = "unknown"


@dataclass
class FailoverResult:
    """Result of a failover invocation."""

    content: str
    success: bool
    model_used: str  # "primary" or "fallback"
    error: str | None = None


# Type variable for the invoke function return type
T = TypeVar("T")


def classify_error(error: Exception) -> FailoverErrorType:
    """Classify an exception as retryable or non-retryable.

    Retryable errors:
    - Network timeout / connection errors
    - Provider 429 (rate limit)
    - Provider 5xx (server errors)
    - Explicit transient provider errors

    Non-retryable errors:
    - Auth errors (401, 403)
    - Validation errors (400, 422)
    - Schema errors
    - Content policy violations
    """
    error_msg = str(error).lower()
    error_type = type(error).__name__.lower()

    # Non-retryable: authentication and authorization
    if any(kw in error_msg for kw in ["auth", "unauthorized", "forbidden", "invalid api key", "api key invalid"]):
        return FailoverErrorType.NON_RETRYABLE

    # Non-retryable: validation and schema
    if any(kw in error_msg for kw in ["validation", "invalid request", "schema", "bad request"]):
        return FailoverErrorType.NON_RETRYABLE

    # Non-retryable: content policy
    if any(kw in error_msg for kw in ["content policy", "content_filter", "safety", "moderation"]):
        return FailoverErrorType.NON_RETRYABLE

    # Retryable: rate limiting
    if any(kw in error_msg for kw in ["rate limit", "429", "too many requests"]):
        return FailoverErrorType.RETRYABLE

    # Retryable: server errors
    if any(kw in error_msg for kw in ["500", "502", "503", "504", "server error", "internal error"]):
        return FailoverErrorType.RETRYABLE

    # Retryable: network and timeout
    if any(kw in error_msg for kw in ["timeout", "connection", "network", "unreachable", "refused", "reset", "dns"]):
        return FailoverErrorType.RETRYABLE

    # Retryable: transient errors
    if any(kw in error_msg for kw in ["temporary", "transient", "unavailable", "overloaded", "busy"]):
        return FailoverErrorType.RETRYABLE

    # LLMError with specific patterns
    if isinstance(error, LLMError):
        # Check the error message for HTTP status codes
        if any(code in error_msg for code in ["401", "403", "400", "422"]):
            return FailoverErrorType.NON_RETRYABLE
        if any(code in error_msg for code in ["429", "500", "502", "503", "504", "408"]):
            return FailoverErrorType.RETRYABLE

    return FailoverErrorType.UNKNOWN


async def invoke_with_failover(
    primary_model,
    fallback_model,
    invoke_fn: Callable[..., Awaitable[T]],
    *args,
    **kwargs,
) -> tuple[T | None, str, str | None]:
    """Invoke LLM with automatic failover from primary to fallback.

    Args:
        primary_model: The primary LLM model config (can be None)
        fallback_model: The fallback LLM model config (can be None)
        invoke_fn: Async function to call the LLM (e.g., client.complete)
        *args, **kwargs: Arguments to pass to invoke_fn

    Returns:
        Tuple of (result, model_used, error)
        - result: The LLM response or None if both failed
        - model_used: "primary", "fallback", or "none"
        - error: Error message if both failed, None otherwise
    """
    # Config-level fallback: if no primary, use fallback directly
    if primary_model is None and fallback_model is not None:
        logger.info("[Failover] Primary model not configured, using fallback directly")
        primary_model = fallback_model
        fallback_model = None

    if primary_model is None:
        return None, "none", "No LLM model configured (primary or fallback)"

    # Try primary model
    try:
        logger.debug(f"[Failover] Invoking primary model: {primary_model.provider}/{primary_model.model}")
        result = await invoke_fn(*args, **kwargs)
        return result, "primary", None
    except Exception as e:
        error_type = classify_error(e)
        error_msg = str(e) or repr(e)

        logger.warning(
            f"[Failover] Primary model failed ({error_type.value}): {error_msg[:150]}"
        )

        # Non-retryable errors: don't attempt fallback
        if error_type == FailoverErrorType.NON_RETRYABLE:
            logger.info("[Failover] Non-retryable error, not attempting fallback")
            return None, "none", f"Primary failed (non-retryable): {error_msg}"

        # No fallback available
        if fallback_model is None:
            logger.warning("[Failover] No fallback model available")
            return None, "none", f"Primary failed: {error_msg}"

        # Runtime fallback: retry with fallback model
        logger.info(f"[Failover] Retrying with fallback model: {fallback_model.provider}/{fallback_model.model}")

        try:
            # Update kwargs with fallback model if needed
            if "model" in kwargs:
                kwargs["model"] = fallback_model

            result = await invoke_fn(*args, **kwargs)
            logger.info("[Failover] Fallback model succeeded")
            return result, "fallback", None

        except Exception as e2:
            error_msg2 = str(e2) or repr(e2)
            logger.error(f"[Failover] Fallback model also failed: {error_msg2[:150]}")
            return None, "none", f"Primary: {error_msg[:80]} | Fallback: {error_msg2[:80]}"


async def call_llm_with_failover(
    primary_model,
    fallback_model,
    messages: list[LLMMessage],
    tools: list | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    timeout: float = 120.0,
    stream: bool = False,
    on_chunk=None,
    on_thinking=None,
) -> tuple[LLMResponse | None, str, str | None]:
    """Call LLM with automatic failover support.

    This is the unified entry point for all LLM calls with failover.

    Args:
        primary_model: Primary LLM model config
        fallback_model: Fallback LLM model config
        messages: List of LLMMessage
        tools: Optional tool definitions
        temperature: Sampling temperature
        max_tokens: Max output tokens
        timeout: Request timeout
        stream: Whether to use streaming API
        on_chunk: Callback for streaming chunks
        on_thinking: Callback for thinking/reasoning content

    Returns:
        Tuple of (response, model_used, error)
    """
    async def _invoke(model):
        client = create_llm_client(
            provider=model.provider,
            api_key=model.api_key_encrypted,
            model=model.model,
            base_url=model.base_url,
            timeout=timeout,
        )

        _max_tokens = max_tokens or get_max_tokens(
            model.provider, model.model, getattr(model, "max_output_tokens", None)
        )

        try:
            if stream:
                response = await client.stream(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=_max_tokens,
                    on_chunk=on_chunk,
                    on_thinking=on_thinking,
                )
            else:
                response = await client.complete(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=_max_tokens,
                )
            return response
        finally:
            await client.close()

    return await invoke_with_failover(primary_model, fallback_model, _invoke, primary_model)


# Backward compatibility: re-export for convenience
__all__ = [
    "FailoverErrorType",
    "FailoverResult",
    "classify_error",
    "invoke_with_failover",
    "call_llm_with_failover",
]
