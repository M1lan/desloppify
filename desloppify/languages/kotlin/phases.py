"""Kotlin detector phase runners."""

from __future__ import annotations

from pathlib import Path

from desloppify.base.output.terminal import log
from desloppify.engine.detectors.base import ComplexitySignal
from desloppify.languages._framework.base.shared_phases import run_structural_phase
from desloppify.languages._framework.base.types import LangRuntimeContract
from desloppify.state_io import Issue

KOTLIN_COMPLEXITY_SIGNALS = [
    ComplexitySignal(
        "when branches",
        r"\bwhen\b",
        weight=1,
        threshold=15,
    ),
    ComplexitySignal(
        "if/else branches",
        r"\b(?:if|else\s+if|else)\b",
        weight=1,
        threshold=25,
    ),
    ComplexitySignal(
        "for/while loops",
        r"\b(?:for|while)\b",
        weight=1,
        threshold=15,
    ),
    ComplexitySignal(
        "try/catch",
        r"\b(?:try|catch)\b",
        weight=1,
        threshold=10,
    ),
    ComplexitySignal(
        "coroutine launches",
        r"\b(?:launch|async|runBlocking|withContext)\b",
        weight=2,
        threshold=5,
    ),
    ComplexitySignal(
        "Flow operators",
        r"\.(?:map|flatMapLatest|combine|zip|collect)\b",
        weight=1,
        threshold=10,
    ),
    ComplexitySignal(
        "TODOs",
        r"(?m)//\s*(?:TODO|FIXME|HACK|XXX)",
        weight=2,
        threshold=0,
    ),
]


def phase_structural(path: Path, lang: LangRuntimeContract) -> tuple[list[Issue], dict[str, int]]:
    """Run structural detectors (large/complexity/flat directories)."""
    return run_structural_phase(
        path,
        lang,
        complexity_signals=KOTLIN_COMPLEXITY_SIGNALS,
        log_fn=log,
    )
