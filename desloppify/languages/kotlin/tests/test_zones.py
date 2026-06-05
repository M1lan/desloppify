"""Tests for Kotlin zone classification rules."""

from __future__ import annotations

from desloppify.engine.policy.zones import Zone, classify_file
from desloppify.languages.kotlin._zones import KOTLIN_ZONE_RULES


class TestKotlinZoneRules:
    """Verify Kotlin-specific zone classification."""

    def test_production_source(self):
        assert classify_file("src/main/kotlin/com/app/Feature.kt", KOTLIN_ZONE_RULES) == Zone.PRODUCTION

    def test_production_top_level(self):
        assert classify_file("com/app/Service.kt", KOTLIN_ZONE_RULES) == Zone.PRODUCTION

    def test_test_suffix_test_kt(self):
        assert classify_file("src/test/kotlin/com/app/FeatureTest.kt", KOTLIN_ZONE_RULES) == Zone.TEST

    def test_test_suffix_spec_kt(self):
        assert classify_file("src/test/kotlin/com/app/FeatureSpec.kt", KOTLIN_ZONE_RULES) == Zone.TEST

    def test_test_src_test_dir(self):
        assert classify_file("src/test/kotlin/com/app/Helper.kt", KOTLIN_ZONE_RULES) == Zone.TEST

    def test_test_android_test_dir(self):
        assert classify_file("src/androidTest/kotlin/com/app/UITest.kt", KOTLIN_ZONE_RULES) == Zone.TEST

    def test_test_common_test_dir(self):
        assert classify_file("src/commonTest/kotlin/TestUtils.kt", KOTLIN_ZONE_RULES) == Zone.TEST

    def test_test_jvm_test_dir(self):
        assert classify_file("src/jvmTest/kotlin/JvmTest.kt", KOTLIN_ZONE_RULES) == Zone.TEST

    def test_test_ios_test_dir(self):
        assert classify_file("src/iosTest/kotlin/IosTest.kt", KOTLIN_ZONE_RULES) == Zone.TEST

    def test_generated_build_dir(self):
        assert classify_file("build/generated/source/kapt/main/Module.kt", KOTLIN_ZONE_RULES) == Zone.GENERATED

    def test_generated_annotation(self):
        assert classify_file("com/app/Foo.generated.kt", KOTLIN_ZONE_RULES) == Zone.GENERATED

    def test_generated_dir(self):
        assert classify_file("generated/com/app/Foo.kt", KOTLIN_ZONE_RULES) == Zone.GENERATED

    def test_config_build_gradle_kts(self):
        assert classify_file("build.gradle.kts", KOTLIN_ZONE_RULES) == Zone.CONFIG

    def test_config_build_gradle(self):
        assert classify_file("build.gradle", KOTLIN_ZONE_RULES) == Zone.CONFIG

    def test_config_settings_gradle_kts(self):
        assert classify_file("settings.gradle.kts", KOTLIN_ZONE_RULES) == Zone.CONFIG

    def test_config_settings_gradle(self):
        assert classify_file("settings.gradle", KOTLIN_ZONE_RULES) == Zone.CONFIG

    def test_config_gradle_properties(self):
        assert classify_file("gradle.properties", KOTLIN_ZONE_RULES) == Zone.CONFIG

    def test_config_proguard(self):
        assert classify_file("proguard-rules.pro", KOTLIN_ZONE_RULES) == Zone.CONFIG

    def test_script_buildsrc(self):
        assert classify_file("buildSrc/src/main/kotlin/Dependencies.kt", KOTLIN_ZONE_RULES) == Zone.SCRIPT

    def test_script_scripts_dir(self):
        assert classify_file("scripts/deploy.kts", KOTLIN_ZONE_RULES) == Zone.SCRIPT

    def test_vendor_dir(self):
        assert classify_file("vendor/some/lib.kt", KOTLIN_ZONE_RULES) == Zone.VENDOR

    def test_common_test_dir(self):
        """The COMMON_ZONE_RULES /tests/ pattern also applies."""
        assert classify_file("tests/integration/SomeTest.kt", KOTLIN_ZONE_RULES) == Zone.TEST
