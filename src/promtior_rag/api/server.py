"""LangServe + FastAPI application exposing the RAG chain over HTTP."""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langserve import add_routes

from promtior_rag.api.schemas import ChatInput, ChatOutput
from promtior_rag.chain.rag_chain import build_rag_chain
from promtior_rag.config import settings
from promtior_rag.logging_config import configure_logging, get_logger

log = get_logger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def _configure_langsmith() -> None:
    """Export LangSmith settings to the environment so the SDK picks them up.

    LangSmith's SDK reads from os.environ, not from our Settings object.
    Without this, tracing would only work in ECS (which sets the env vars
    directly in the task definition) but not locally with a .env file.
    """
    if not settings.langsmith_tracing or settings.langsmith_api_key is None:
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize resources on startup, clean up on shutdown."""
    configure_logging()
    _configure_langsmith()
    log.info(
        "server.startup",
        host=settings.server_host,
        port=settings.server_port,
        env=settings.app_env,
    )
    yield
    log.info("server.shutdown")


def create_app() -> FastAPI:
    """Build the FastAPI app with CORS, health check, and chain routes."""
    app = FastAPI(
        title="Promtior RAG API",
        description="Retrieval-augmented chatbot about Promtior.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    chain = build_rag_chain()

    typed_chain = chain.with_types(input_type=ChatInput, output_type=ChatOutput)

    add_routes(
        app,
        typed_chain,
        path="/chat",
        input_type=ChatInput,
        output_type=ChatOutput,
    )

    @app.get("/healthz", tags=["meta"])
    async def health_check() -> JSONResponse:
        """Liveness probe for the load balancer."""
        return JSONResponse({"status": "ok"})
    
    @app.get("/", include_in_schema=False)
    async def root() -> FileResponse:
        """Serve the chat landing page."""
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


app = create_app()


def main() -> None:
    """Entry point for `poetry run promtior-serve`."""
    import uvicorn

    uvicorn.run(
        "promtior_rag.api.server:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.app_env.value == "development",
    )


if __name__ == "__main__":
    main()