"""Tests for KotlinConfig plugin contract."""

from __future__ import annotations

from desloppify.languages.kotlin import Config, KotlinConfig, register, register_hooks


def test_name():
    assert KotlinConfig().name == "kotlin"


def test_extensions():
    assert KotlinConfig().extensions == [".kt", ".kts"]


def test_detect_markers():
    assert KotlinConfig().detect_markers == ["build.gradle.kts", "build.gradle"]


def test_integration_depth():
    assert KotlinConfig().integration_depth == "full"


def test_phases_count():
    assert len(KotlinConfig().phases) >= 8


def test_detect_commands_count():
    assert len(KotlinConfig().detect_commands) == 6


def test_file_finder_not_none():
    assert KotlinConfig().file_finder is not None


def test_extract_functions_not_none():
    assert KotlinConfig().extract_functions is not None


def test_zone_rules_count():
    assert len(KotlinConfig().zone_rules) == 8


def test_holistic_review_dimensions_count():
    assert len(KotlinConfig().holistic_review_dimensions) == 7


def test_review_guidance_not_empty():
    assert KotlinConfig().review_guidance


def test_review_module_patterns_fn_not_none():
    assert KotlinConfig().review_module_patterns_fn is not None


def test_review_api_surface_fn_not_none():
    assert KotlinConfig().review_api_surface_fn is not None


def test_register_no_error():
    register()


def test_register_hooks_no_error():
    register_hooks()


def test_config_is_kotlin_config():
    assert Config is KotlinConfig
