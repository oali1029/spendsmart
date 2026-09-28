"""Application entry point: builds the FastAPI app and wires everything together."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.llm_client import LLMError
from app.ai.tool_provider import ToolProviderError
from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.routers import budgets, categories, chat, expenses, health, summary

# Show INFO logs from our own code (e.g. which tools the coach called) in the server console.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="SpendSmart API")

# CORS: the React dev server runs on a different origin (localhost:5173), so the browser
# blocks its calls to this API unless we explicitly allow that origin.
# The allowed origins come from config, so production can use a different value.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Services raise domain exceptions (which know nothing about HTTP);
# these handlers are the single place they are translated into HTTP responses.
@app.exception_handler(NotFoundError)
def not_found_handler(_: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def conflict_handler(_: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(LLMError)
def llm_error_handler(_: Request, exc: LLMError):
    # 502: our app is fine, the upstream model service failed. The real cause goes to the log;
    # the client gets a generic message (no internal URLs or provider details leaked).
    logger.error("LLM failure: %s", exc)
    return JSONResponse(status_code=502, content={"detail": "The AI coach is currently unavailable."})


@app.exception_handler(ToolProviderError)
def tool_provider_error_handler(_: Request, exc: ToolProviderError):
    # 503: a backing service (the MCP server) is down; the request can be retried later.
    logger.error("Tool backend failure: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "The financial data service is currently unavailable."})


# All endpoints live under /api/v1 so the API can be versioned later without breaking clients.
app.include_router(health.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")
app.include_router(summary.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
