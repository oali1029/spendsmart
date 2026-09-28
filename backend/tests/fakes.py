"""Test doubles, so no test needs Ollama (or any real LLM) to be running."""
from app.ai.llm_client import LLMClient
from app.ai.types import LLMResponse, ToolCall


class FakeLLMClient(LLMClient):
    """Replays scripted responses and records every call it receives."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def chat(self, system, messages, tools):
        self.calls.append({"system": system, "messages": list(messages), "tools": list(tools)})
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def say(text: str) -> LLMResponse:
    """A final text answer."""
    return LLMResponse(text=text)


def call_tool(name: str, call_id: str = "c1", **arguments) -> LLMResponse:
    """The model asking for a tool instead of answering."""
    return LLMResponse(text="", tool_calls=(ToolCall(id=call_id, name=name, arguments=arguments),))
