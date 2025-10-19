"""
Transcription client factory.

This module provides a factory for creating transcription clients
based on the inference provider.
"""

from .openai_client import OpenAIClient, GroqClient, BaseAIClient
from .const import InferenceProvider


class TranscriptionClients:
    """Factory for creating transcription clients based on provider."""

    def __init__(self):
        self.clients = {}

    def get(self, provider: InferenceProvider, api_key: str) -> BaseAIClient:
        """
        Get or create a client for the specified provider.

        Args:
            provider: The inference provider (OpenAI or Groq)
            api_key: API key for the provider

        Returns:
            An instance of BaseAIClient for the specified provider

        Raises:
            ValueError: If api_key is empty or provider is not supported
        """
        if not api_key:
            raise ValueError(f"API key not found for provider {provider}")

        match provider:
            case InferenceProvider.OPENAI:
                return self.clients.setdefault(provider, OpenAIClient(api_key))
            case InferenceProvider.GROQ:
                return self.clients.setdefault(provider, GroqClient(api_key))
