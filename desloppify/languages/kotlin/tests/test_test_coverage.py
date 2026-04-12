"""Tests for Kotlin test coverage hooks."""

from __future__ import annotations

from desloppify.languages.kotlin.test_coverage import (
    ASSERT_PATTERNS,
    MOCK_PATTERNS,
    TEST_FUNCTION_RE,
    has_testable_logic,
    map_test_to_source,
    strip_comments,
    strip_test_markers,
)


class TestHasTestableLogic:
    def test_function_declaration(self):
        assert has_testable_logic("foo.kt", "fun doSomething() {}")

    def test_class_declaration(self):
        assert has_testable_logic("foo.kt", "class MyService {}")

    def test_object_declaration(self):
        assert has_testable_logic("foo.kt", "object Constants {}")

    def test_empty_file(self):
        assert not has_testable_logic("foo.kt", "")

    def test_imports_only(self):
        assert not has_testable_logic(
            "foo.kt", "import com.example.Foo\npackage com.example\n"
        )


class TestMapTestToSource:
    def test_test_suffix(self):
        production = {"src/main/kotlin/com/app/Feature.kt"}
        result = map_test_to_source(
            "src/main/kotlin/com/app/FeatureTest.kt", production
        )
        assert result == "src/main/kotlin/com/app/Feature.kt"

    def test_spec_suffix(self):
        production = {"src/main/kotlin/com/app/Feature.kt"}
        result = map_test_to_source(
            "src/main/kotlin/com/app/FeatureSpec.kt", production
        )
        assert result == "src/main/kotlin/com/app/Feature.kt"

    def test_mirrored_test_dir(self):
        production = {"src/main/kotlin/com/app/Feature.kt"}
        result = map_test_to_source(
            "src/test/kotlin/com/app/FeatureTest.kt", production
        )
        assert result == "src/main/kotlin/com/app/Feature.kt"

    def test_no_match(self):
        production = {"src/main/kotlin/com/app/Other.kt"}
        result = map_test_to_source(
            "src/test/kotlin/com/app/FeatureTest.kt", production
        )
        assert result is None

    def test_non_test_file(self):
        production = {"src/main/kotlin/com/app/Feature.kt"}
        result = map_test_to_source("src/main/kotlin/com/app/Feature.kt", production)
        assert result is None


class TestStripTestMarkers:
    def test_strip_test(self):
        assert strip_test_markers("FeatureTest.kt") == "Feature.kt"

    def test_strip_spec(self):
        assert strip_test_markers("FeatureSpec.kt") == "Feature.kt"

    def test_no_marker(self):
        assert strip_test_markers("Feature.kt") is None

    def test_non_kotlin(self):
        assert strip_test_markers("FeatureTest.java") is None


class TestTestFunctionRegex:
    def test_annotated_test(self):
        assert TEST_FUNCTION_RE.search("    @Test fun testSomething()")

    def test_plain_test(self):
        assert TEST_FUNCTION_RE.search("    fun testSomething()")

    def test_backtick_test(self):
        assert TEST_FUNCTION_RE.search("    @Test fun `should do something`()")

    def test_non_test(self):
        assert not TEST_FUNCTION_RE.search("    fun doSomething()")


class TestAssertPatterns:
    def test_assert_equals(self):
        assert any(p.search("assertEquals(expected, actual)") for p in ASSERT_PATTERNS)

    def test_should_be(self):
        assert any(p.search("result shouldBe expected") for p in ASSERT_PATTERNS)


class TestMockPatterns:
    def test_mockk(self):
        assert any(
            p.search("val service = mockk<UserService>()") for p in MOCK_PATTERNS
        )

    def test_every(self):
        assert any(
            p.search("every { service.getUser() } returns user") for p in MOCK_PATTERNS
        )

    def test_co_every(self):
        assert any(
            p.search("coEvery { service.fetchUser() } returns user")
            for p in MOCK_PATTERNS
        )


class TestStripComments:
    def test_line_comment(self):
        result = strip_comments("val x = 1 // comment\nval y = 2")
        assert "comment" not in result
        assert "val x = 1" in result
        assert "val y = 2" in result

    def test_block_comment(self):
        result = strip_comments("val x = 1 /* block\ncomment */ val y = 2")
        assert "block" not in result
        assert "val x = 1" in result
        assert "val y = 2" in result

    def test_string_preserved(self):
        result = strip_comments('val x = "// not a comment"')
        assert "// not a comment" in result

    def test_triple_quoted_string(self):
        result = strip_comments('val x = """has // slashes"""')
        assert "// slashes" in result
