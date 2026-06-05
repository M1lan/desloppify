"""Tests for Kotlin function extraction."""

from __future__ import annotations

from desloppify.languages.kotlin.extractors import (
    _find_matching_brace,
    extract_kotlin_functions,
    find_kotlin_files,
    normalize_kotlin_body,
)


class TestExtractKotlinFunctions:
    """Verify extract_kotlin_functions() returns correct FunctionInfo objects."""

    def test_basic_function(self, tmp_path):
        kt = tmp_path / "Foo.kt"
        kt.write_text(
            "fun greet(name: String): String {\n"
            '    return "Hello, $name"\n'
            "}\n"
        )
        results = extract_kotlin_functions(str(kt))
        assert len(results) == 1
        fi = results[0]
        assert fi.name == "greet"
        assert fi.line == 1
        assert "greet" in fi.body

    def test_basic_function_body_contains_return(self, tmp_path):
        kt = tmp_path / "Calc.kt"
        kt.write_text(
            "fun add(a: Int, b: Int): Int {\n"
            "    return a + b\n"
            "}\n"
        )
        results = extract_kotlin_functions(str(kt))
        assert len(results) == 1
        assert "return a + b" in results[0].body

    def test_basic_function_end_line(self, tmp_path):
        kt = tmp_path / "Multi.kt"
        kt.write_text(
            "fun multi(\n"
            "    x: Int,\n"
            "    y: Int\n"
            "): Int {\n"
            "    return x * y\n"
            "}\n"
        )
        results = extract_kotlin_functions(str(kt))
        assert len(results) == 1
        fi = results[0]
        assert fi.end_line > fi.line

    def test_extension_function_receiver_type(self, tmp_path):
        kt = tmp_path / "Extensions.kt"
        kt.write_text(
            "fun String.isEmail(): Boolean {\n"
            '    return contains("@")\n'
            "}\n"
        )
        results = extract_kotlin_functions(str(kt))
        assert len(results) == 1
        assert results[0].name == "String.isEmail"

    def test_suspend_function(self, tmp_path):
        kt = tmp_path / "Network.kt"
        kt.write_text(
            "suspend fun fetchData(url: String): String {\n"
            '    return "data"\n'
            "}\n"
        )
        results = extract_kotlin_functions(str(kt))
        assert len(results) == 1
        assert results[0].name == "fetchData"

    def test_multiple_functions(self, tmp_path):
        kt = tmp_path / "Utils.kt"
        kt.write_text(
            "fun foo(): Int {\n"
            "    return 1\n"
            "}\n"
            "\n"
            "fun bar(): Int {\n"
            "    return 2\n"
            "}\n"
        )
        results = extract_kotlin_functions(str(kt))
        names = [fi.name for fi in results]
        assert "foo" in names
        assert "bar" in names

    def test_missing_file_returns_empty(self):
        results = extract_kotlin_functions("/nonexistent/path/Missing.kt")
        assert results == []

    def test_function_info_file_field(self, tmp_path):
        kt = tmp_path / "Check.kt"
        kt.write_text("fun check(): Boolean {\n    return true\n}\n")
        results = extract_kotlin_functions(str(kt))
        assert len(results) == 1
        assert results[0].file == str(kt)


class TestNormalizeKotlinBody:
    """Verify normalize_kotlin_body() strips noise."""

    def test_strips_blank_lines(self):
        body = "fun f() {\n\n    val x = 1\n\n    return x\n}"
        result = normalize_kotlin_body(body)
        assert "\n\n" not in result

    def test_strips_line_comments(self):
        body = "fun f() {\n    // this is a comment\n    return 1\n}"
        result = normalize_kotlin_body(body)
        assert "//" not in result
        assert "return 1" in result

    def test_strips_block_comments(self):
        body = "fun f() {\n    /* block\n       comment */\n    return 1\n}"
        result = normalize_kotlin_body(body)
        assert "block" not in result
        assert "return 1" in result

    def test_strips_logging_println(self):
        body = 'fun f() {\n    println("debug")\n    return 1\n}'
        result = normalize_kotlin_body(body)
        assert "println" not in result
        assert "return 1" in result

    def test_strips_logging_log(self):
        body = 'fun f() {\n    log.debug("x")\n    return 2\n}'
        result = normalize_kotlin_body(body)
        assert "log.debug" not in result
        assert "return 2" in result

    def test_strips_single_line_annotations(self):
        body = "fun f() {\n    @Suppress\n    val x = 1\n    return x\n}"
        result = normalize_kotlin_body(body)
        assert "@Suppress" not in result
        assert "val x = 1" in result

    def test_keeps_annotations_with_parens(self):
        # Annotations with parentheses (e.g. @Suppress("foo")) should NOT be stripped
        body = 'fun f() {\n    @Suppress("unchecked")\n    val x = 1\n    return x\n}'
        result = normalize_kotlin_body(body)
        assert "val x = 1" in result

    def test_empty_body(self):
        result = normalize_kotlin_body("")
        assert result == ""

    def test_only_comments(self):
        body = "// one\n/* two */\n"
        result = normalize_kotlin_body(body)
        assert result == ""


