"""Tests for Kotlin review guidance hooks."""

from __future__ import annotations

from desloppify.languages.kotlin.review import (
    LOW_VALUE_PATTERN,
    api_surface,
    module_patterns,
)


class TestModulePatterns:
    def test_extracts_imports(self):
        content = (
            "package com.example\n"
            "\n"
            "import com.example.util.Helper\n"
            "import kotlinx.coroutines.flow.Flow\n"
            "\n"
            "class MyService {}\n"
        )
        patterns = module_patterns(content)
        assert "com.example.util.Helper" in patterns
        assert "kotlinx.coroutines.flow.Flow" in patterns

    def test_no_imports(self):
        content = "package com.example\n\nclass MyService {}\n"
        patterns = module_patterns(content)
        assert patterns == []

    def test_star_import(self):
        content = "import kotlinx.coroutines.*\n"
        patterns = module_patterns(content)
        assert "kotlinx.coroutines.*" in patterns


class TestApiSurface:
    def test_public_function(self):
        files = {
            "Service.kt": "fun fetchUsers(): List<User> {\n    return emptyList()\n}\n"
        }
        surface = api_surface(files)
        assert "fetchUsers" in surface["public_functions"]

    def test_private_excluded(self):
        files = {"Service.kt": "private fun helper(): Int = 42\n"}
        surface = api_surface(files)
        assert "helper" not in surface["public_functions"]

    def test_internal_excluded(self):
        files = {"Service.kt": "internal fun helper(): Int = 42\n"}
        surface = api_surface(files)
        assert "helper" not in surface["public_functions"]

    def test_public_class(self):
        files = {"Models.kt": "data class User(val id: String, val name: String)\n"}
        surface = api_surface(files)
        assert "User" in surface["public_types"]

    def test_sealed_class(self):
        files = {
            "State.kt": "sealed class UiState {\n    object Loading : UiState()\n}\n"
        }
        surface = api_surface(files)
        assert "UiState" in surface["public_types"]

    def test_private_class_excluded(self):
        files = {"Internal.kt": "private class InternalHelper {}\n"}
        surface = api_surface(files)
        assert "InternalHelper" not in surface["public_types"]

    def test_suspend_function(self):
        files = {"Service.kt": "suspend fun loadData(): Data {\n    return Data()\n}\n"}
        surface = api_surface(files)
        assert "loadData" in surface["public_functions"]


class TestLowValuePattern:
    def test_package_declaration(self):
        assert LOW_VALUE_PATTERN.search("package com.example.app")

    def test_import_statement(self):
        assert LOW_VALUE_PATTERN.search("import com.example.util.Helper")

    def test_function_not_low_value(self):
        assert not LOW_VALUE_PATTERN.search("fun doSomething() {}")

    def test_class_not_low_value(self):
        assert not LOW_VALUE_PATTERN.search("class MyService {}")
