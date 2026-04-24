from __future__ import annotations

import pytest
from langchain_core.documents import Document


@pytest.fixture
def sample_documents() -> list[Document]:
    """A small corpus of documents mirroring what the real retriever loads.

    Covers two sources (the PDF and the website) and two languages so tests can
    exercise the hybrid retrieval and language-analysis paths without touching
    the real vector store.
    """
    return [
        Document(
            page_content=(
                "In May 2023, Promtior was founded by Emiliano Chinelli "
                "to help organizations adopt generative AI."
            ),
            metadata={"source": "data/AI_Engineer.pdf", "page": 3},
        ),
        Document(
            page_content=(
                "Promtior offers five services: Process Optimization, "
                "Advanced Personalization, GenAI Product Delivery, "
                "GenAI Department as a Service, and GenAI Adoption Consulting."
            ),
            metadata={"source": "https://www.promtior.ai/service"},
        ),
        Document(
            page_content=(
                "En Promtior trabajamos con empresas de LATAM para acelerar "
                "su adopción de IA generativa."
            ),
            metadata={"source": "https://www.promtior.ai/about"},
        ),
    ]