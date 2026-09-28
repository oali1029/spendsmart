"""The provider-independent LLM interface.

ChatService depends only on this. To add Amazon Bedrock (or a hosted API) later, write a new
subclass and register it in llm_factory.py; ChatService does not change.
"""
from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.ai.types import LLMResponse, Message, ToolDefinition


class LLMError(Exception):
    """The LLM provider failed (unreachable, timed out, bad response). Mapped to HTTP 502."""


class LLMClient(ABC):
    @abstractmethod
    def chat(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolDefinition]
    ) -> LLMResponse:
        """One model call. Returns either final text or a request to call tools (or both).

        Pass an empty `tools` list to forbid tool calls on this turn.
        Implementations must raise LLMError (never a provider-specific exception) on failure.
        """
