"""The financial tools the AI coach may call. This is the ONLY data the model can reach.

Think of it as a second "presentation layer" next to the HTTP routers:
    tool function -> existing Service -> Repository -> Model
The model never gets SQL, a database session or any other way in; it can only ask for these
named, read-only, argument-validated functions.

Design rules for tool output:
- Deterministic application data only. The LLM interprets and phrases it; it never computes it.
- Everything the answer might need is PRECOMPUTED (remaining, percentages, over-limit flags),
  because language models are unreliable at arithmetic, especially small local ones.
- Money is a fixed 2-decimal string ("50.00"), so it is quoted exactly as stored.

These plain functions are the single source of truth: DirectToolProvider calls them directly,
and the MCP server (app/mcp_server.py) calls the very same code through `execute_tool`.
"""
import json
import logging
import re
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.ai.types import ToolDefinition, ToolResult
from app.services.category_service import CategoryService
from app.services.expense_service import ExpenseService
from app.services.summary_service import SummaryService

logger = logging.getLogger(__name__)

# Bound how much data one tool call can put into the model's context.
MAX_EXPENSES = 50

_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_CENTS = Decimal("0.01")


class ToolError(Exception):
    """Bad tool input. The message is shown to the model so it can correct itself and retry."""


def _money(value: Decimal) -> str:
    return str(value.quantize(_CENTS))


def _percent(part: Decimal, whole: Decimal | None) -> float | None:
    if whole is None or whole == 0:
        return None
    return round(float(part / whole * 100), 1)


def _check_month(month: Any) -> None:
    if not isinstance(month, str) or not _MONTH_PATTERN.match(month):
        raise ToolError("month must be a string in YYYY-MM format, for example 2026-09")


def get_monthly_summary(db: Session, month: str) -> dict:
    _check_month(month)
    summary = SummaryService(db).get_summary(month)

    result: dict[str, Any] = {
        "month": summary.month,
        "budget": _money(summary.budget) if summary.budget is not None else None,
        "total_spent": _money(summary.total_spent),
        "remaining": _money(summary.remaining) if summary.remaining is not None else None,
        "budget_used_percent": _percent(summary.total_spent, summary.budget),
        "over_budget": summary.remaining is not None and summary.remaining < 0,
        "categories": [
            {
                "name": item.name,
                "spent": _money(item.spent),
                "monthly_limit": _money(item.monthly_limit) if item.monthly_limit is not None else None,
                "limit_used_percent": _percent(item.spent, item.monthly_limit),
                "over_limit": item.monthly_limit is not None and item.spent > item.monthly_limit,
            }
            for item in summary.categories
        ],
    }
    if summary.budget is None:
        # An explicit note stops a model from inventing a budget when the field is null.
        result["note"] = f"No budget has been set for {summary.month}."
    return result


def get_expenses(db: Session, month: str, category: str | None = None) -> dict:
    _check_month(month)
    if category is not None and not isinstance(category, str):
        raise ToolError("category must be a category name (string)")

    categories = CategoryService(db).list_categories()
    names = {c.id: c.name for c in categories}

    category_id = None
    category_name = None
    if category:  # None and "" both mean "all categories"
        match = next((c for c in categories if c.name.casefold() == category.strip().casefold()), None)
        if match is None:
            # List the valid names so the model can retry with a real one instead of guessing.
            valid = ", ".join(names.values()) or "(no categories exist yet)"
            raise ToolError(f"Unknown category '{category}'. Valid categories: {valid}")
        category_id, category_name = match.id, match.name

    expenses = ExpenseService(db).list_expenses(month, category_id)
    return {
        "month": month,
        "category": category_name,
        "count": len(expenses),
        # The total covers ALL matching expenses, even when the list below is truncated.
        "total": _money(sum((e.amount for e in expenses), Decimal("0"))),
        "truncated": len(expenses) > MAX_EXPENSES,
        "expenses": [
            {
                "date": e.expense_date.isoformat(),
                "amount": _money(e.amount),
                "category": names[e.category_id],
                "description": e.description,
            }
            for e in expenses[:MAX_EXPENSES]
        ],
    }


# Descriptions matter: they are how the model decides WHEN to call each tool. They are defined
# once here and reused by the MCP server, so both providers show the model identical wording.
MONTH_DESCRIPTION = "The month as YYYY-MM, for example 2026-09. Work out 'this month' from today's date."
CATEGORY_DESCRIPTION = "Optional category name to filter by, e.g. Food. Omit for all categories."

_MONTH_PROPERTY = {"type": "string", "description": MONTH_DESCRIPTION}

TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="get_monthly_summary",
        description=(
            "Get the user's overall budget, total spending, remaining budget and per-category "
            "spending with category limits for one month. Use this for questions like "
            "'how am I doing', 'how much have I spent' or 'am I over budget'."
        ),
        parameters={
            "type": "object",
            "properties": {"month": _MONTH_PROPERTY},
            "required": ["month"],
        },
    ),
    ToolDefinition(
        name="get_expenses",
        description=(
            "List the user's individual expenses for one month, optionally for a single "
            "category. Use this when the user asks what they bought or wants specific expenses."
        ),
        parameters={
            "type": "object",
            "properties": {
                "month": _MONTH_PROPERTY,
                "category": {"type": "string", "description": CATEGORY_DESCRIPTION},
            },
            "required": ["month"],
        },
    ),
)

# Allow-list dispatch: only these names are callable. Anything else is rejected, never executed.
_TOOL_FUNCTIONS: dict[str, Callable[..., dict]] = {
    "get_monthly_summary": get_monthly_summary,
    "get_expenses": get_expenses,
}


def run_tool(db: Session, name: str, arguments: dict[str, Any]) -> dict:
    """Validate the call against the tool's schema, then run it. Raises ToolError on bad input."""
    function = _TOOL_FUNCTIONS.get(name)
    if function is None:
        raise ToolError(f"Unknown tool '{name}'. Available tools: {', '.join(_TOOL_FUNCTIONS)}")

    schema = next(t.parameters for t in TOOL_DEFINITIONS if t.name == name)
    allowed = set(schema["properties"])
    missing = set(schema["required"]) - set(arguments)
    unexpected = set(arguments) - allowed
    if missing or unexpected:
        # Models sometimes send wrong or extra arguments; say exactly what was wrong.
        raise ToolError(
            f"Invalid arguments for {name}. Missing: {sorted(missing) or 'none'}. "
            f"Unexpected: {sorted(unexpected) or 'none'}. Allowed: {sorted(allowed)}."
        )
    return function(db, **arguments)


def execute_tool(db: Session, name: str, arguments: dict[str, Any]) -> ToolResult:
    """Run a tool and package the outcome for the model. Never raises.

    Shared by DirectToolProvider and the MCP server, so both behave identically: bad input
    becomes an error result the model can read and correct; unexpected failures become a
    generic error (details only in the server log, never shown to the model or user).
    """
    try:
        return ToolResult(content=json.dumps(run_tool(db, name, arguments), ensure_ascii=False))
    except ToolError as exc:
        return _error_result(str(exc))
    except Exception:
        logger.exception("Tool %s failed unexpectedly", name)
        return _error_result("The tool failed unexpectedly. Tell the user you could not retrieve the data.")


def _error_result(message: str) -> ToolResult:
    return ToolResult(content=json.dumps({"error": message}), is_error=True)
