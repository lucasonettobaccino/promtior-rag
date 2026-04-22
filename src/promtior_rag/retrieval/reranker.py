"""Cohere-based reranker that re-scores retrieved candidates by relevance."""

from __future__ import annotations

from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
from langchain_core.retrievers import BaseRetriever

from promtior_rag.config import settings
from promtior_rag.logging_config import get_logger

log = get_logger(__name__)


def wrap_with_reranker(
    base_retriever: BaseRetriever,
    top_n: int | None = None,
) -> BaseRetriever:
    """Wrap a base retriever with a Cohere reranker for final re-scoring."""
    n = top_n if top_n is not None else settings.rerank_top_n

    log.info(
        "reranker.build",
        model=settings.rerank_model,
        top_n=n,
    )

    compressor = CohereRerank(
        model=settings.rerank_model,
        cohere_api_key=settings.cohere_api_key.get_secret_value(),
        top_n=n,
    )

    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )