from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_MESSAGE_CHARS = 1000
# Hard cap on what a client may send. The service trims further to the most recent messages.
MAX_HISTORY_SENT = 50


class ChatTurn(BaseModel):
    """One earlier message, supplied by the client (the server keeps no conversation state)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Only user/assistant: a client can't inject "system" instructions or fake tool results.
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # The client picks a coach by id; it never sends prompt text, so it can't tamper with the
    # system prompt.
    coach_id: str
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORY_SENT)


class ChatResponse(BaseModel):
    coach_id: str
    reply: str
    # Names of the tools run to produce this answer (useful for the UI and for debugging).
    tools_used: list[str]


class CoachRead(BaseModel):
    """Public coach info. The style prompt is deliberately not exposed."""

    id: str
    display_name: str
    tagline: str
