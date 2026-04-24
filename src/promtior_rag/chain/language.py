"""Language detection utilities for the RAG chain.

Used to make the LLM's language matching deterministic: instead of relying
on the model to infer the question's language from context (which can be
overridden by the retrieved content's language), we detect it explicitly
in code and inject the result into the prompt.
"""

from __future__ import annotations

from langdetect import DetectorFactory, detect, LangDetectException

from promtior_rag.logging_config import get_logger

log = get_logger(__name__)

# Seed the detector for reproducible results.
# langdetect is non-deterministic by default (random sampling of features).
DetectorFactory.seed = 0

# Map ISO 639-1 codes to human-readable names the LLM responds to well.
_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese",
}

_DEFAULT_LANGUAGE = "English"
_MIN_LENGTH = 3


def detect_language(text: str) -> str:
    """Detect the language of a text and return a human-readable name.

    Falls back to English on detection failure (empty input, too short,
    ambiguous text). This is a safe default because the prompt's base
    behavior is English-first.
    """
    if not text or len(text.strip()) < _MIN_LENGTH:
        return _DEFAULT_LANGUAGE

    try:
        code = detect(text)
        language = _LANGUAGE_NAMES.get(code, _DEFAULT_LANGUAGE)
        log.debug("language_detected", text_preview=text[:50], code=code, language=language)
        return language
    except LangDetectException as exc:
        log.warning("language_detection_failed", text_preview=text[:50], error=str(exc))
        return _DEFAULT_LANGUAGE