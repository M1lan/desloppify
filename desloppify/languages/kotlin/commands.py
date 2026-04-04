"""Kotlin detect-subcommand registry using canonical framework composition."""

from __future__ import annotations

from collections.abc import Callable

from desloppify.languages._framework.commands.base import (
    make_cmd_complexity,
    make_cmd_large,
)
from desloppify.languages._framework.commands.registry import (
    build_standard_detect_registry,
    compose_detect_registry,
    make_cmd_cycles,
    make_cmd_deps,
    make_cmd_dupes,
    make_cmd_orphaned,
)
from desloppify.languages.kotlin.detectors.deps import build_dep_graph
from desloppify.languages.kotlin.extractors import extract_functions, find_kotlin_files
from desloppify.languages.kotlin.phases import KOTLIN_COMPLEXITY_SIGNALS

cmd_large = make_cmd_large(
    find_kotlin_files,
    default_threshold=400,
    module_name=__name__,
)
cmd_complexity = make_cmd_complexity(
    find_kotlin_files,
    KOTLIN_COMPLEXITY_SIGNALS,
    default_threshold=12,
    module_name=__name__,
)
cmd_deps = make_cmd_deps(
    build_dep_graph_fn=build_dep_graph,
    empty_message="No Kotlin dependencies detected.",
    import_count_label="Imports",
    top_imports_label="Top imports",
    module_name=__name__,
)
cmd_cycles = make_cmd_cycles(build_dep_graph_fn=build_dep_graph, module_name=__name__)
cmd_orphaned = make_cmd_orphaned(
    build_dep_graph_fn=build_dep_graph,
    extensions=[".kt", ".kts"],
    extra_entry_patterns=["/main.kt", "/Application.kt", "/Main.kt", "/App.kt"],
    extra_barrel_names=set(),
    module_name=__name__,
)
cmd_dupes = make_cmd_dupes(extract_functions_fn=extract_functions, module_name=__name__)


def get_detect_commands() -> dict[str, Callable[..., None]]:
    return compose_detect_registry(
        base_registry=build_standard_detect_registry(
            cmd_deps=cmd_deps,
            cmd_cycles=cmd_cycles,
            cmd_orphaned=cmd_orphaned,
            cmd_dupes=cmd_dupes,
            cmd_large=cmd_large,
            cmd_complexity=cmd_complexity,
        ),
    )
