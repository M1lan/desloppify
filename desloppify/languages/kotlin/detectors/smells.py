"""Kotlin code smell detection."""

from __future__ import annotations

import re
from pathlib import Path

from desloppify.base.discovery.file_paths import rel, resolve_path
from desloppify.languages.kotlin.extractors import find_kotlin_files

SEVERITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}

# ---------------------------------------------------------------------------
# Smell catalog
# ---------------------------------------------------------------------------

KOTLIN_SMELL_CHECKS: list[dict] = [
    {
        "id": "kotlin_non_null_assertion",
        "label": "!! overuse (non-null assertion)",
        "severity": "high",
        "pattern": r"!!(?!\s*//)",
        "per_file_threshold": 3,
    },
    {
        "id": "kotlin_global_scope",
        "label": "GlobalScope usage",
        "severity": "high",
        "pattern": r"\bGlobalScope\s*\.\s*(?:launch|async)\b",
    },
    {
        "id": "kotlin_run_blocking",
        "label": "runBlocking in production code",
        "severity": "high",
        "pattern": r"\brunBlocking\s*(?:\(|\{)",
        "skip_test": True,
    },
    {
        "id": "kotlin_mutable_data_class",
        "label": "var in data class",
        "severity": "medium",
        "pattern": None,
    },
    {
        "id": "kotlin_lateinit_misuse",
        "label": "lateinit var usage",
        "severity": "medium",
        "pattern": r"\blateinit\s+var\b",
    },
    {
        "id": "kotlin_empty_catch",
        "label": "empty catch block",
        "severity": "medium",
        "pattern": None,
    },
]

# ---------------------------------------------------------------------------
# Comment / string stripping (preserves line structure)
# ---------------------------------------------------------------------------

_TEST_PATH_MARKERS = (
    "/test/",
    "/tests/",
    "/androidTest/",
    "/commonTest/",
    "/jvmTest/",
    "/iosTest/",
    "/jsTest/",
)


def _is_test_path(filepath: str) -> bool:
    normalized = filepath.replace("\\", "/")
    return any(marker in normalized for marker in _TEST_PATH_MARKERS)


def _strip_kotlin_comments(content: str) -> str:
    """Replace comments with whitespace, preserving line numbers.  Strings kept intact."""
    out: list[str] = []
    i = 0
    length = len(content)

    while i < length:
        ch = content[i]
        nxt = content[i + 1] if i + 1 < length else ""

        # Block comment
        if ch == "/" and nxt == "*":
            out.append("  ")
            i += 2
            while i < length:
                if content[i] == "*" and i + 1 < length and content[i + 1] == "/":
                    out.append("  ")
                    i += 2
                    break
                out.append("\n" if content[i] == "\n" else " ")
                i += 1
            continue

        # Line comment
        if ch == "/" and nxt == "/":
            while i < length and content[i] != "\n":
                out.append(" ")
                i += 1
            continue

        # Triple-quoted string — keep content
        if ch == '"' and nxt == '"' and i + 2 < length and content[i + 2] == '"':
            out.append('"""')
            i += 3
            while i < length:
                if (
                    content[i] == '"'
                    and i + 2 < length
                    and content[i + 1] == '"'
                    and content[i + 2] == '"'
                ):
                    out.append('"""')
                    i += 3
                    break
                out.append(content[i])
                i += 1
            continue

        # Regular string — keep content
        if ch == '"':
            out.append(ch)
            i += 1
            while i < length:
                c = content[i]
                out.append(c)
                if c == "\\":
                    i += 1
                    if i < length:
                        out.append(content[i])
                    i += 1
                    continue
                if c == '"':
                    i += 1
                    break
                i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def _line_preview(content: str, line_num: int) -> str:
    lines = content.splitlines()
    if 1 <= line_num <= len(lines):
        return lines[line_num - 1].strip()[:100]
    return ""


def _match_in_string(line: str, match_start: int) -> bool:
    """Rough check: is match_start inside a string literal on this line?"""
    in_str = False
    escape = False
    for i, ch in enumerate(line):
        if i == match_start:
            return in_str
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
    return False


# ---------------------------------------------------------------------------
# Semantic detectors
# ---------------------------------------------------------------------------

_DATA_CLASS_RE = re.compile(
    r"(?m)^[ \t]*(?:public\s+|internal\s+|private\s+)?data\s+class\s+\w+"
)
_VAR_IN_BODY_RE = re.compile(r"\bvar\s+\w+\s*:")


