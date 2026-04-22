"""Loaders for persisted retrieval indices (FAISS + BM25)."""

from __future__ import annotations

import pickle
from pathlib import Path

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings

from promtior_rag.config import settings
from promtior_rag.ingestion.pipeline import BM25_FILENAME
from promtior_rag.logging_config import get_logger

log = get_logger(__name__)


def load_faiss_retriever(top_k: int | None = None) -> BaseRetriever:
    """Load the persisted FAISS vector store and return it as a retriever."""
    k = top_k if top_k is not None else settings.retriever_top_k
    path = settings.vector_store_path

    log.info("faiss.load.start", path=str(path), top_k=k)

    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key.get_secret_value(),
    )
    store = FAISS.load_local(
        str(path),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    log.info("faiss.load.completed", num_vectors=store.index.ntotal)
    return store.as_retriever(search_kwargs={"k": k})


def load_bm25_retriever(top_k: int | None = None) -> BM25Retriever:
    """Load the persisted BM25 retriever from disk."""
    k = top_k if top_k is not None else settings.retriever_top_k
    path = settings.vector_store_path / BM25_FILENAME

    log.info("bm25.load.start", path=str(path), top_k=k)

    with path.open("rb") as f:
        retriever: BM25Retriever = pickle.load(f)
    retriever.k = k

    log.info("bm25.load.completed")
    return retriever