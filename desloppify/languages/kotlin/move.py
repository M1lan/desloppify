"""Kotlin move helpers for file relocation scaffolding."""

from __future__ import annotations


def find_replacements(
    source_abs: str, dest_abs: str, graph: dict
) -> dict[str, list[tuple[str, str]]]:
    """Kotlin import rewrites are not implemented yet."""
    del source_abs, dest_abs, graph
    return {}


def find_self_replacements(
    source_abs: str, dest_abs: str, graph: dict
) -> list[tuple[str, str]]:
    """No self-import rewrites for Kotlin at this time."""
    del source_abs, dest_abs, graph
    return []
