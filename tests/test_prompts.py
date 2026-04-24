from __future__ import annotations

from promtior_rag.chain.prompts import build_rag_prompt


def test_prompt_renders_with_all_required_variables() -> None:
    """The prompt must declare context, question, and language as input variables."""
    prompt = build_rag_prompt()

    assert "context" in prompt.input_variables
    assert "question" in prompt.input_variables
    assert "language" in prompt.input_variables


def test_prompt_includes_entity_attribution_rules() -> None:
    """The system prompt must keep the Promtior/Knowment entity-attribution rule.

    This protects challenge #1 from regressions: if someone refactors the prompt
    and drops the Kahan few-shot, this test fails before it reaches production.
    """
    prompt = build_rag_prompt()

    rendered = prompt.format(
        context="sample context",
        question="sample question",
        language="English",
    )

    lowered = rendered.lower()
    assert "kahan" in lowered or "knowment" in lowered, (
        "Expected the Promtior vs Knowment entity-attribution example "
        "to be present in the system prompt"
    )


def test_prompt_instructs_language_matching() -> None:
    """The rendered prompt must include the detected language as an instruction."""
    prompt = build_rag_prompt()

    rendered = prompt.format(
        context="sample context",
        question="¿Cuándo fue fundada?",
        language="Spanish",
    )

    assert "Spanish" in rendered