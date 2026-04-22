"""Hybrid retriever combining BM25 (lexical) and FAISS (semantic) results."""

from __future__ import annotations

from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.retrievers import BaseRetriever

from promtior_rag.config import settings
from promtior_rag.logging_config import get_logger
from promtior_rag.retrieval.vector_store import load_bm25_retriever, load_faiss_retriever

log = get_logger(__name__)


def build_hybrid_retriever(
    top_k: int | None = None,
    semantic_weight: float | None = None,
) -> BaseRetriever:
    """Build an ensemble retriever merging BM25 and FAISS results."""
    k = top_k if top_k is not None else settings.retriever_top_k
    semantic = semantic_weight if semantic_weight is not None else settings.retriever_semantic_weight
    lexical = 1.0 - semantic

    log.info(
        "hybrid_retriever.build",
        top_k=k,
        semantic_weight=semantic,
        lexical_weight=lexical,
    )

    bm25 = load_bm25_retriever(top_k=k)
    faiss = load_faiss_retriever(top_k=k)

    return EnsembleRetriever(
        retrievers=[bm25, faiss],
        weights=[lexical, semantic],
    )