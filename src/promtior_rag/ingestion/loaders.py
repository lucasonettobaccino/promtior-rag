"""Document loaders for web and PDF sources."""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.sitemap import SitemapLoader
from langchain_core.documents import Document

from promtior_rag.logging_config import get_logger

log = get_logger(__name__)


DEFAULT_URL_EXCLUDE_PATTERNS: list[str] = [
    r"errorenelpago",
    r"graciasportucompra",
    r"politica-de-privacidad",
    r"download-white-paper",
    r"webinar-registration",
    r"sorteo",
    r"/blog/categories/",
]

MIN_PAGE_CHARS = 50


def _parse_page(content: BeautifulSoup) -> str:
    """Extract clean text from a page, stripping non-content tags."""
    for tag in content(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = content.get_text(separator="\n", strip=True)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _should_exclude(url: str, patterns: list[re.Pattern[str]]) -> bool:
    """Check if a URL matches any of the exclusion patterns."""
    return any(pattern.search(url) for pattern in patterns)


def load_web_documents(
    sitemap_url: str,
    exclude_patterns: list[str] | None = None,
) -> list[Document]:
    """Load all pages declared in a sitemap, filtering out noise URLs."""
    raw_patterns = exclude_patterns if exclude_patterns is not None else DEFAULT_URL_EXCLUDE_PATTERNS
    patterns = [re.compile(p, flags=re.IGNORECASE) for p in raw_patterns]

    log.info("web_loader.start", sitemap_url=sitemap_url, exclude_count=len(patterns))

    loader = SitemapLoader(
        web_path=sitemap_url,
        parsing_function=_parse_page,
        continue_on_failure=True,
    )
    loader.requests_per_second = 2

    raw_documents = loader.load()

    seen_urls: set[str] = set()
    documents: list[Document] = []
    for doc in raw_documents:
        url = doc.metadata.get("source", "")
        if url in seen_urls:
            continue
        if _should_exclude(url, patterns):
            continue
        if len(doc.page_content.strip()) <= MIN_PAGE_CHARS:
            continue

        doc.metadata["document_type"] = "web"
        seen_urls.add(url)
        documents.append(doc)

    log.info(
        "web_loader.completed",
        sitemap_url=sitemap_url,
        num_raw=len(raw_documents),
        num_documents=len(documents),
        num_filtered=len(raw_documents) - len(documents),
        total_chars=sum(len(d.page_content) for d in documents),
    )
    return documents


def load_pdf_documents(pdf_path: Path) -> list[Document]:
    """Load a PDF and return one Document per page."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    log.info("pdf_loader.start", path=str(pdf_path))

    loader = PyPDFLoader(str(pdf_path))
    raw_documents = loader.load()

    documents: list[Document] = []
    for doc in raw_documents:
        if not doc.page_content.strip():
            continue
        doc.metadata["file_name"] = pdf_path.name
        doc.metadata["document_type"] = "pdf"
        documents.append(doc)

    log.info(
        "pdf_loader.completed",
        path=str(pdf_path),
        num_pages=len(documents),
        total_chars=sum(len(d.page_content) for d in documents),
    )
    return documents