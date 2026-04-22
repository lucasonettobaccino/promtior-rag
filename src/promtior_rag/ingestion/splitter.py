"""Text splitter for breaking documents into indexable chunks."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from promtior_rag.config import settings
from promtior_rag.logging_config import get_logger

log = get_logger(__name__)


def split_documents(
    documents: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """Split documents into overlapping chunks suitable for retrieval."""
    size = chunk_size if chunk_size is not None else settings.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    log.info(
        "splitter.start",
        num_documents=len(documents),
        chunk_size=size,
        chunk_overlap=overlap,
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
        add_start_index=True,
    )

    chunks = splitter.split_documents(documents)

    log.info(
        "splitter.completed",
        num_documents=len(documents),
        num_chunks=len(chunks),
        avg_chunk_chars=sum(len(c.page_content) for c in chunks) // max(len(chunks), 1),
    )
    return chunks