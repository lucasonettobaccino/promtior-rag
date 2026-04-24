"""Main RAG chain: retrieve, build prompt, generate, parse."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from promtior_rag.api.schemas import ChatOutput
from promtior_rag.chain.language import analyze_question
from promtior_rag.chain.prompts import build_rag_prompt
from promtior_rag.config import settings
from promtior_rag.logging_config import get_logger
from promtior_rag.retrieval.hybrid import build_hybrid_retriever
from promtior_rag.retrieval.reranker import wrap_with_reranker

log = get_logger(__name__)


def _format_docs(docs: list[Document]) -> str:
    """Format retrieved documents into a single context string for the prompt."""
    blocks = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        blocks.append(f"[source: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(blocks)


def build_rag_chain(retriever: BaseRetriever | None = None) -> Runnable:
    """Build the end-to-end RAG chain as an LCEL pipeline.

    Steps:
      1. Extract the question from the LangServe input dict.
      2. Analyze language: detect + translate to English for retrieval.
      3. Retrieve with the English-translated query, format context.
      4. Pass original question + detected language + context to the prompt.
      5. Call the LLM, parse to string, wrap in the ChatOutput schema.
    """
    log.info("rag_chain.build", llm_model=settings.llm_model)

    base_retriever = retriever if retriever is not None else wrap_with_reranker(
        build_hybrid_retriever()
    )

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.openai_api_key.get_secret_value(),
    )

    prompt = build_rag_prompt()

    question_extractor = RunnableLambda(
        lambda x: x["question"] if isinstance(x, dict) else x
    )

    # Enrich the question with language + translation info, then fan out:
    # - use the translated query for retrieval (better corpus coverage)
    # - preserve the original question for the final prompt
    # - pass the detected language so the model responds in it
    enrich_with_analysis = RunnableLambda(
        lambda question: {
            "question": question,
            "analysis": analyze_question(question),
        }
    )

    return (
        question_extractor
        | enrich_with_analysis
        | {
            "context": (
                RunnableLambda(lambda x: x["analysis"]["translated_query"])
                | base_retriever
                | RunnableLambda(_format_docs)
            ),
            "question": RunnableLambda(lambda x: x["question"]),
            "language": RunnableLambda(lambda x: x["analysis"]["language"]),
        }
        | prompt
        | llm
        | StrOutputParser()
        | RunnableLambda(lambda answer: ChatOutput(answer=answer))
    )
