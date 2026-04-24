from __future__ import annotations

from unittest.mock import MagicMock, patch

from promtior_rag.chain import language as language_module


def test_analyze_question_returns_language_and_translation(
    mocker: MagicMock,
) -> None:
    """The function must return both 'language' and 'translated_query' keys."""
    fake_result = {
        "language": "Spanish",
        "translated_query": "When was Promtior founded?",
    }

    # Patch the JsonOutputParser so the final step of the chain returns our fake.
    # The chain is built inline as prompt | llm | JsonOutputParser(); by forcing
    # JsonOutputParser.invoke to return our dict, we bypass the real LLM call.
    mocker.patch.object(
        language_module,
        "build_language_analyzer",
        return_value=MagicMock(),
    )
    mocker.patch(
        "promtior_rag.chain.language.JsonOutputParser.invoke",
        return_value=fake_result,
    )

    result = language_module.analyze_question("¿Cuándo fue fundada Promtior?")

    assert result["language"] == "Spanish"
    assert result["translated_query"] == "When was Promtior founded?"


def test_analyze_question_falls_back_to_english_on_failure(
    mocker: MagicMock,
) -> None:
    """If the LLM call or JSON parsing raises, fall back to English with no translation."""
    mocker.patch.object(
        language_module,
        "build_language_analyzer",
        return_value=MagicMock(),
    )
    mocker.patch(
        "promtior_rag.chain.language.JsonOutputParser.invoke",
        side_effect=RuntimeError("network down"),
    )

    result = language_module.analyze_question("Any question")

    assert result["language"] == "English"
    assert result["translated_query"] == "Any question"