def _detect_mutable_data_classes(
    filepath: str,
    raw_content: str,
    stripped: str,
    smell_counts: dict[str, list[dict]],
) -> None:
    for m in _DATA_CLASS_RE.finditer(stripped):
        # Find the class body (opening brace after the match)
        brace = stripped.find("(", m.end())
        if brace == -1:
            continue
        # Scan the primary constructor for var declarations
        depth = 1
        i = brace + 1
        ctor_text = []
        while i < len(stripped) and depth > 0:
            ch = stripped[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth > 0:
                ctor_text.append(ch)
            i += 1
        ctor = "".join(ctor_text)
        if _VAR_IN_BODY_RE.search(ctor):
            line = _line_number(stripped, m.start())
            smell_counts["kotlin_mutable_data_class"].append(
                {
                    "file": filepath,
                    "line": line,
                    "content": _line_preview(raw_content, line),
                }
            )


_CATCH_RE = re.compile(r"\bcatch\s*\([^)]*\)\s*\{")


def _detect_empty_catch(
    filepath: str,
    raw_content: str,
    stripped: str,
    smell_counts: dict[str, list[dict]],
) -> None:
    for m in _CATCH_RE.finditer(stripped):
        # Check if the block body is empty (only whitespace before closing brace)
        after = stripped[m.end() :]
        rest = after.lstrip()
        if rest.startswith("}"):
            line = _line_number(stripped, m.start())
            smell_counts["kotlin_empty_catch"].append(
                {
                    "file": filepath,
                    "line": line,
                    "content": _line_preview(raw_content, line),
                }
            )


# ---------------------------------------------------------------------------
# Pattern scanning
# ---------------------------------------------------------------------------


def _scan_pattern_smells(
    filepath: str,
    raw_content: str,
    stripped: str,
    smell_counts: dict[str, list[dict]],
    *,
    is_test: bool,
) -> None:
    for check in KOTLIN_SMELL_CHECKS:
        pattern = check.get("pattern")
        if pattern is None:
            continue
        if is_test and check.get("skip_test"):
            continue

        per_file: list[dict] = []
        for match in re.finditer(pattern, stripped):
            line = _line_number(stripped, match.start())
            line_text = (
                stripped.splitlines()[line - 1]
                if line <= len(stripped.splitlines())
                else ""
            )
            if _match_in_string(
                line_text, match.start() - stripped.rfind("\n", 0, match.start()) - 1
            ):
                continue
            per_file.append(
                {
                    "file": filepath,
                    "line": line,
                    "content": _line_preview(raw_content, line),
                }
            )

        threshold = check.get("per_file_threshold")
        if threshold and len(per_file) <= threshold:
            continue
        smell_counts[check["id"]].extend(per_file)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_smells(path: Path) -> tuple[list[dict], int]:
    """Detect Kotlin-specific code smell patterns across source files."""
    smell_counts: dict[str, list[dict]] = {
        check["id"]: [] for check in KOTLIN_SMELL_CHECKS
    }
    total_files = 0

    for filepath in find_kotlin_files(path):
        absolute = Path(resolve_path(filepath))
        is_test = _is_test_path(filepath)
        total_files += 1

        try:
            content = absolute.read_text(errors="replace")
        except OSError:
            continue

        stripped = _strip_kotlin_comments(content)
        normalized_file = rel(absolute)

        _scan_pattern_smells(
            normalized_file, content, stripped, smell_counts, is_test=is_test
        )
        _detect_mutable_data_classes(normalized_file, content, stripped, smell_counts)
        _detect_empty_catch(normalized_file, content, stripped, smell_counts)

    entries: list[dict] = []
    for check in KOTLIN_SMELL_CHECKS:
        matches = smell_counts[check["id"]]
        if not matches:
            continue
        entries.append(
            {
                "id": check["id"],
                "label": check["label"],
                "severity": check["severity"],
                "count": len(matches),
                "files": len({m["file"] for m in matches}),
                "matches": matches[:50],
            }
        )
    entries.sort(key=lambda e: (SEVERITY_ORDER.get(e["severity"], 9), -e["count"]))
    return entries, total_files


__all__ = ["KOTLIN_SMELL_CHECKS", "SEVERITY_ORDER", "detect_smells"]
