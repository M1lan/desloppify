"""Tests for Kotlin detector phases and smell detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from desloppify.languages.kotlin.phases import KOTLIN_COMPLEXITY_SIGNALS, phase_structural
from desloppify.languages.kotlin.detectors.smells import detect_smells
from desloppify.languages.kotlin.extractors import find_kotlin_files


# ---------------------------------------------------------------------------
# phase_structural tests
# ---------------------------------------------------------------------------


class TestKotlinComplexitySignals:
    def test_signal_count(self):
        assert len(KOTLIN_COMPLEXITY_SIGNALS) == 7

    def test_signal_names(self):
        names = [s.name for s in KOTLIN_COMPLEXITY_SIGNALS]
        assert "when branches" in names
        assert "coroutine launches" in names
        assert "TODOs" in names


class TestPhaseStructural:
    def test_phase_structural_callable(self, tmp_path):
        (tmp_path / "Main.kt").write_text("fun main() {}\n")

        lang = MagicMock()
        lang.large_threshold = 500
        lang.complexity_threshold = 15
        lang.props_threshold = 14
        lang.file_finder = find_kotlin_files
        lang.zone_map = None
        lang.dep_graph = None
        lang.complexity_map = {}
        lang.runtime_cache = {}
        lang.review_cache = {}
        lang.review_max_age_days = 30
        lang.subjective_assessments = {}
        lang.detector_coverage = {}
        lang.coverage_warnings = []
        lang.name = "kotlin"
        lang.extensions = [".kt", ".kts"]
        lang.entry_patterns = []
        lang.barrel_names = set()
        lang.external_test_dirs = []
        lang.test_file_extensions = [".kt"]
        lang.review_low_value_pattern = None
        lang.extract_functions = None
        lang.get_area = None
        lang.runtime_setting.return_value = None
        lang.runtime_option.return_value = None
        lang.scan_coverage_prerequisites.return_value = []

        issues, counts = phase_structural(tmp_path, lang)
        assert isinstance(issues, list)
        assert isinstance(counts, dict)


# ---------------------------------------------------------------------------
# detect_smells tests
# ---------------------------------------------------------------------------


def _write_kt(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


class TestDetectSmellsNonNullAssertion:
    def test_detects_nn_assertion_overuse(self, tmp_path):
        # >3 occurrences of !! triggers the smell
        _write_kt(tmp_path, "Foo.kt", "val a = x!!\nval b = y!!\nval c = z!!\nval d = w!!\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_non_null_assertion" in ids

    def test_no_detection_below_threshold(self, tmp_path):
        # exactly 3 should NOT trigger (threshold is 3, only triggers when >3)
        _write_kt(tmp_path, "Foo.kt", "val a = x!!\nval b = y!!\nval c = z!!\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_non_null_assertion" not in ids


class TestDetectSmellsGlobalScope:
    def test_detects_global_scope(self, tmp_path):
        _write_kt(tmp_path, "Foo.kt", "GlobalScope.launch { doWork() }\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_global_scope" in ids

    def test_detects_global_scope_async(self, tmp_path):
        _write_kt(tmp_path, "Foo.kt", "GlobalScope.async { doWork() }\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_global_scope" in ids


class TestDetectSmellsRunBlocking:
    def test_detects_run_blocking_production(self, tmp_path):
        _write_kt(tmp_path, "Foo.kt", "fun main() { runBlocking { doWork() } }\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_run_blocking" in ids

    def test_run_blocking_skipped_in_test_files(self, tmp_path):
        # Path contains /test/ so it should be skipped
        test_dir = tmp_path / "src" / "test" / "kotlin"
        test_dir.mkdir(parents=True)
        _write_kt(test_dir, "FooTest.kt", "fun setup() { runBlocking { doWork() } }\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_run_blocking" not in ids


class TestDetectSmellsMutableDataClass:
    def test_detects_var_in_data_class(self, tmp_path):
        _write_kt(tmp_path, "Foo.kt", "data class Foo(var x: Int, val y: String)\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_mutable_data_class" in ids

    def test_no_detection_val_only_data_class(self, tmp_path):
        _write_kt(tmp_path, "Foo.kt", "data class Foo(val x: Int, val y: String)\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_mutable_data_class" not in ids


class TestDetectSmellsLateinitMisuse:
    def test_detects_lateinit_var(self, tmp_path):
        _write_kt(tmp_path, "Foo.kt", "class Foo {\n    lateinit var foo: String\n}\n")
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_lateinit_misuse" in ids


class TestDetectSmellsEmptyCatch:
    def test_detects_empty_catch(self, tmp_path):
        content = "fun f() {\n    try { doWork() } catch (e: Exception) { }\n}\n"
        _write_kt(tmp_path, "Foo.kt", content)
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_empty_catch" in ids

    def test_no_detection_non_empty_catch(self, tmp_path):
        content = "fun f() {\n    try { doWork() } catch (e: Exception) { log(e) }\n}\n"
        _write_kt(tmp_path, "Foo.kt", content)
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_empty_catch" not in ids


class TestCommentAndStringExclusion:
    def test_nn_in_comment_not_detected(self, tmp_path):
        # !! appears only in a comment — strip should exclude them
        content = "// this!! is!! a!! comment!! with!! four!! bangs\nval x = 1\n"
        _write_kt(tmp_path, "Foo.kt", content)
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_non_null_assertion" not in ids

    def test_nn_in_string_not_detected(self, tmp_path):
        # !! inside string literals — the pattern uses stripped content but
        # _match_in_string should filter matches inside quoted strings.
        # We generate >3 occurrences all inside strings.
        content = (
            'val a = "x!!"\n'
            'val b = "y!!"\n'
            'val c = "z!!"\n'
            'val d = "w!!"\n'
        )
        _write_kt(tmp_path, "Foo.kt", content)
        entries, _ = detect_smells(tmp_path)
        ids = [e["id"] for e in entries]
        assert "kotlin_non_null_assertion" not in ids


class TestCleanFile:
    def test_clean_file_no_smells(self, tmp_path):
        _write_kt(
            tmp_path,
            "Clean.kt",
            "package com.example\n\nfun greet(name: String): String = \"Hello, $name\"\n",
        )
        entries, total = detect_smells(tmp_path)
        assert entries == []
        assert total == 1
