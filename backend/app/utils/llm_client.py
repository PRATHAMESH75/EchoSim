"""
LLM client wrapper
Unified calls using the OpenAI format
"""

from typing import Optional, Dict, Any, List, Iterable
from openai import OpenAI

from ..config import Config
from .llm_sanitizer import sanitize_content, parse_json


class LLMClient:
    """LLM client"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
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
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # Route every response through the shared guardrail so reasoning-model
        # artefacts (e.g. <think> blocks from MiniMax/GLM) never leak downstream.
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
