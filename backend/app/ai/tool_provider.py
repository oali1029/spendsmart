"""How ChatService discovers and runs tools, without knowing where they live.

ChatService talks only to ToolProvider. DirectToolProvider (below) calls the tool functions
in-process; McpToolProvider (mcp_tool_provider.py) runs the SAME tools through an MCP server.
ChatService cannot tell them apart, and the TOOL_PROVIDER setting chooses between them.
"""
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.ai.types import ToolDefinition, ToolResult
from app.tools.spendsmart_tools import TOOL_DEFINITIONS, execute_tool


class ToolProviderError(Exception):
    """The tool backend itself is unavailable (e.g. the MCP server is down). Mapped to HTTP 503."""


class ToolProvider(ABC):
    @abstractmethod
    def list_tools(self) -> list[ToolDefinition]:
        """The tools the model is allowed to call. Raises ToolProviderError if the backend is down."""

    @abstractmethod
    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Run one tool. Must NOT raise for bad input or backend failure: return an error
        ToolResult instead, so the model gets a chance to respond gracefully."""


class DirectToolProvider(ToolProvider):
    """Runs tools in-process, using the current request's database session."""

    def __init__(self, db: Session):
        self.db = db

    def list_tools(self) -> list[ToolDefinition]:
        return list(TOOL_DEFINITIONS)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        try:
            return execute_tool(self.db, name, arguments)
        finally:
            # Tools only read. Ending the read transaction hands the DB connection back to the pool
            # instead of holding it "idle in transaction" while the (slow) LLM thinks.
            self.db.rollback()
