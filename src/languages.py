# Provides shared language-code normalization and translation-direction defaults.

from __future__ import annotations


# Language aliases that Soniox should receive as the ISO 639-1 Czech code.
# @var frozenset[str]
CZECH_LANGUAGE_CODES = frozenset({"cs", "cz"})


def normalize_language_code(value: str) -> str:
    # Normalizes a command-line language code for Soniox requests.
    # --------------------------------------------------------------------------
    # @param value: User-supplied language code.
    # @return: Lower-case language code, with Czech aliases normalized to `cs`.
    # @throws ValueError: If the supplied value is empty.
    # --------------------------------------------------------------------------
    # reject empty arguments before constructing a remote session configuration.
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("language code cannot be empty")

    # use Soniox's canonical Czech language code for either common spelling.
    if normalized in CZECH_LANGUAGE_CODES:
        return "cs"
    return normalized
#end def


def resolve_translation_languages(
    source_language: str,
    target_language: str | None,
) -> tuple[str, str]:
    # Resolves a normalized source and explicit or inferred target language pair.
    # --------------------------------------------------------------------------
    # Czech speech defaults to English; every other source defaults to Czech.
    # @param source_language: Required source language supplied by the user.
    # @param target_language: Optional target language supplied by the user.
    # @return: Normalized `(source_language, target_language)` pair.
    # @throws ValueError: If either supplied language code is empty.
    # --------------------------------------------------------------------------
    # normalize the source before selecting its complementary default target.
    source = normalize_language_code(source_language)
    if target_language is None:
        return source, "en" if source == "cs" else "cs"

    # preserve an explicit direction while applying the same alias normalization.
    return source, normalize_language_code(target_language)
#end def
