"""Language detection + query translation for multilingual retrieval.

Uses the LLM as a lightweight utility call to:
1. Detect the language of the user's question (robust for short/noisy input).
2. Translate non-English questions to English for retrieval (the corpus
   is predominantly English, so EN queries match better).

The LLM's original-language output for the FINAL answer is unaffected —
we pass the detected language to the main prompt, which instructs the
model to answer in the user's language.
"""

from __future__ import annotations

import json
from typing import TypedDict

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from promtior_rag.config import settings
from promtior_rag.logging_config import get_logger

log = get_logger(__name__)


class LanguageAnalysis(TypedDict):
    language: str
    translated_query: str


_DETECTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a language detection and translation utility.

Given a user question, return a JSON object with TWO fields:
1. "language": the full name of the question's language in English \
("English", "Spanish", "Portuguese", "French", etc.).
2. "translated_query": the question translated to English for document retrieval. \
If the question is already in English, return it as-is.

Rules:
- Preserve proper nouns (company names, product names, person names) unchanged.
- Keep the translation concise and semantically equivalent.
- Respond ONLY with valid JSON. No preamble, no explanation.

Examples:
Question: "When was Promtior founded?"
Response: {{"language": "English", "translated_query": "When was Promtior founded?"}}

Question: "Que servicios ofrece Promtior?"
Response: {{"language": "Spanish", "translated_query": "What services does Promtior offer?"}}

Question: "Quais sao os clientes da Promtior?"
Response: {{"language": "Portuguese", "translated_query": "Who are Promtior's clients?"}}
""",
        ),
        ("human", "Question: {question}"),
    ]
)


def build_language_analyzer() -> ChatOpenAI:
    """Build a cheap LLM instance for language detection + translation.

    We use the same model as the main chain for consistency, but with
    low max_tokens since the JSON response is short.
    """
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=0.0,
        max_tokens=200,
        api_key=settings.openai_api_key.get_secret_value(),
    )


def analyze_question(question: str) -> LanguageAnalysis:
    """Detect the question's language and produce an English translation.

    Returns a dict with 'language' and 'translated_query'. On parsing
    failure, defaults to English (no translation needed).
    """
    llm = build_language_analyzer()
    chain = _DETECTION_PROMPT | llm | JsonOutputParser()

    try:
        result = chain.invoke({"question": question})
        language = result.get("language", "English")
        translated = result.get("translated_query", question)
        log.debug(
            "language_analysis",
            question_preview=question[:50],
            detected=language,
            translated=translated[:50],
        )
        return {"language": language, "translated_query": translated}
    except Exception as exc:
        log.warning("language_analysis_failed", error=str(exc), question_preview=question[:50])
        # Safe fallback: treat as English, no translation.
        return {"language": "English", "translated_query": question}