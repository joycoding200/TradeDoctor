from __future__ import annotations
"""LLM provider abstraction with OpenAI / Claude / DeepSeek backends.

Usage:
    provider = get_llm()
    report = await provider.generate(system_prompt, user_prompt)
"""
from abc import ABC, abstractmethod

from app.config import settings


class LLMProvider(ABC):
    """Abstract base for LLM API wrappers."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the response text."""
        ...


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible chat completions API."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        import openai

        kwargs = {"api_key": settings.openai_api_key, "timeout": 60.0}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.AsyncOpenAI(**kwargs)
        self.model = model or settings.openai_model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Empty response from LLM")
        return response.choices[0].message.content.strip()


class ClaudeProvider(LLMProvider):
    """Anthropic Claude messages API."""

    def __init__(self) -> None:
        import anthropic

        self.client = anthropic.AsyncAnthropic(api_key=settings.claude_api_key, timeout=60.0)
        self.model = settings.claude_model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=4096,
            temperature=0.3,
        )
        if not response.content or not response.content[0].text:
            raise ValueError("Empty response from LLM")
        return response.content[0].text.strip()


class DeepSeekProvider(LLMProvider):
    """DeepSeek via OpenAI-compatible API endpoint."""

    def __init__(self) -> None:
        import openai

        self.client = openai.AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
            timeout=60.0,
        )
        self.model = settings.deepseek_model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Empty response from LLM")
        return response.choices[0].message.content.strip()


# Module-level cached provider — avoids connection pool leaks from repeated instantiation
_provider_instance: LLMProvider | None = None


def get_llm() -> LLMProvider:
    """Factory: return the LLM provider configured in settings. Cached for reuse.

    Raises:
        ValueError: If settings.ai_provider is not one of the supported values,
                    or if the configured API key is empty.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider = settings.ai_provider.lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        _provider_instance = OpenAIProvider()
    elif provider == "openrouter":
        base_url = settings.ai_base_url or "https://openrouter.ai/api/v1"
        model = settings.ai_model or settings.openai_model
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        _provider_instance = OpenAIProvider(base_url=base_url, model=model)
    elif provider == "claude":
        if not settings.claude_api_key:
            raise ValueError("CLAUDE_API_KEY is not configured")
        _provider_instance = ClaudeProvider()
    elif provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        _provider_instance = DeepSeekProvider()
    else:
        raise ValueError(
            f"Unknown AI provider: '{settings.ai_provider}'. "
            f"Expected one of: openai, claude, deepseek, openrouter."
        )
    return _provider_instance
