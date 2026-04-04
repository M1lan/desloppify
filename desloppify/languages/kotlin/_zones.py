"""Zone/path classification rules for Kotlin."""

from __future__ import annotations

from desloppify.engine.policy.zones import COMMON_ZONE_RULES, Zone, ZoneRule

KOTLIN_ZONE_RULES = [
    ZoneRule(Zone.GENERATED, ["/build/", "/generated/", ".generated.kt"]),
    ZoneRule(
        Zone.TEST,
        [
            "Test.kt",
            "Spec.kt",
            "_test.kt",
            "/src/test/",
            "/src/androidTest/",
            "/src/commonTest/",
            "/src/jvmTest/",
            "/src/iosTest/",
        ],
    ),
    ZoneRule(
        Zone.CONFIG,
        [
            "build.gradle.kts",
            "build.gradle",
            "settings.gradle.kts",
            "settings.gradle",
            "gradle.properties",
            "proguard-rules.pro",
        ],
    ),
    ZoneRule(Zone.SCRIPT, ["/buildSrc/", "/scripts/"]),
] + COMMON_ZONE_RULES

__all__ = ["KOTLIN_ZONE_RULES"]
