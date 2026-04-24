from __future__ import annotations

from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document


def _build_in_memory_retriever(docs: list[Document]) -> EnsembleRetriever:
    """Replica of build_hybrid_retriever but without FAISS (to avoid embeddings).

    Uses BM25 twice with different weights to exercise the ensemble wiring
    without incurring network calls for embeddings.
    """
    bm25_a = BM25Retriever.from_documents(docs)
    bm25_a.k = 3
    bm25_b = BM25Retriever.from_documents(docs)
    bm25_b.k = 3
    return EnsembleRetriever(retrievers=[bm25_a, bm25_b], weights=[0.4, 0.6])


def test_retriever_returns_documents(sample_documents: list[Document]) -> None:
    """The retriever should return a non-empty list for a relevant query."""
    retriever = _build_in_memory_retriever(sample_documents)

    results = retriever.invoke("When was Promtior founded?")

    assert len(results) > 0
    assert all(isinstance(doc, Document) for doc in results)


def test_retriever_preserves_source_metadata(
    sample_documents: list[Document],
) -> None:
    """Retrieved docs must carry the source metadata used by the prompt's citations."""
    retriever = _build_in_memory_retriever(sample_documents)

    results = retriever.invoke("services Promtior")

    assert all("source" in doc.metadata for doc in results)
    sources = {doc.metadata["source"] for doc in results}
    assert any("promtior.ai" in s or "AI_Engineer" in s for s in sources)


def test_retriever_ranks_relevant_doc_first(
    sample_documents: list[Document],
) -> None:
    """A keyword-heavy query should rank the obviously relevant chunk highest."""
    retriever = _build_in_memory_retriever(sample_documents)

    results = retriever.invoke("founded May 2023")

    assert "founded" in results[0].page_content.lower()