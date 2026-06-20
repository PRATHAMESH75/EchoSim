"""
LLM client wrapper
Unified calls using the OpenAI format
"""

import time
from typing import Optional, Dict, Any, List, Iterable
from openai import OpenAI

from ..config import Config
from .logger import get_logger
from .llm_sanitizer import sanitize_content, parse_json

logger = get_logger('mirofish.llm_client')

# Provider errors worth retrying: rate limits (429), timeouts, connection
# blips, and 5xx. Imported defensively so the module still loads if the openai
# SDK surface changes.
try:
    from openai import (
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        InternalServerError,
    )
    _TRANSIENT_LLM_ERRORS = (
        RateLimitError, APITimeoutError, APIConnectionError, InternalServerError,
    )
except ImportError:  # pragma: no cover - depends on openai version
    _TRANSIENT_LLM_ERRORS = ()


class LLMError(RuntimeError):
    """Uniform, user-facing failure surface for outbound LLM calls.

    Raised after retries (and fallback, if configured) are exhausted, so callers
    handle one predictable exception instead of provider-specific SDK errors.
    """


class LLMClient:
    """LLM client with per-task model, backup-model fallback, and retries."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        fallback_base_url: Optional[str] = None,
        fallback_api_key: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=Config.LLM_TIMEOUT,
        )

        # Optional backup model engaged only when a primary call raises. It may
        # target a different provider, so it keeps its own URL/key (defaulting
        # to the primary connection). The client is built lazily on first use.
        self.fallback_model = fallback_model
        self.fallback_base_url = fallback_base_url or self.base_url
        self.fallback_api_key = fallback_api_key or self.api_key
        self._fallback_client: Optional[OpenAI] = None

    @classmethod
    def for_task(cls, task: Optional[str] = None, **overrides) -> "LLMClient":
        """Build a client using the per-task model + fallback from Config.

        Keyword overrides (e.g. ``model=...``) take precedence over the resolved
        settings when not ``None``, so callers can still force a specific model.
        """
        settings = Config.llm_settings(task)
        settings.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**settings)

    def _get_fallback_client(self) -> Optional[OpenAI]:
        """Lazily build the backup client, or None when no fallback is configured."""
        if not self.fallback_model or self.fallback_model == self.model:
            return None
        if self._fallback_client is None:
            self._fallback_client = OpenAI(
                api_key=self.fallback_api_key,
                base_url=self.fallback_base_url,
                timeout=Config.LLM_TIMEOUT,
            )
        return self._fallback_client

    def _request_with_retries(self, client: OpenAI, model: str, kwargs: Dict[str, Any]) -> str:
        """Call one model, retrying transient provider errors with backoff.

        Non-transient errors (bad request, auth, etc.) raise immediately — no
        point retrying those.
        """
        delay = Config.LLM_RETRY_INITIAL_DELAY
        for attempt in range(Config.LLM_MAX_RETRIES + 1):
            try:
                response = client.chat.completions.create(model=model, **kwargs)
                return response.choices[0].message.content
            except _TRANSIENT_LLM_ERRORS as exc:
                if attempt >= Config.LLM_MAX_RETRIES:
                    raise
                wait = min(delay, Config.LLM_RETRY_MAX_DELAY)
                logger.warning(
                    "Transient LLM error on '%s' (attempt %d/%d): %s; retrying in %.1fs",
                    model, attempt + 1, Config.LLM_MAX_RETRIES, exc, wait
                )
                time.sleep(wait)
                delay *= 2

    def _create(self, kwargs: Dict[str, Any]) -> str:
        """Call the primary model (with retries), then the backup, then give up.

        Always raises :class:`LLMError` on terminal failure so callers see one
        clear, actionable error rather than a provider-specific SDK exception.
        """
        try:
            return self._request_with_retries(self.client, self.model, kwargs)
        except Exception as primary_error:
            fallback = self._get_fallback_client()
            if fallback is None:
                raise LLMError(self._failure_message(self.model, primary_error)) from primary_error
            logger.warning(
                "Primary model '%s' failed (%s); falling back to '%s'",
                self.model, primary_error, self.fallback_model
            )
            try:
                return self._request_with_retries(fallback, self.fallback_model, kwargs)
            except Exception as fallback_error:
                raise LLMError(
                    self._failure_message(self.fallback_model, fallback_error)
                ) from fallback_error

    @staticmethod
    def _failure_message(model: str, error: Exception) -> str:
        return (
            f"The language model request failed (model '{model}'): {error}. "
            "Please retry shortly; if this persists, check your LLM provider "
            "status, API key, and rate limits."
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Send a chat request

        Args:
            messages: List of messages
            temperature: Temperature parameter
            max_tokens: Maximum token count
            response_format: Response format (e.g. JSON mode)

        Returns:
            Model response text
        """
        kwargs = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        # _create selects the model (per-task) and falls back to the backup
        # model on failure. Route every response through the shared guardrail so
        # reasoning-model artefacts (e.g. <think> blocks) never leak downstream.
        content = self._create(kwargs)
        return sanitize_content(content)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        required_keys: Optional[Iterable[str]] = None
    ) -> Dict[str, Any]:
        """
        Send a chat request and return JSON

        Args:
            messages: List of messages
            temperature: Temperature parameter
            max_tokens: Maximum token count
            required_keys: Optional keys the parsed object must contain

        Returns:
            Parsed JSON object

        Raises:
            ValueError: If the response cannot be parsed/repaired into valid JSON,
                or is missing a required key. Never leaks a raw JSONDecodeError.
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # Shared layer strips fences, repairs truncated/malformed JSON, and
        # validates the schema before returning.
        return parse_json(response, required_keys=required_keys)
