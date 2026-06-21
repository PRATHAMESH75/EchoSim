"""
LLM client wrapper
Unified calls using the OpenAI format
"""

from typing import Optional, Dict, Any, List, Iterable
from openai import OpenAI

from ..config import Config
from .logger import get_logger
from .llm_sanitizer import sanitize_content, parse_json

logger = get_logger('mirofish.llm_client')


class LLMClient:
    """LLM client with optional per-task model and backup-model fallback."""

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
            base_url=self.base_url
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
                base_url=self.fallback_base_url
            )
        return self._fallback_client

    def _create(self, kwargs: Dict[str, Any]) -> str:
        """Call the primary model, falling back to the backup model on failure."""
        try:
            response = self.client.chat.completions.create(model=self.model, **kwargs)
            return response.choices[0].message.content
        except Exception as primary_error:
            fallback = self._get_fallback_client()
            if fallback is None:
                raise
            logger.warning(
                "Primary model '%s' failed (%s); falling back to '%s'",
                self.model, primary_error, self.fallback_model
            )
            response = fallback.chat.completions.create(model=self.fallback_model, **kwargs)
            return response.choices[0].message.content

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
