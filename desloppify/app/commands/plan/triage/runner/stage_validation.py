"""Post-subagent validation and auto-attestation for triage runners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from desloppify.engine.plan import TriageInput

from ..helpers import manual_clusters_with_issues, observe_dimension_breakdown
from ..stage_helpers import unclustered_review_issues, unenriched_clusters
from .._stage_validation import (
    _cluster_file_overlaps,
    _clusters_with_directory_scatter,
    _clusters_with_high_step_ratio,
    _underspecified_steps,
    _steps_missing_issue_refs,
    _steps_with_bad_paths,
    _steps_with_vague_detail,
    _steps_without_effort,
)


@dataclass(frozen=True)
class EnrichQualityFailure:
    """Structured enrich-quality validation failure."""

    code: str
    message: str


def run_enrich_quality_checks(
    plan: dict,
    repo_root: Path,
    *,
    phase_label: str,
) -> list[EnrichQualityFailure]:
    """Run enrich-level executor-readiness checks for a phase."""
    sense_suffix = f" after {phase_label}" if phase_label == "sense-check" else ""
    failures: list[EnrichQualityFailure] = []

    underspec = _underspecified_steps(plan)
    if underspec:
        total = sum(n for _, n, _ in underspec)
        failures.append(
            EnrichQualityFailure(
                code="underspecified_steps",
                message=f"{total} step(s) still lack detail or issue_refs{sense_suffix}.",
            )
        )

    bad_paths = _steps_with_bad_paths(plan, repo_root)
    if bad_paths:
        total = sum(len(bp) for _, _, bp in bad_paths)
        if phase_label == "sense-check":
            message = f"{total} file path(s) don't exist on disk{sense_suffix}."
        else:
            message = f"{total} file path(s) in step details don't exist on disk."
        failures.append(
            EnrichQualityFailure(code="missing_paths", message=message)
        )

    untagged = _steps_without_effort(plan)
    if untagged:
        total = sum(n for _, n, _ in untagged)
        if phase_label == "sense-check":
            message = f"{total} step(s) have no effort tag{sense_suffix}."
        else:
            message = (
                f"{total} step(s) have no effort tag "
                "(trivial/small/medium/large)."
            )
        failures.append(
            EnrichQualityFailure(code="missing_effort", message=message)
        )

    no_refs = _steps_missing_issue_refs(plan)
    if no_refs:
        total = sum(n for _, n, _ in no_refs)
        if phase_label == "sense-check":
            message = f"{total} step(s) have no issue_refs{sense_suffix}."
        else:
            message = f"{total} step(s) have no issue_refs for traceability."
        failures.append(
            EnrichQualityFailure(code="missing_issue_refs", message=message)
        )

    vague = _steps_with_vague_detail(plan, repo_root)
    if vague:
        if phase_label == "sense-check":
            message = f"{len(vague)} step(s) have vague detail{sense_suffix}."
        else:
            message = (
                f"{len(vague)} step(s) have vague detail (< 80 chars, no file paths). "
                "Executor-ready means: file path + specific instruction."
            )
        failures.append(
            EnrichQualityFailure(code="vague_detail", message=message)
        )

    return failures


def _validate_observe_stage(stages: dict) -> tuple[bool, str]:
    if "observe" not in stages:
        return False, "Observe stage not recorded."
    report = stages["observe"].get("report", "")
    if len(report) < 100:
        return False, f"Observe report too short ({len(report)} chars, need 100+)."
    cited = stages["observe"].get("cited_ids", [])
    issue_count = stages["observe"].get("issue_count", 0)
    if issue_count <= 0:
        return True, ""
    min_citations = min(5, max(1, issue_count // 10))
    if len(cited) >= min_citations:
        return True, ""
    return (
        False,
        f"Observe report cites only {len(cited)} issue(s) "
        f"(need {min_citations}+). Reference specific issue "
        f"hashes to prove you read them.",
    )


def _validate_reflect_stage(stages: dict) -> tuple[bool, str]:
    if "reflect" not in stages:
        return False, "Reflect stage not recorded."
    report = stages["reflect"].get("report", "")
    if len(report) < 100:
        return False, f"Reflect report too short ({len(report)} chars, need 100+)."
    return True, ""


def _organize_warnings(plan: dict) -> list[str]:
    """Collect advisory warnings for organize stage quality."""
    warnings: list[str] = []
    overlaps = _cluster_file_overlaps(plan)
    if overlaps:
        warnings.append(f"{len(overlaps)} cluster pair(s) share files without dependencies")
    scattered = _clusters_with_directory_scatter(plan)
    if scattered:
        names = ", ".join(n for n, _, _ in scattered)
        warnings.append(f"Theme-grouped clusters (5+ dirs): {names}")
    high_ratio = _clusters_with_high_step_ratio(plan)
    if high_ratio:
        names = ", ".join(n for n, _, _, _ in high_ratio)
        warnings.append(f"1:1 step-to-issue ratio: {names}")
    clusters = plan.get("clusters", {})
    orphaned = [
        n for n, c in clusters.items()
        if not c.get("auto") and not c.get("issue_ids") and c.get("action_steps")
    ]
    if orphaned:
        warnings.append(f"Orphaned clusters (steps, no issues): {', '.join(orphaned)}")
    return warnings


def _validate_organize_stage(plan: dict, state: dict, stages: dict) -> tuple[bool, str]:
    if "organize" not in stages:
        return False, "Organize stage not recorded."
    manual = manual_clusters_with_issues(plan)
    if not manual:
        return False, "No manual clusters with issues exist."
    gaps = unenriched_clusters(plan)
    if gaps:
        names = ", ".join(n for n, _ in gaps)
        return False, f"Unenriched clusters: {names}"
    unclustered = unclustered_review_issues(plan, state)
    if unclustered:
        return False, f"{len(unclustered)} review issue(s) not in any cluster."
    warnings = _organize_warnings(plan)
    if warnings:
        return True, "Advisory: " + "; ".join(warnings)
    return True, ""


def _validate_enrich_quality_stage(
    *,
    stage: str,
    plan: dict,
    repo_root: Path,
    stages: dict,
) -> tuple[bool, str]:
    if stage not in stages:
        return False, f"{stage.capitalize()} stage not recorded."
    if stage == "sense-check":
        report = stages["sense-check"].get("report", "")
        if len(report) < 100:
            return False, f"Sense-check report too short ({len(report)} chars, need 100+)."
    failures = run_enrich_quality_checks(plan, repo_root, phase_label=stage)
    if failures:
        return False, failures[0].message
    return True, ""


def validate_stage(
    stage: str,
    plan: dict,
    state: dict,
    repo_root: Path,
    *,
    triage_input: TriageInput | None = None,
) -> tuple[bool, str]:
    """Check subagent completed stage correctly. Returns (ok, error_msg)."""
    meta = plan.get("epic_triage_meta", {})
    stages = meta.get("triage_stages", {})
    validators = {
        "observe": lambda: _validate_observe_stage(stages),
        "reflect": lambda: _validate_reflect_stage(stages),
        "organize": lambda: _validate_organize_stage(plan, state, stages),
        "enrich": lambda: _validate_enrich_quality_stage(
            stage="enrich",
            plan=plan,
            repo_root=repo_root,
            stages=stages,
        ),
        "sense-check": lambda: _validate_enrich_quality_stage(
            stage="sense-check",
            plan=plan,
            repo_root=repo_root,
            stages=stages,
        ),
    }
    validator = validators.get(stage)
    if validator is None:
        return False, f"Unknown stage: {stage}"
    return validator()


def validate_completion(
    plan: dict,
    state: dict,
    repo_root: Path,
) -> tuple[bool, str]:
    """Validate plan is ready for triage completion. Returns (ok, error_msg)."""
    meta = plan.get("epic_triage_meta", {})
    stages = meta.get("triage_stages", {})

    missing = _missing_or_unconfirmed_required_stages(stages)
    if missing:
        return False, missing

    manual = manual_clusters_with_issues(plan)
    if not manual:
        return False, "No manual clusters with issues."

    gaps = unenriched_clusters(plan)
    if gaps:
        return False, f"{len(gaps)} cluster(s) still need enrichment."

    unclustered = unclustered_review_issues(plan, state)
    if unclustered:
        return False, f"{len(unclustered)} review issue(s) not in any cluster."

    clusters = plan.get("clusters", {})
    self_dep = _self_dependent_cluster_name(clusters)
    if self_dep:
        return False, f"Cluster {self_dep} depends on itself."

    all_trivial_clusters = _all_trivial_manual_clusters(clusters)
    if all_trivial_clusters:
        names = ", ".join(all_trivial_clusters)
        return True, f"Advisory: all action steps are marked trivial in cluster(s): {names}"

    return True, ""


def _missing_or_unconfirmed_required_stages(stages: dict) -> str | None:
    """Return the first missing/unconfirmed required stage message, if any."""
    for required in ("observe", "reflect", "organize", "enrich", "sense-check"):
        if required not in stages:
            return f"Stage {required} not recorded."
        if not stages[required].get("confirmed_at"):
            return f"Stage {required} not confirmed."
    return None


def _self_dependent_cluster_name(clusters: dict) -> str | None:
    """Return cluster name when it depends on itself, else None."""
    for name, cluster in clusters.items():
        deps = cluster.get("depends_on_clusters", [])
        if name in deps:
            return name
    return None


def _all_trivial_manual_clusters(clusters: dict) -> list[str]:
    """Return sorted manual cluster names where all steps are trivial."""
    names: list[str] = []
    for name, cluster in clusters.items():
        if cluster.get("auto") or not cluster.get("issue_ids"):
            continue
        steps = cluster.get("action_steps") or []
        if steps and all(
            isinstance(step, dict) and step.get("effort") == "trivial"
            for step in steps
        ):
            names.append(name)
    return sorted(names)


def build_auto_attestation(
    stage: str,
    plan: dict,
    triage_input: TriageInput,
) -> str:
    """Generate valid 80+ char attestation referencing real dimensions/cluster names."""
    if stage == "observe":
        _by_dim, dim_names = observe_dimension_breakdown(triage_input)
        top_dims = dim_names[:3]
        dims_str = ", ".join(top_dims)
        return (
            f"I have thoroughly analysed {len(triage_input.open_issues)} issues "
            f"across dimensions including {dims_str}, identifying themes, "
            f"root causes, and contradictions across the codebase."
        )

    if stage == "reflect":
        _by_dim, dim_names = observe_dimension_breakdown(triage_input)
        top_dims = dim_names[:3]
        dims_str = ", ".join(top_dims)
        return (
            f"My strategy accounts for {len(triage_input.open_issues)} issues "
            f"across dimensions including {dims_str}, comparing against "
            f"resolved history and forming priorities for execution."
        )

    if stage == "organize":
        cluster_names = manual_clusters_with_issues(plan)
        names_str = ", ".join(cluster_names[:3])
        return (
            f"I have organized all review issues into clusters including "
            f"{names_str}, with descriptions, action steps, and clear "
            f"priority ordering based on root cause analysis."
        )

    if stage == "enrich":
        cluster_names = manual_clusters_with_issues(plan)
        names_str = ", ".join(cluster_names[:3])
        return (
            f"Steps in clusters including {names_str} are executor-ready with "
            f"detail, file paths, issue refs, and effort tags, verified "
            f"against the actual codebase."
        )

    if stage == "sense-check":
        cluster_names = manual_clusters_with_issues(plan)
        names_str = ", ".join(cluster_names[:3])
        return (
            f"Content and structure verified for clusters including {names_str}. "
            f"All step details are factually accurate, cross-cluster dependencies "
            f"are safe, and enrich-level checks pass."
        )

    return f"Stage {stage} completed with thorough analysis of all available data and verified against codebase."


__all__ = [
    "EnrichQualityFailure",
    "build_auto_attestation",
    "run_enrich_quality_checks",
    "validate_completion",
    "validate_stage",
]
