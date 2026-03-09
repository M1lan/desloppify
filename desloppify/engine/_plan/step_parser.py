"""Parse and format numbered-steps text files for ActionStep data."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from desloppify.engine._plan.schema import ActionStep

_STEP_HEADER_RE = re.compile(r"^(\d+)\.\s+(.+)$")
_REFS_RE = re.compile(r"^\s*Refs?:\s*(.+)$", re.IGNORECASE)


def _flush_step(
    *,
    steps: list[ActionStep],
    current: ActionStep | None,
    detail_lines: list[str],
) -> tuple[ActionStep | None, list[str]]:
    """Finalize current step into ``steps`` and reset parser state."""
    if current is None:
        return None, []
    detail = "\n".join(detail_lines).strip()
    if detail:
        current["detail"] = detail
    steps.append(current)
    return None, []


def _consume_indented_line(
    line: str,
    *,
    current: ActionStep,
    detail_lines: list[str],
) -> None:
    """Parse an indented line as either refs metadata or detail text."""
    ref_match = _REFS_RE.match(line)
    if ref_match:
        refs = [ref.strip() for ref in ref_match.group(1).split(",") if ref.strip()]
        current.setdefault("issue_refs", []).extend(refs)
        return
    detail_lines.append(line.strip())


def _format_step_lines(index: int, step: str | dict) -> list[str]:
    """Render a single step block into numbered text lines."""
    if isinstance(step, str):
        return [f"{index}. {step}", ""]
    if not isinstance(step, dict):
        return [""]

    lines: list[str] = []
    title = step.get("title", "")
    done = step.get("done", False)
    prefix = "[x] " if done else ""
    lines.append(f"{index}. {prefix}{title}")

    detail = step.get("detail", "")
    if detail:
        for detail_line in detail.splitlines():
            lines.append(f"   {detail_line}")

    refs = step.get("issue_refs", [])
    if refs:
        lines.append(f"   Refs: {', '.join(refs)}")

    lines.append("")
    return lines


def _step_title_from_header(line: str) -> str | None:
    match = _STEP_HEADER_RE.match(line)
    if match is None:
        return None
    return match.group(2).strip()


def _consume_non_header_line(
    line: str,
    *,
    current: ActionStep,
    detail_lines: list[str],
) -> None:
    if line and (line[0] == " " or line[0] == "\t"):
        _consume_indented_line(line, current=current, detail_lines=detail_lines)
        return
    if line.strip() == "" and detail_lines:
        detail_lines.append("")


def parse_steps_file(text: str) -> list[ActionStep]:
    """Parse a numbered-steps text format into ActionStep dicts.

    Format::

        1. Step title here
           Detail lines indented by 2+ spaces.
           More detail.
           Refs: abc123, def456

        2. Another step
           Its detail block.
    """
    steps: list[ActionStep] = []
    current: ActionStep | None = None
    detail_lines: list[str] = []

    for line in text.splitlines():
        title = _step_title_from_header(line)
        if title is not None:
            current, detail_lines = _flush_step(
                steps=steps,
                current=current,
                detail_lines=detail_lines,
            )
            current = {"title": title}
            continue

        if current is None:
            continue

        _consume_non_header_line(
            line,
            current=current,
            detail_lines=detail_lines,
        )

    current, detail_lines = _flush_step(
        steps=steps,
        current=current,
        detail_lines=detail_lines,
    )
    return steps


def format_steps(steps: list[str | dict]) -> str:
    """Format a list of ActionStep dicts (or legacy strings) into numbered-steps text.

    Round-trips with ``parse_steps_file``: ``parse_steps_file(format_steps(steps))``
    reproduces the same data (modulo whitespace normalization).
    """
    lines: list[str] = []
    for i, step in enumerate(steps, 1):
        lines.extend(_format_step_lines(i, step))
    return "\n".join(lines)


def normalize_step(step: str | dict) -> dict:
    """Ensure a step is an ActionStep dict. Wraps plain strings."""
    if isinstance(step, dict):
        return step
    return {"title": step}


def step_summary(step: str | dict) -> str:
    """Return a one-line summary of a step for display."""
    if isinstance(step, str):
        return step
    return step.get("title", "")


__all__ = [
    "format_steps",
    "normalize_step",
    "parse_steps_file",
    "step_summary",
]
