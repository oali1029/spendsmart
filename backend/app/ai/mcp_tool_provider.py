"""ToolProvider that runs tools through an MCP server instead of in-process.

This is the "MCP client" side. ChatService is unaware of it: same interface as DirectToolProvider.
"""
import asyncio
import json
import logging
from typing import Any

from mcp import Client
from mcp.server.mcpserver import MCPServer

from app.ai.tool_provider import ToolProvider, ToolProviderError
from app.ai.types import ToolDefinition, ToolResult

logger = logging.getLogger(__name__)


class McpToolProvider(ToolProvider):
    def __init__(self, target: "str | MCPServer", timeout: float = 30.0):
        # `target` is the MCP server's URL in real use. Tests pass an MCPServer object instead,
        # which the SDK connects to in-process, so tests need no network.
        self.target = target
        self.timeout = timeout

    def list_tools(self) -> list[ToolDefinition]:
        # The tool list comes FROM THE SERVER (tools/list), not from a local copy. That is the
        # point of MCP: the client discovers what is available.
        try:
            listing = self._run(lambda client: client.list_tools())
        except Exception as exc:
            # Fail before spending a slow model call on a request that cannot use its tools.
            logger.error("MCP server unreachable while listing tools: %r", exc)
            raise ToolProviderError("The financial data service (MCP server) is unavailable") from exc
        return [
            ToolDefinition(name=t.name, description=t.description or "", parameters=t.input_schema)
            for t in listing.tools
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        logger.info("Calling tool via MCP client: %s(%s)", name, arguments)
        try:
            result = self._run(lambda client: client.call_tool(name, arguments))
        except Exception as exc:
            # Backend failed mid-chat: report it to the model as a tool error so it can answer
            # gracefully, matching how DirectToolProvider treats tool failures.
            logger.error("MCP call to %s failed: %r", name, exc)
            return _error("The financial data service is unavailable. Tell the user you could not retrieve the data.")

        text = "\n".join(part.text for part in result.content if getattr(part, "type", "") == "text")
        if result.is_error:
            # MCP delivers error text; wrap it in the same JSON shape DirectToolProvider uses.
            return _error(text)
        return ToolResult(content=text)

    def _run(self, operation):
        # ChatService is synchronous but the MCP SDK is async, so bridge with asyncio.run: one
        # short-lived MCP session per operation. Simple, and negligible next to a multi-second
        # LLM call. (Requires no event loop already running in this thread; FastAPI runs sync
        # endpoints in worker threads, so that holds. An `async def` endpoint would need changes.)
        async def go():
            async with Client(self.target, read_timeout_seconds=self.timeout) as client:
                return await operation(client)

        return asyncio.run(go())


def _error(message: str) -> ToolResult:
    return ToolResult(content=json.dumps({"error": message}), is_error=True)
