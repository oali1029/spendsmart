"""MCP layer tests.

The provider is pointed at an in-process MCPServer object (no network, no separate process), backed
by the same in-memory test database. The key idea is PARITY: MCP must return exactly what the
direct provider returns, so switching TOOL_PROVIDER never changes the coach's answers.
"""
import json

import pytest

from app.ai.mcp_tool_provider import McpToolProvider
from app.ai.tool_provider import DirectToolProvider, ToolProviderError
from app.ai.llm_factory import get_llm_client
from app.main import app
from app.mcp_server import create_mcp_server
from app.routers import chat as chat_router
from app.routers.chat import get_tool_provider
from app.tools.spendsmart_tools import TOOL_DEFINITIONS
from tests.fakes import FakeLLMClient, call_tool, say
from tests.test_tools import seed


@pytest.fixture
def mcp(session_factory):
    return McpToolProvider(create_mcp_server(session_factory))


# ---- tool discovery ---------------------------------------------------------------------------------

def test_mcp_advertises_the_same_tools_as_the_direct_provider(mcp):
    advertised = {t.name: t for t in mcp.list_tools()}
    expected = {t.name: t for t in TOOL_DEFINITIONS}

    assert advertised.keys() == expected.keys()  # exactly two tools, nothing extra
    for name, tool in expected.items():
        remote = advertised[name]
        assert remote.description == tool.description
        assert remote.parameters["required"] == tool.parameters["required"]
        # Same argument names and types; guards against the server's signatures drifting.
        assert {k: v["type"] for k, v in remote.parameters["properties"].items()} == {
            k: v["type"] for k, v in tool.parameters["properties"].items()
        }
        for prop, spec in tool.parameters["properties"].items():
            assert remote.parameters["properties"][prop]["description"] == spec["description"]


# ---- parity of results ------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("get_monthly_summary", {"month": "2026-09"}),
        ("get_monthly_summary", {"month": "2026-01"}),  # empty month, no budget
        ("get_expenses", {"month": "2026-09"}),
        ("get_expenses", {"month": "2026-09", "category": "food"}),
    ],
)
def test_mcp_and_direct_return_identical_data(client, db, mcp, tool, arguments):
    seed(client)
    direct = DirectToolProvider(db).call_tool(tool, arguments)
    via_mcp = mcp.call_tool(tool, arguments)

    assert via_mcp.is_error is False
    assert json.loads(via_mcp.content) == json.loads(direct.content)


def test_mcp_returns_real_database_numbers(client, mcp):
    seed(client)
    data = json.loads(mcp.call_tool("get_monthly_summary", {"month": "2026-09"}).content)
    assert (data["budget"], data["total_spent"], data["remaining"]) == ("500.00", "150.00", "350.00")


# ---- errors -----------------------------------------------------------------------------------------

def test_bad_input_is_an_error_result_the_model_can_read(mcp):
    result = mcp.call_tool("get_monthly_summary", {"month": "September"})
    assert result.is_error is True
    assert "YYYY-MM" in json.loads(result.content)["error"]


def test_unknown_category_error_lists_valid_names(client, mcp):
    seed(client)
    result = mcp.call_tool("get_expenses", {"month": "2026-09", "category": "Gaming"})
    assert result.is_error is True
    assert "Food" in result.content


def test_unknown_tool_is_rejected_and_nothing_else_is_reachable(mcp):
    result = mcp.call_tool("run_sql", {"query": "SELECT * FROM expenses"})
    assert result.is_error is True


def test_unexpected_server_failure_does_not_leak_internals(client, mcp, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret-connection-string")

    monkeypatch.setattr("app.tools.spendsmart_tools.SummaryService.get_summary", boom)
    result = mcp.call_tool("get_monthly_summary", {"month": "2026-09"})
    assert result.is_error is True
    assert "secret-connection-string" not in result.content


def test_unreachable_mcp_server(caplog):
    dead = McpToolProvider("http://127.0.0.1:9/mcp", timeout=3)  # nothing listens on port 9

    # No tools available -> fail fast (mapped to HTTP 503) instead of wasting a slow LLM call.
    with pytest.raises(ToolProviderError):
        dead.list_tools()

    # Mid-chat failure -> an error result (never an exception), so the model can answer gracefully.
    result = dead.call_tool("get_monthly_summary", {"month": "2026-09"})
    assert result.is_error is True


# ---- configuration switch ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("setting", "expected"), [("direct", DirectToolProvider), ("mcp", McpToolProvider)]
)
def test_tool_provider_is_chosen_by_configuration(db, monkeypatch, setting, expected):
    from app.core.config import get_settings

    monkeypatch.setattr(
        chat_router, "get_settings", lambda: get_settings().model_copy(update={"tool_provider": setting})
    )
    assert isinstance(get_tool_provider(db), expected)


def test_unknown_tool_provider_setting_is_rejected(db, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(
        chat_router, "get_settings", lambda: get_settings().model_copy(update={"tool_provider": "carrier-pigeon"})
    )
    with pytest.raises(ValueError, match="TOOL_PROVIDER"):
        get_tool_provider(db)


# ---- ChatService is unchanged: same /chat contract over MCP ---------------------------------------------

def test_chat_over_mcp_matches_the_direct_flow(client, mcp):
    seed(client)
    fake = FakeLLMClient([call_tool("get_monthly_summary", month="2026-09"), say("You have 350 left.")])
    app.dependency_overrides[get_llm_client] = lambda: fake
    app.dependency_overrides[get_tool_provider] = lambda: mcp

    response = client.post(
        "/api/v1/chat", json={"coach_id": "ronaldo", "message": "How am I doing this month?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"coach_id", "reply", "tools_used"}  # contract unchanged
    assert body["tools_used"] == ["get_monthly_summary"]
    assert body["reply"].endswith("SIUUU!")
    # The model received the real numbers, delivered through MCP.
    tool_message = fake.calls[1]["messages"][-1]
    assert json.loads(tool_message.content)["remaining"] == "350.00"


def test_chat_returns_503_when_the_mcp_server_is_down(client):
    fake = FakeLLMClient([say("never reached")])
    app.dependency_overrides[get_llm_client] = lambda: fake
    app.dependency_overrides[get_tool_provider] = lambda: McpToolProvider("http://127.0.0.1:9/mcp", timeout=3)

    response = client.post("/api/v1/chat", json={"coach_id": "messi", "message": "hi"})

    assert response.status_code == 503
    assert fake.calls == []  # failed fast: the slow model was never called
