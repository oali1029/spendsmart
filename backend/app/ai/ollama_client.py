"""LLMClient implementation for a local Ollama server (https://ollama.com).

Talks to Ollama's native /api/chat endpoint over plain HTTP, so no extra SDK is needed.
All Ollama-specific details (wire format, quirks) live in this file and nowhere else.
"""
import json
import logging
import uuid
from collections.abc import Sequence

import httpx

from app.ai.llm_client import LLMClient, LLMError
from app.ai.types import LLMResponse, Message, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class OllamaLLMClient(LLMClient):
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 180.0,
        temperature: float = 0.3,
        keep_alive: str = "10m",
        client: httpx.Client | None = None,
    ):
        self.url = f"{base_url.rstrip('/')}/api/chat"
        self.model = model
        self.temperature = temperature
        # Keep the model in memory between requests; reloading it is the slowest part of a cold call.
        self.keep_alive = keep_alive
        # Local models on CPU are slow, so the timeout is generous. `client` is injectable for tests.
        self._http = client or httpx.Client(timeout=timeout)

    def chat(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolDefinition]
    ) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "stream": False,  # MVP is non-streaming: one complete JSON response
            "keep_alive": self.keep_alive,
            # Low temperature: we want faithful use of tool data, not creative numbers.
            "options": {"temperature": self.temperature},
            "messages": [{"role": "system", "content": system}, *map(_message_to_ollama, messages)],
        }
        # NOTE: deliberately no "think" field. Sending think=false makes qwen3 leak its reasoning
        # into the reply text; when omitted, Ollama returns it separately in message.thinking.
        if tools:
            payload["tools"] = [_tool_to_ollama(tool) for tool in tools]

        try:
            response = self._http.post(self.url, json=payload)
            response.raise_for_status()
            body = response.json()
            message = body["message"]
        except httpx.HTTPStatusError as exc:
            # e.g. 404 when the model has not been pulled. Log detail; callers get a generic LLMError.
            logger.error("Ollama returned %s: %s", exc.response.status_code, exc.response.text[:300])
            raise LLMError(f"Ollama returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:  # connection refused, timeout, ...
            raise LLMError(f"Could not reach Ollama at {self.url}: {exc!r}") from exc
        except (ValueError, KeyError, TypeError) as exc:  # invalid JSON or unexpected shape
            raise LLMError("Ollama returned an unexpected response") from exc

        tool_calls = tuple(_tool_call_from_ollama(c) for c in message.get("tool_calls") or [])
        return LLMResponse(text=_clean_text(message.get("content") or ""), tool_calls=tool_calls)


def _tool_to_ollama(tool: ToolDefinition) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def _message_to_ollama(message: Message) -> dict:
    if message.role == "tool":
        return {"role": "tool", "tool_name": message.tool_name, "content": message.content}
    payload: dict = {"role": message.role, "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = [
            {"function": {"name": call.name, "arguments": call.arguments}}
            for call in message.tool_calls
        ]
    return payload


def _tool_call_from_ollama(raw: dict) -> ToolCall:
    function = raw.get("function") or {}
    arguments = function.get("arguments") or {}
    if isinstance(arguments, str):  # some models return arguments as a JSON string
        try:
            arguments = json.loads(arguments)
        except ValueError:
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    # Ollama does not always supply call ids; generate one so the rest of the app can rely on it.
    return ToolCall(
        id=raw.get("id") or f"call_{uuid.uuid4().hex[:8]}",
        name=function.get("name", ""),
        arguments=arguments,
    )


def _clean_text(text: str) -> str:
    # Defensive: if a model still leaks reasoning inline, keep only what follows the last </think>.
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text.strip()
