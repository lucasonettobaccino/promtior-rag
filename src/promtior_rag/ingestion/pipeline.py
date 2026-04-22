"""Orchestrator for the full ingestion pipeline: load, split, embed, persist."""

from __future__ import annotations

import pickle
from pathlib import Path

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from promtior_rag.config import settings
from promtior_rag.ingestion.loaders import load_pdf_documents, load_web_documents
from promtior_rag.ingestion.splitter import split_documents
from promtior_rag.logging_config import configure_logging, get_logger

log = get_logger(__name__)

BM25_FILENAME = "bm25.pkl"


def load_all_documents() -> list[Document]:
    """Load documents from all configured sources."""
    pdf_docs = load_pdf_documents(settings.promtior_pdf_path)
    web_docs = load_web_documents(settings.promtior_web_url)
    return pdf_docs + web_docs


def build_faiss_index(chunks: list[Document], output_path: Path) -> None:
    """Embed chunks and persist a FAISS vector store."""
    log.info("faiss.build.start", num_chunks=len(chunks), model=settings.embedding_model)

    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key.get_secret_value(),
    )
    vector_store = FAISS.from_documents(chunks, embeddings)

    output_path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(output_path))

    log.info("faiss.build.completed", output_path=str(output_path))


def build_bm25_index(chunks: list[Document], output_path: Path) -> None:
    """Serialize chunks for later BM25 retrieval."""
    log.info("bm25.build.start", num_chunks=len(chunks))

    retriever = BM25Retriever.from_documents(chunks)

    output_path.mkdir(parents=True, exist_ok=True)
    bm25_path = output_path / BM25_FILENAME
    with bm25_path.open("wb") as f:
        pickle.dump(retriever, f)

    log.info("bm25.build.completed", output_path=str(bm25_path))


def run() -> None:
    """Execute the full pipeline: load, split, index, persist."""
    log.info("pipeline.start")

    documents = load_all_documents()
    chunks = split_documents(documents)

    build_faiss_index(chunks, settings.vector_store_path)
    build_bm25_index(chunks, settings.vector_store_path)

    log.info(
        "pipeline.completed",
        num_documents=len(documents),
        num_chunks=len(chunks),
        vector_store_path=str(settings.vector_store_path),
    )


def main() -> None:
    """Entry point for `poetry run promtior-ingest`."""
    configure_logging()
    run()


if __name__ == "__main__":
    main()