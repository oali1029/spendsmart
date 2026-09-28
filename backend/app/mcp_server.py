"""The SpendSmart MCP server: exposes the financial tools over the Model Context Protocol.

Run it as its own process:   python -m app.mcp_server

It is a thin adapter. It contains no financial logic and no SQL: every tool call goes to the
same `execute_tool` used by the in-process provider, which calls the existing
Service -> Repository -> PostgreSQL code. The model only ever sees these two named tools.

Security note: there is no authentication, so it binds to 127.0.0.1 only (see MCP_HOST). It
must never be exposed publicly; on AWS it should be reachable only from the backend itself.
"""
import json
import logging
from collections.abc import Callable
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.tools.spendsmart_tools import (
    CATEGORY_DESCRIPTION,
    MONTH_DESCRIPTION,
    TOOL_DEFINITIONS,
    execute_tool,
)

logger = logging.getLogger("spendsmart.mcp_server")


def create_mcp_server(session_factory: Callable[[], Session] = SessionLocal) -> MCPServer:
    """Build the server. `session_factory` is injectable so tests can use their own database."""
    server = MCPServer("spendsmart")
    definitions = {tool.name: tool for tool in TOOL_DEFINITIONS}

    def run(name: str, arguments: dict) -> str:
        # Unlike the in-process provider (which reuses the request's session), this server is its
        # own process, so each tool call opens and closes its own short-lived session.
        logger.info("MCP tool call handled by MCP server: %s(%s)", name, arguments)
        with session_factory() as db:
            result = execute_tool(db, name, arguments)
        if result.is_error:
            # Raising the SDK's ToolError makes MCP mark the response isError=true, so the client
            # can tell a failed call from real data.
            raise ToolError(json.loads(result.content)["error"])
        return result.content

    # The function signatures below define the schema MCP advertises to clients. Descriptions
    # are imported from the tools module (single source), and a test checks nothing drifts.
    def get_monthly_summary(month: Annotated[str, Field(description=MONTH_DESCRIPTION)]) -> str:
        return run("get_monthly_summary", {"month": month})

    def get_expenses(
        month: Annotated[str, Field(description=MONTH_DESCRIPTION)],
        # A plain string defaulting to "" (meaning "all categories") instead of `str | None`:
        # Optional types produce an `anyOf` schema that small local models handle less reliably.
        category: Annotated[str, Field(description=CATEGORY_DESCRIPTION)] = "",
    ) -> str:
        return run("get_expenses", {"month": month, "category": category})

    for function in (get_monthly_summary, get_expenses):
        definition = definitions[function.__name__]
        # structured_output=False: return the tool's JSON as plain text, exactly like the
        # in-process provider does, so the model sees identical content either way.
        server.add_tool(function, name=definition.name, description=definition.description, structured_output=False)
    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    logger.info("Starting SpendSmart MCP server on http://%s:%s/mcp", settings.mcp_host, settings.mcp_port)
    create_mcp_server().run("streamable-http", host=settings.mcp_host, port=settings.mcp_port)


if __name__ == "__main__":
    main()
