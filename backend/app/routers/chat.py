"""Router layer for the AI coach. HTTP only."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.llm_client import LLMClient
from app.ai.llm_factory import get_llm_client
from app.ai.mcp_tool_provider import McpToolProvider
from app.ai.tool_provider import DirectToolProvider, ToolProvider
from app.coaches.personas import list_coaches as registered_coaches
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, CoachRead
from app.services.chat_service import ChatService

router = APIRouter(tags=["coach"])


def get_tool_provider(db: Session = Depends(get_db)) -> ToolProvider:
    # TOOL_PROVIDER=direct|mcp picks how the model's tool calls are executed. ChatService is
    # identical either way. (In "mcp" mode the request's db session goes unused: it is opened
    # lazily, so this costs nothing.)
    settings = get_settings()
    if settings.tool_provider == "direct":
        return DirectToolProvider(db)
    if settings.tool_provider == "mcp":
        return McpToolProvider(settings.mcp_server_url, timeout=settings.mcp_timeout_seconds)
    raise ValueError(f"Unsupported TOOL_PROVIDER: {settings.tool_provider!r} (use 'direct' or 'mcp')")


def get_chat_service(
    llm: LLMClient = Depends(get_llm_client), tools: ToolProvider = Depends(get_tool_provider)
) -> ChatService:
    # The single wiring point for the AI pieces: which LLM, which tool provider.
    # Tests override get_llm_client with a fake LLM and can override get_tool_provider.
    settings = get_settings()
    return ChatService(
        llm=llm,
        tools=tools,
        max_tool_rounds=settings.chat_max_tool_rounds,
        currency_symbol=settings.currency_symbol,
    )


# Coaches are static configuration (no database, no business rules), so the router reads the
# registry directly rather than going through a service.
@router.get("/coaches", response_model=list[CoachRead])
def list_coaches():
    return registered_coaches()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, service: ChatService = Depends(get_chat_service)):
    return service.chat(request)
