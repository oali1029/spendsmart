"""OllamaLLMClient tested against a fake HTTP transport: no Ollama server needed."""
import json

import httpx
import pytest

from app.ai.llm_client import LLMError
from app.ai.ollama_client import OllamaLLMClient
from app.ai.types import Message, ToolCall, ToolDefinition

TOOL = ToolDefinition(
    name="get_monthly_summary",
    description="Summary",
    parameters={"type": "object", "properties": {"month": {"type": "string"}}, "required": ["month"]},
)


def make_client(handler) -> OllamaLLMClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return OllamaLLMClient("http://ollama.test/", "test-model", client=http)


def reply(message: dict) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", **message}})


def test_request_has_the_expected_shape():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return reply({"content": "hi"})

    make_client(handler).chat("SYSTEM", [Message(role="user", content="hello")], [TOOL])

    body = seen["body"]
    assert seen["url"] == "http://ollama.test/api/chat"
    assert body["model"] == "test-model"
    assert body["stream"] is False
    assert "think" not in body  # think=false makes qwen3 leak its reasoning into the reply
    assert body["messages"] == [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "hello"},
    ]
    assert body["tools"] == [
        {
            "type": "function",
            "function": {"name": "get_monthly_summary", "description": "Summary", "parameters": TOOL.parameters},
        }
    ]


def test_no_tools_means_no_tools_field():
    seen = {}

    def handler(request: httpx.Request):
        seen["body"] = json.loads(request.content)
        return reply({"content": "hi"})

    make_client(handler).chat("s", [Message(role="user", content="x")], [])
    assert "tools" not in seen["body"]


def test_tool_call_history_is_translated():
    seen = {}

    def handler(request: httpx.Request):
        seen["body"] = json.loads(request.content)
        return reply({"content": "done"})

    messages = [
        Message(role="user", content="how am I doing?"),
        Message(
            role="assistant",
            tool_calls=(ToolCall(id="c1", name="get_monthly_summary", arguments={"month": "2026-09"}),),
        ),
        Message(role="tool", content='{"remaining": "450.00"}', tool_name="get_monthly_summary"),
    ]
    make_client(handler).chat("s", messages, [TOOL])

    _, _, assistant, tool = seen["body"]["messages"]
    assert assistant["tool_calls"] == [
        {"function": {"name": "get_monthly_summary", "arguments": {"month": "2026-09"}}}
    ]
    assert tool == {"role": "tool", "tool_name": "get_monthly_summary", "content": '{"remaining": "450.00"}'}


def test_parses_text_reply():
    result = make_client(lambda _: reply({"content": "  You are doing great.  "})).chat("s", [], [])
    assert result.text == "You are doing great."
    assert result.tool_calls == ()


def test_parses_tool_calls_and_generates_missing_ids():
    raw = {"content": "", "tool_calls": [{"function": {"name": "get_expenses", "arguments": {"month": "2026-09"}}}]}
    result = make_client(lambda _: reply(raw)).chat("s", [], [TOOL])
    (call,) = result.tool_calls
    assert call.name == "get_expenses"
    assert call.arguments == {"month": "2026-09"}
    assert call.id  # generated because Ollama did not supply one


def test_arguments_supplied_as_json_string_are_parsed():
    raw = {"tool_calls": [{"id": "abc", "function": {"name": "x", "arguments": '{"month": "2026-09"}'}}]}
    (call,) = make_client(lambda _: reply(raw)).chat("s", [], [TOOL]).tool_calls
    assert call.id == "abc"
    assert call.arguments == {"month": "2026-09"}


def test_leaked_reasoning_is_stripped():
    result = make_client(lambda _: reply({"content": "Let me think...\n</think>\n\nYou spent $50."})).chat("s", [], [])
    assert result.text == "You spent $50."


def test_http_error_becomes_llm_error():
    handler = lambda _: httpx.Response(404, json={"error": "model 'x' not found"})
    with pytest.raises(LLMError):
        make_client(handler).chat("s", [], [])


def test_connection_failure_becomes_llm_error():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(LLMError):
        make_client(handler).chat("s", [], [])


def test_timeout_becomes_llm_error():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(LLMError):
        make_client(handler).chat("s", [], [])


@pytest.mark.parametrize("response", [httpx.Response(200, text="not json"), httpx.Response(200, json={"oops": 1})])
def test_malformed_response_becomes_llm_error(response):
    with pytest.raises(LLMError):
        make_client(lambda _: response).chat("s", [], [])
