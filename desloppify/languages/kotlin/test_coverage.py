"""Kotlin-specific test coverage heuristics and mappings."""

from __future__ import annotations

import os
import re

ASSERT_PATTERNS = [
    re.compile(p)
    for p in [
        r"\bassertEquals\b",
        r"\bassertTrue\b",
        r"\bassertFalse\b",
        r"\bassertNotNull\b",
        r"\bassertNull\b",
        r"\bassertThat\b",
        r"\bshouldBe\b",
        r"\bshouldNotBe\b",
        r"\bexpectThat\b",
    ]
]
MOCK_PATTERNS = [
    re.compile(p)
    for p in [
        r"\bmockk<",
        r"\bevery\s*\{",
        r"\bverify\s*\{",
        r"\bcoEvery\s*\{",
        r"\bcoVerify\s*\{",
        r"\bmock\(",
        r"\bwhenever\(",
    ]
]
SNAPSHOT_PATTERNS: list[re.Pattern[str]] = []
TEST_FUNCTION_RE = re.compile(
    r"(?m)^\s*(?:@Test\s+)?fun\s+(?:`[^`]+`|test\w+)\s*\("
)
BARREL_BASENAMES: set[str] = set()


def has_testable_logic(_filepath: str, content: str) -> bool:
    """Return True when a Kotlin file contains function or class declarations."""
    return bool(re.search(r"(?m)(?:^\s*fun\s+|^\s*class\s+|^\s*object\s+)", content))


def resolve_import_spec(
    spec: str, test_path: str, production_files: set[str]
) -> str | None:
    """Best-effort Kotlin import-path to source-file resolution."""
    normalized = spec.strip().strip("\"'`").replace("\\", "/").strip("/")
    if not normalized or normalized.endswith(".*"):
        return None

    parts = normalized.split(".")
    if len(parts) < 2:
        return None

    candidates: list[str] = []
    for ext in (".kt", ".kts"):
        rel_path = os.path.join(*parts[:-1], parts[-1] + ext)
        candidates.append(rel_path)

    normalized_production = {
        file_path.replace("\\", "/").strip("/"): file_path
        for file_path in production_files
    }
    for candidate in candidates:
        normalized_candidate = candidate.replace("\\", "/").strip("/")
        if normalized_candidate in normalized_production:
            return normalized_production[normalized_candidate]
        suffix = f"/{normalized_candidate}"
        for normalized_path, original in normalized_production.items():
            if normalized_path.endswith(suffix):
                return original
    return None


def resolve_barrel_reexports(_filepath: str, _production_files: set[str]) -> set[str]:
    return set()


def parse_test_import_specs(_content: str) -> list[str]:
    return []


def map_test_to_source(test_path: str, production_set: set[str]) -> str | None:
    """Map a Kotlin test file to its source counterpart by naming convention."""
    basename = os.path.basename(test_path)

    # Try FooTest.kt -> Foo.kt
    for marker in ("Test.kt", "Spec.kt"):
        if basename.endswith(marker):
            src_basename = basename[: -len(marker)] + ".kt"
            src = test_path[: -len(basename)] + src_basename
            if src in production_set:
                return src
            # Try mirroring src/test -> src/main
            for test_dir, main_dir in [
                ("src/test/", "src/main/"),
                ("src/androidTest/", "src/main/"),
                ("src/commonTest/", "src/commonMain/"),
                ("src/jvmTest/", "src/jvmMain/"),
                ("src/iosTest/", "src/iosMain/"),
            ]:
                if test_dir in src:
                    src_mirrored = src.replace(test_dir, main_dir, 1)
                    if src_mirrored in production_set:
                        return src_mirrored

    return None


def strip_test_markers(basename: str) -> str | None:
    """Strip Kotlin test naming markers to derive source basename."""
    for marker in ("Test.kt", "Spec.kt"):
        if basename.endswith(marker):
            return basename[: -len(marker)] + ".kt"
    return None


def strip_comments(content: str) -> str:
    """Strip Kotlin comments while preserving string literals."""
    out: list[str] = []
    in_block = False
    in_string: str | None = None
    i = 0
    while i < len(content):
        ch = content[i]
        nxt = content[i + 1] if i + 1 < len(content) else ""

        if in_block:
            if ch == "\n":
                out.append("\n")
            if ch == "*" and nxt == "/":
                in_block = False
                i += 2
                continue
            i += 1
            continue

        if in_string is not None:
            out.append(ch)
            if ch == "\\" and i + 1 < len(content):
                out.append(content[i + 1])
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue

        if ch == '"':
            # Check for triple-quoted string
            if nxt == '"' and i + 2 < len(content) and content[i + 2] == '"':
                # Skip triple-quoted string
                out.append('"""')
                i += 3
                while i < len(content):
                    if (
                        content[i] == '"'
                        and i + 2 < len(content)
                        and content[i + 1] == '"'
                        and content[i + 2] == '"'
                    ):
                        out.append('"""')
                        i += 3
                        break
                    out.append(content[i])
                    i += 1
                continue
            in_string = '"'
            out.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "*":
            in_block = True
            i += 2
            continue
        if ch == "/" and nxt == "/":
            while i < len(content) and content[i] != "\n":
                i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)
