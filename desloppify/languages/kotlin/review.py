"""Review guidance hooks for Kotlin."""

from __future__ import annotations

import re

HOLISTIC_REVIEW_DIMENSIONS: list[str] = [
    "design_coherence",
    "type_safety",
    "abstraction_fitness",
    "cross_module_architecture",
    "test_strategy",
    "error_consistency",
    "api_surface_coherence",
]

REVIEW_GUIDANCE = {
    "patterns": [
        "Prefer sealed classes/interfaces for state modeling with exhaustive when-expressions.",
        "Use structured concurrency — never GlobalScope; prefer coroutineScope/supervisorScope.",
        "Leverage type inference internally but use explicit types on public API surfaces.",
        "Prefer immutable data (val, data class) over mutable state (var, lateinit).",
    ],
    "auth": [
        "Centralize auth in Ktor plugins or OkHttp/Retrofit interceptors.",
        "Avoid scattering auth checks across individual handler functions.",
    ],
    "naming": (
        "Use camelCase for functions/properties, PascalCase for classes/interfaces/objects, "
        "SCREAMING_SNAKE_CASE for constants. Backtick-quoted names only in test functions."
    ),
}

MIGRATION_PATTERN_PAIRS: list[tuple[str, object, object]] = []
MIGRATION_MIXED_EXTENSIONS: set[str] = {".java"}
LOW_VALUE_PATTERN = re.compile(
    r"^\s*(?:package\s+[\w.]+\s*$|import\s+[\w.*]+\s*$)", re.MULTILINE
)

_IMPORT_RE = re.compile(r"(?m)^\s*import\s+([\w.*]+)\s*$")
_PUBLIC_FUN_RE = re.compile(
    r"(?m)^(?!.*\b(?:private|internal|protected)\b)\s*(?:suspend\s+)?fun\s+(\w+)\s*[(<]"
)
_PUBLIC_CLASS_RE = re.compile(
    r"(?m)^(?!.*\b(?:private|internal)\b)\s*(?:data\s+|sealed\s+|abstract\s+|open\s+|enum\s+)?"
    r"(?:class|interface|object)\s+(\w+)"
)


def module_patterns(content: str) -> list[str]:
    """Extract module-level dependency specs for review context."""
    return [match.group(1) for match in _IMPORT_RE.finditer(content)]


def api_surface(file_contents: dict[str, str]) -> dict[str, list[str]]:
    """Build minimal API-surface summary from parsed Kotlin files."""
    public_types: set[str] = set()
    public_functions: set[str] = set()
    for content in file_contents.values():
        for match in _PUBLIC_CLASS_RE.finditer(content):
            public_types.add(match.group(1))
        for match in _PUBLIC_FUN_RE.finditer(content):
            public_functions.add(match.group(1))

    return {
        "public_types": sorted(public_types),
        "public_functions": sorted(public_functions),
    }


__all__ = [
    "HOLISTIC_REVIEW_DIMENSIONS",
    "LOW_VALUE_PATTERN",
    "MIGRATION_MIXED_EXTENSIONS",
    "MIGRATION_PATTERN_PAIRS",
    "REVIEW_GUIDANCE",
    "api_surface",
    "module_patterns",
]
