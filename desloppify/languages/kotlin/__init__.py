"""Kotlin language configuration for Desloppify."""

from __future__ import annotations

from desloppify.base.discovery.paths import get_area
from desloppify.languages._framework.base.phase_builders import (
    detector_phase_security,
    detector_phase_signature,
    detector_phase_test_coverage,
    shared_subjective_duplicates_tail,
)
from desloppify.languages._framework.base.types import DetectorPhase, LangConfig
from desloppify.languages._framework.generic_support.core import make_tool_phase
from desloppify.languages._framework.registry.registration import register_full_plugin
from desloppify.languages._framework.registry.state import register_lang_hooks
from desloppify.languages._framework.treesitter.phases import all_treesitter_phases
from desloppify.languages.kotlin import test_coverage as kotlin_test_coverage_hooks
from desloppify.languages.kotlin.commands import get_detect_commands
from desloppify.languages.kotlin.detectors.deps import build_dep_graph
from desloppify.languages.kotlin.extractors import (
    KOTLIN_FILE_EXCLUSIONS,
    extract_functions,
    find_kotlin_files,
)
from desloppify.languages.kotlin.phases import phase_structural
from desloppify.languages.kotlin.phases_smells import phase_kotlin_smells
from desloppify.languages.kotlin.review import (
    HOLISTIC_REVIEW_DIMENSIONS,
    LOW_VALUE_PATTERN,
    MIGRATION_MIXED_EXTENSIONS,
    MIGRATION_PATTERN_PAIRS,
    REVIEW_GUIDANCE,
    api_surface,
    module_patterns,
)

from desloppify.languages.kotlin._zones import KOTLIN_ZONE_RULES

KOTLIN_ENTRY_PATTERNS = ["/main.kt", "/Application.kt", "/Main.kt", "/App.kt"]


class KotlinConfig(LangConfig):
    """Kotlin language configuration."""

    def __init__(self):
        super().__init__(
            name="kotlin",
            extensions=[".kt", ".kts"],
            exclusions=KOTLIN_FILE_EXCLUSIONS,
            default_src=".",
            build_dep_graph=build_dep_graph,
            entry_patterns=KOTLIN_ENTRY_PATTERNS,
            barrel_names=set(),
            phases=[
                DetectorPhase("Structural analysis", phase_structural),
                DetectorPhase("Kotlin smells", phase_kotlin_smells),
                make_tool_phase(
                    "ktlint",
                    "ktlint --reporter=json",
                    "json",
                    "ktlint_violation",
                    tier=2,
                ),
                *all_treesitter_phases("kotlin"),
                detector_phase_signature(),
                detector_phase_test_coverage(),
                detector_phase_security(),
                *shared_subjective_duplicates_tail(),
            ],
            fixers={},
            get_area=get_area,
            detect_commands=get_detect_commands(),
            boundaries=[],
            typecheck_cmd="",
            file_finder=find_kotlin_files,
            large_threshold=500,
            complexity_threshold=15,
            default_scan_profile="full",
            detect_markers=["build.gradle.kts", "build.gradle"],
            external_test_dirs=[],
            test_file_extensions=[".kt"],
            review_module_patterns_fn=module_patterns,
            review_api_surface_fn=api_surface,
            review_guidance=REVIEW_GUIDANCE,
            review_low_value_pattern=LOW_VALUE_PATTERN,
            holistic_review_dimensions=HOLISTIC_REVIEW_DIMENSIONS,
            migration_pattern_pairs=MIGRATION_PATTERN_PAIRS,
            migration_mixed_extensions=MIGRATION_MIXED_EXTENSIONS,
            extract_functions=extract_functions,
            zone_rules=KOTLIN_ZONE_RULES,
        )


def register() -> None:
    """Register Kotlin language config + hooks through an explicit entrypoint."""
    register_full_plugin(
        "kotlin",
        KotlinConfig,
        test_coverage=kotlin_test_coverage_hooks,
    )


def register_hooks() -> None:
    """Register Kotlin hook modules without language-config bootstrap."""
    register_lang_hooks("kotlin", test_coverage=kotlin_test_coverage_hooks)


Config = KotlinConfig


__all__ = [
    "Config",
    "KotlinConfig",
    "register",
    "register_hooks",
    "KOTLIN_ENTRY_PATTERNS",
    "KOTLIN_ZONE_RULES",
    "HOLISTIC_REVIEW_DIMENSIONS",
    "LOW_VALUE_PATTERN",
    "MIGRATION_MIXED_EXTENSIONS",
    "MIGRATION_PATTERN_PAIRS",
    "REVIEW_GUIDANCE",
]
