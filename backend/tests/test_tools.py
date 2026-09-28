import json
from decimal import Decimal

import pytest

from app.ai.tool_provider import DirectToolProvider
from app.tools.spendsmart_tools import (
    MAX_EXPENSES,
    ToolError,
    get_expenses,
    get_monthly_summary,
    run_tool,
)


def seed(client):
    """Budget 500. Food (limit 100) spent 110 -> over its limit. Travel (no limit) spent 40."""
    food = client.post("/api/v1/categories", json={"name": "Food", "monthly_limit": 100}).json()["id"]
    travel = client.post("/api/v1/categories", json={"name": "Travel"}).json()["id"]
    for category, amount, day, description in [
        (food, 60, "2026-09-05", "Lunch"),
        (food, 50, "2026-09-10", "Dinner"),
        (travel, 40, "2026-09-12", "Train"),
        (food, 999, "2026-08-31", "Wrong month"),
    ]:
        client.post(
            "/api/v1/expenses",
            json={"amount": amount, "expense_date": day, "category_id": category, "description": description},
        )
    client.put("/api/v1/budgets/2026-09", json={"amount": 500})


# ---- get_monthly_summary ----------------------------------------------------------------------

def test_summary_returns_precomputed_values(client, db):
    seed(client)
    result = get_monthly_summary(db, "2026-09")

    assert result["budget"] == "500.00"
    assert result["total_spent"] == "150.00"
    assert result["remaining"] == "350.00"
    assert result["budget_used_percent"] == 30.0
    assert result["over_budget"] is False

    food = next(c for c in result["categories"] if c["name"] == "Food")
    assert food["spent"] == "110.00"
    assert food["monthly_limit"] == "100.00"
    assert food["limit_used_percent"] == 110.0
    assert food["over_limit"] is True

    travel = next(c for c in result["categories"] if c["name"] == "Travel")
    assert travel["monthly_limit"] is None
    assert travel["limit_used_percent"] is None
    assert travel["over_limit"] is False


def test_summary_without_budget_says_so_explicitly(client, db):
    result = get_monthly_summary(db, "2026-09")
    assert result["budget"] is None
    assert result["remaining"] is None
    assert "No budget has been set" in result["note"]


def test_summary_flags_overspent_budget(client, db):
    seed(client)
    client.put("/api/v1/budgets/2026-09", json={"amount": 100})
    result = get_monthly_summary(db, "2026-09")
    assert result["remaining"] == "-50.00"
    assert result["over_budget"] is True


@pytest.mark.parametrize("month", ["2026-13", "2026-9", "September", "", None, 202609])
def test_summary_rejects_bad_month(db, month):
    with pytest.raises(ToolError, match="YYYY-MM"):
        get_monthly_summary(db, month)


# ---- get_expenses -----------------------------------------------------------------------------

def test_expenses_for_month(client, db):
    seed(client)
    result = get_expenses(db, "2026-09")
    assert result["count"] == 3
    assert result["total"] == "150.00"
    assert result["truncated"] is False
    # newest first; the August expense is excluded
    assert [e["description"] for e in result["expenses"]] == ["Train", "Dinner", "Lunch"]
    assert result["expenses"][0] == {
        "date": "2026-09-12", "amount": "40.00", "category": "Travel", "description": "Train",
    }


def test_expenses_category_filter_is_case_insensitive(client, db):
    seed(client)
    result = get_expenses(db, "2026-09", "  food ")
    assert result["category"] == "Food"
    assert result["count"] == 2
    assert result["total"] == "110.00"


def test_expenses_empty_category_means_all(client, db):
    seed(client)
    assert get_expenses(db, "2026-09", "")["count"] == 3


def test_unknown_category_lists_valid_names(client, db):
    seed(client)
    with pytest.raises(ToolError) as error:
        get_expenses(db, "2026-09", "Gaming")
    assert "Food" in str(error.value) and "Travel" in str(error.value)


def test_expenses_are_truncated_but_total_covers_everything(client, db):
    category = client.post("/api/v1/categories", json={"name": "Misc"}).json()["id"]
    for _ in range(MAX_EXPENSES + 5):
        client.post(
            "/api/v1/expenses",
            json={"amount": 1, "expense_date": "2026-09-01", "category_id": category},
        )
    result = get_expenses(db, "2026-09")
    assert result["count"] == MAX_EXPENSES + 5
    assert len(result["expenses"]) == MAX_EXPENSES
    assert result["truncated"] is True
    assert Decimal(result["total"]) == MAX_EXPENSES + 5


# ---- run_tool: the allow-list and argument validation ------------------------------------------

def test_unknown_tool_is_rejected(db):
    with pytest.raises(ToolError, match="Unknown tool"):
        run_tool(db, "drop_all_tables", {})


def test_missing_and_unexpected_arguments_are_rejected(db):
    with pytest.raises(ToolError, match="Missing"):
        run_tool(db, "get_monthly_summary", {})
    with pytest.raises(ToolError, match="Unexpected"):
        run_tool(db, "get_monthly_summary", {"month": "2026-09", "sql": "SELECT 1"})


# ---- DirectToolProvider -------------------------------------------------------------------------

def test_provider_exposes_exactly_two_tools(db):
    names = {tool.name for tool in DirectToolProvider(db).list_tools()}
    assert names == {"get_monthly_summary", "get_expenses"}


def test_provider_returns_json_for_success(client, db):
    seed(client)
    result = DirectToolProvider(db).call_tool("get_monthly_summary", {"month": "2026-09"})
    assert result.is_error is False
    assert json.loads(result.content)["remaining"] == "350.00"


def test_provider_turns_bad_input_into_error_result_not_exception(db):
    provider = DirectToolProvider(db)
    for name, args in [
        ("get_monthly_summary", {"month": "nope"}),
        ("get_monthly_summary", {}),
        ("no_such_tool", {}),
    ]:
        result = provider.call_tool(name, args)
        assert result.is_error is True
        assert "error" in json.loads(result.content)


def test_provider_survives_unexpected_tool_failure(db, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("database exploded: secret-connection-string")

    monkeypatch.setattr("app.tools.spendsmart_tools.SummaryService.get_summary", boom)
    result = DirectToolProvider(db).call_tool("get_monthly_summary", {"month": "2026-09"})
    assert result.is_error is True
    # The internal error text must not be forwarded to the model (or user).
    assert "secret-connection-string" not in result.content
