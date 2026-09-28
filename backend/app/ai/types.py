"""Provider-neutral data types shared by ChatService, LLM clients and tool providers.

Every LLM client translates these to and from its own wire format (Ollama, Bedrock, ...).
Nothing above the client layer ever sees a provider-specific shape, which is what makes
swapping providers a change to one file.
"""
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ToolDefinition:
    """A tool the model may call, described with a JSON Schema for its arguments."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """The model asking us to run a tool. We run it; the model never executes anything."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """What a tool returned: JSON text for the model. Errors are data too, so the model can recover."""

    content: str
    is_error: bool = False


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant", "tool"]
    content: str = ""
    # Set on an assistant message when the model asked for tools instead of (or before) answering.
    tool_calls: tuple[ToolCall, ...] = ()
    # Set on a tool message: which tool produced this result.
    tool_name: str | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tool_calls: tuple[ToolCall, ...] = ()
