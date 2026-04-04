"""Kotlin dependency graph builder (stub).

Kotlin import resolution is delegated to tree-sitter via the generic
framework.  This stub provides the contract for full plugin registration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_dep_graph(
    path: Path,
    roslyn_cmd: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Build Kotlin dependency graph -- stub returning empty dict."""
    del path, roslyn_cmd
    return {}
