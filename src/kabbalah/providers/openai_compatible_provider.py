"""Generic provider for OpenAI-compatible chat completion APIs."""

from __future__ import annotations

import os
import time
from typing import Dict, Iterator, Optional

import requests

from .base import BaseProvider, ProviderResponse


class OpenAICompatibleProvider(BaseProvider):
    """Provider adapter for services exposing ``/chat/completions``."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str,
        api_key_env: Optional[str] = None,
        model: str,
        input_cost_per_1m_tokens: float = 0.0,
        output_cost_per_1m_tokens: float = 0.0,
        **kwargs,
    ):
        """Initialize the OpenAI-compatible provider."""
        resolved_api_key = api_key
        if resolved_api_key is None and api_key_env:
            resolved_api_key = os.getenv(api_key_env)

        super().__init__(api_key=resolved_api_key, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.model = model
        self.input_cost_per_1m_tokens = input_cost_per_1m_tokens
        self.output_cost_per_1m_tokens = output_cost_per_1m_tokens

    def execute_request(
        self,
        request: Dict,
        timeout: float = 30.0,
    ) -> ProviderResponse:
        """Execute a chat completion request."""
        self.validate_request(request)

        payload = {
            "model": request.get("model") or self.model,
            "messages": request["messages"],
            "temperature": request.get("temperature", 0.7),
            "max_tokens": request.get("max_tokens", 1024),
        }
        if "top_p" in request:
            payload["top_p"] = request["top_p"]

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        started = time.time()
        response = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        latency_ms = (time.time() - started) * 1000
        response.raise_for_status()
        data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
        cost = self._calculate_cost_from_usage(prompt_tokens, completion_tokens)

        provider_response = ProviderResponse(
            content=content,
            model=data.get("model") or payload["model"],
            tokens_used=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            raw_response=data,
        )
        self._record_call(provider_response)
        return provider_response

    def stream_request(
        self,
        request: Dict,
        timeout: float = 30.0,
    ) -> Iterator[ProviderResponse]:
        """Streaming is intentionally not implemented in the generic adapter yet."""
        raise NotImplementedError("OpenAI-compatible streaming is not implemented")

    def validate_request(self, request: Dict) -> bool:
        """Validate the chat completion request shape."""
        messages = request.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("OpenAI-compatible request requires non-empty messages list")
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("Each message must be a dictionary")
            if "role" not in message or "content" not in message:
                raise ValueError("Each message requires role and content")
        return True

    def calculate_cost(self, tokens_used: int, model: str) -> float:
        """Calculate an approximate total-token cost when split usage is unavailable."""
        blended = (self.input_cost_per_1m_tokens + self.output_cost_per_1m_tokens) / 2
        return round((tokens_used / 1_000_000) * blended, 8)

    def _calculate_cost_from_usage(self, prompt_tokens: int, completion_tokens: int) -> float:
        return round(
            (prompt_tokens / 1_000_000) * self.input_cost_per_1m_tokens
            + (completion_tokens / 1_000_000) * self.output_cost_per_1m_tokens,
            8,
        )