class TestBodyHashStability:
    """Verify body_hash is deterministic for identical content."""

    def test_same_body_same_hash(self, tmp_path):
        content = "fun stable(): Int {\n    return 42\n}\n"
        kt1 = tmp_path / "A.kt"
        kt2 = tmp_path / "B.kt"
        kt1.write_text(content)
        kt2.write_text(content)
        r1 = extract_kotlin_functions(str(kt1))
        r2 = extract_kotlin_functions(str(kt2))
        assert len(r1) == 1
        assert len(r2) == 1
        assert r1[0].body_hash == r2[0].body_hash

    def test_different_body_different_hash(self, tmp_path):
        kt1 = tmp_path / "C.kt"
        kt2 = tmp_path / "D.kt"
        kt1.write_text("fun f(): Int {\n    return 1\n}\n")
        kt2.write_text("fun f(): Int {\n    return 2\n}\n")
        r1 = extract_kotlin_functions(str(kt1))
        r2 = extract_kotlin_functions(str(kt2))
        assert r1[0].body_hash != r2[0].body_hash

    def test_hash_length(self, tmp_path):
        kt = tmp_path / "E.kt"
        kt.write_text("fun f(): Int {\n    return 0\n}\n")
        results = extract_kotlin_functions(str(kt))
        assert len(results[0].body_hash) == 12


class TestFindKotlinFiles:
    """Verify find_kotlin_files() respects exclusion directories."""

    def _make_file(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fun x() {}\n")

    def test_finds_kt_files(self, tmp_path):
        self._make_file(tmp_path / "src" / "Main.kt")
        files = find_kotlin_files(tmp_path)
        assert any("Main.kt" in f for f in files)

    def test_excludes_build_dir(self, tmp_path):
        self._make_file(tmp_path / "src" / "Main.kt")
        self._make_file(tmp_path / "build" / "Generated.kt")
        files = find_kotlin_files(tmp_path)
        assert not any("Generated.kt" in f for f in files)
        assert any("Main.kt" in f for f in files)

    def test_excludes_gradle_dir(self, tmp_path):
        self._make_file(tmp_path / "src" / "App.kt")
        self._make_file(tmp_path / ".gradle" / "Cache.kt")
        files = find_kotlin_files(tmp_path)
        assert not any("Cache.kt" in f for f in files)

    def test_finds_kts_files(self, tmp_path):
        self._make_file(tmp_path / "build.gradle.kts")
        files = find_kotlin_files(tmp_path)
        assert any("build.gradle.kts" in f for f in files)

    def test_empty_dir_returns_empty(self, tmp_path):
        files = find_kotlin_files(tmp_path)
        assert files == []


class TestFindMatchingBrace:
    """Verify _find_matching_brace() handles string literals correctly."""

    def test_simple_match(self):
        content = "{ val x = 1 }"
        assert _find_matching_brace(content, 0) == len(content) - 1

    def test_nested_braces(self):
        content = "{ if (true) { return 1 } }"
        result = _find_matching_brace(content, 0)
        assert result == len(content) - 1

    def test_string_with_brace_not_confused(self):
        content = '{ val s = "{" }'
        result = _find_matching_brace(content, 0)
        assert result == len(content) - 1

    def test_string_with_closing_brace(self):
        content = '{ val s = "}" }'
        result = _find_matching_brace(content, 0)
        assert result == len(content) - 1

    def test_triple_quoted_string_with_braces(self):
        content = '{ val s = """{nested}""" }'
        result = _find_matching_brace(content, 0)
        assert result == len(content) - 1

    def test_line_comment_with_brace(self):
        content = "{ // ignore {\n    return 1\n}"
        result = _find_matching_brace(content, 0)
        assert result == len(content) - 1

    def test_block_comment_with_brace(self):
        content = "{ /* { */ return 1 }"
        result = _find_matching_brace(content, 0)
        assert result == len(content) - 1

    def test_unmatched_returns_none(self):
        content = "{ val x = 1"
        result = _find_matching_brace(content, 0)
        assert result is None
