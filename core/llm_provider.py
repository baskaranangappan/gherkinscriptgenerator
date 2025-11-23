"""
LLM Provider Abstraction
Supports Groq, OpenAI, and Claude with unified interface
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
from groq import Groq
from openai import OpenAI
from anthropic import Anthropic
from .config import config, LLMConfig
from .logger import get_logger

logger = get_logger(__name__)

class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, llm_config: LLMConfig):
        self.config = llm_config
        self.client = None

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text completion"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass

class GroqProvider(BaseLLMProvider):
    """Groq LLM Provider"""

    def __init__(self, llm_config: LLMConfig):
        super().__init__(llm_config)
        api_key = llm_config.api_key or config.GROQ_API_KEY
        if not api_key:
            raise ValueError("Groq API key not found")
        self.client = Groq(api_key=api_key)
        logger.info(f"Initialized Groq provider with model: {llm_config.model}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using Groq"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq generation error: {str(e)}")
            raise

    def is_available(self) -> bool:
        """Check if Groq is available"""
        return bool(config.GROQ_API_KEY or self.config.api_key)

class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM Provider"""

    def __init__(self, llm_config: LLMConfig):
        super().__init__(llm_config)
        api_key = llm_config.api_key or config.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key not found")
        self.client = OpenAI(api_key=api_key)
        logger.info(f"Initialized OpenAI provider with model: {llm_config.model}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using OpenAI"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            raise

    def is_available(self) -> bool:
        """Check if OpenAI is available"""
        return bool(config.OPENAI_API_KEY or self.config.api_key)

class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude LLM Provider"""

    def __init__(self, llm_config: LLMConfig):
        super().__init__(llm_config)
        api_key = llm_config.api_key or config.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("Anthropic API key not found")
        self.client = Anthropic(api_key=api_key)
        logger.info(f"Initialized Claude provider with model: {llm_config.model}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using Claude"""
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt or "",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude generation error: {str(e)}")
            raise

    def is_available(self) -> bool:
        """Check if Claude is available"""
        return bool(config.ANTHROPIC_API_KEY or self.config.api_key)

class LLMFactory:
    """Factory for creating LLM providers"""

    _providers = {
        "groq": GroqProvider,
        "openai": OpenAIProvider,
        "claude": ClaudeProvider
    }

    @classmethod
    def create_provider(cls, llm_config: LLMConfig) -> BaseLLMProvider:
        """Create LLM provider instance"""
        provider_class = cls._providers.get(llm_config.provider.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {llm_config.provider}")

        return provider_class(llm_config)

    @classmethod
    def get_available_providers(cls) -> Dict[str, bool]:
        """Get availability status of all providers"""
        return {
            "groq": bool(config.GROQ_API_KEY),
            "openai": bool(config.OPENAI_API_KEY),
            "claude": bool(config.ANTHROPIC_API_KEY)
        }