"""Kotlin file discovery and function extraction.

Uses tree-sitter for extraction when available; provides the file discovery
and normalization helpers needed by the full plugin contract.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from desloppify.base.discovery.file_paths import resolve_path
from desloppify.base.discovery.source import SourceDiscoveryOptions, find_source_files
from desloppify.engine.detectors.base import FunctionInfo

KOTLIN_FILE_EXCLUSIONS = ["build", ".gradle", ".idea", "node_modules"]

_FUNC_DECL_RE = re.compile(
    r"(?m)^(?:\s*@\w+[^\n]*\n)*"  # optional annotations
    r"\s*(?:(?:private|internal|protected|public|open|override|inline|suspend|operator|infix)\s+)*"
    r"fun\s+"
    r"(?:(\w+)\.)??"  # optional receiver type
    r"(\w+)"  # function name
    r"\s*(?:<[^>]+>\s*)?"  # optional type params
    r"\("
)

_LOG_RE = re.compile(
    r"^\s*(?:println\(|print\(|Logger\.\w+|log\.\w+|Timber\.\w+|Log\.\w+)",
)


def find_kotlin_files(path: Path | str) -> list[str]:
    """Find Kotlin source files under path."""
    return find_source_files(
        path,
        [".kt", ".kts"],
        SourceDiscoveryOptions(exclusions=tuple(KOTLIN_FILE_EXCLUSIONS)),
    )


def normalize_kotlin_body(body: str) -> str:
    """Strip comments, blank lines, logging, and annotations for duplicate detection."""
    lines: list[str] = []
    in_block_comment = False
    for raw_line in body.splitlines():
        stripped = raw_line.strip()

        # Handle block comments
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block_comment = True
            continue

        if not stripped:
            continue
        # Skip line comments
        if stripped.startswith("//"):
            continue
        # Skip single-line annotations
        if stripped.startswith("@") and "(" not in stripped:
            continue
        # Skip common logging/debug statements
        if _LOG_RE.match(stripped):
            continue
        lines.append(stripped)
    return "\n".join(lines)


def _find_matching_brace(content: str, open_pos: int) -> int | None:
    """Find closing brace for a Kotlin function body with string awareness."""
    depth = 0
    i = open_pos
    length = len(content)
    while i < length:
        ch = content[i]

        # Block comment
        if ch == "/" and i + 1 < length and content[i + 1] == "*":
            i += 2
            while i + 1 < length:
                if content[i] == "*" and content[i + 1] == "/":
                    i += 2
                    break
                i += 1
            else:
                i += 1
            continue

        # Line comment
        if ch == "/" and i + 1 < length and content[i + 1] == "/":
            while i < length and content[i] != "\n":
                i += 1
            continue

        # String literal
        if ch == '"':
            # Triple-quoted string
            if i + 2 < length and content[i + 1] == '"' and content[i + 2] == '"':
                i += 3
                while i + 2 < length:
                    if (
                        content[i] == '"'
                        and content[i + 1] == '"'
                        and content[i + 2] == '"'
                    ):
                        i += 3
                        break
                    i += 1
                continue
            # Regular string
            i += 1
            while i < length:
                c = content[i]
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    break
                i += 1
            i += 1
            continue

        # Char literal
        if ch == "'":
            i += 1
            while i < length:
                c = content[i]
                if c == "\\":
                    i += 2
                    continue
                if c == "'":
                    break
                i += 1
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i

        i += 1
    return None


def extract_kotlin_functions(filepath: str) -> list[FunctionInfo]:
    """Extract Kotlin functions/methods from one file."""
    try:
        content = Path(resolve_path(filepath)).read_text(errors="replace")
    except OSError:
        return []

    functions: list[FunctionInfo] = []
    for match in _FUNC_DECL_RE.finditer(content):
        receiver = match.group(1)
        name = match.group(2)
        if receiver:
            name = f"{receiver}.{name}"

        start = match.start()
        start_line = content.count("\n", 0, start) + 1

        # Find the opening brace of the function body
        brace_pos = content.find("{", match.end())
        if brace_pos == -1:
            continue

        end = _find_matching_brace(content, brace_pos)
        if end is None:
            continue

        end_line = content.count("\n", 0, end) + 1
        body = content[start : end + 1]

        normalized = normalize_kotlin_body(body)
        body_hash = hashlib.md5(
            normalized.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()[:12]
        functions.append(
            FunctionInfo(
                name=name,
                file=resolve_path(filepath),
                line=start_line,
                end_line=end_line,
                loc=max(1, end_line - start_line + 1),
                body=body,
                normalized=normalized,
                body_hash=body_hash,
                params=[],
            )
        )

    return functions


def extract_functions(path: Path) -> list[FunctionInfo]:
    """Extract all Kotlin functions below a directory path."""
    functions: list[FunctionInfo] = []
    for filepath in find_kotlin_files(path):
        functions.extend(extract_kotlin_functions(filepath))
    return functions
