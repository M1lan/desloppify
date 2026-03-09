"""Flow execution for plan resolve command."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class PlanResolveDeps:
    colorize_fn: callable
    resolve_synthetic_ids_fn: callable
    load_plan_fn: callable
    blocked_triage_stages_fn: callable
    has_triage_in_queue_fn: callable
    inject_triage_stages_fn: callable
    save_plan_fn: callable
    append_log_entry_fn: callable
    purge_ids_fn: callable
    auto_complete_steps_fn: callable
    state_path_fn: callable
    load_state_fn: callable
    validate_note_length_fn: callable
    show_note_length_requirement_fn: callable
    validate_attestation_fn: callable
    show_attestation_requirement_fn: callable
    command_runtime_fn: callable
    check_cluster_guard_fn: callable
    cmd_resolve_fn: callable
    log_best_effort_failure_fn: callable
    logger: object
    workflow_score_checkpoint_id: str
    workflow_create_plan_id: str
    attest_example: str
    plan_load_exceptions: tuple[type[BaseException], ...]


def run_plan_resolve(args: argparse.Namespace, *, deps: PlanResolveDeps) -> None:
    """Mark issues as fixed — delegates to cmd_resolve for rich UX."""
    patterns: list[str] = getattr(args, "patterns", [])
    attestation: str | None = getattr(args, "attest", None)
    note: str | None = getattr(args, "note", None)

    if getattr(args, "confirm", False):
        if not note:
            print(deps.colorize_fn("  --confirm requires --note to describe what you did.", "red"))
            return
        attestation = f"I have actually {note} and I am not gaming the score."
        args.attest = attestation

    synthetic_ids, real_patterns = deps.resolve_synthetic_ids_fn(patterns)
    if synthetic_ids:
        plan = deps.load_plan_fn()

        blocked_map = deps.blocked_triage_stages_fn(plan)
        for sid in synthetic_ids:
            if sid in blocked_map:
                deps_text = ", ".join(dep.replace("triage::", "") for dep in blocked_map[sid])
                print(deps.colorize_fn(f"  Cannot resolve {sid} — blocked by: {deps_text}", "red"))
                print(
                    deps.colorize_fn(
                        "  Complete those stages first, or use --force-resolve to override.",
                        "dim",
                    )
                )
                if not getattr(args, "force_resolve", False):
                    return

        gated_ids = [
            sid
            for sid in synthetic_ids
            if sid in {deps.workflow_score_checkpoint_id, deps.workflow_create_plan_id}
        ]
        if gated_ids:
            force = getattr(args, "force_resolve", False)
            meta = plan.get("epic_triage_meta", {})
            triage_ever_completed = bool(meta.get("last_completed_at"))
            if triage_ever_completed:
                missing: set[str] = set()
            else:
                confirmed_stages = set(meta.get("triage_stages", {}).keys())
                required_stages = {"observe", "reflect", "organize", "enrich", "commit"}
                missing = required_stages - confirmed_stages

            if missing and not force:
                if not deps.has_triage_in_queue_fn(plan):
                    deps.inject_triage_stages_fn(plan)
                    meta.setdefault("triage_stages", {})
                    plan["epic_triage_meta"] = meta
                    deps.save_plan_fn(plan)

                stage_order = ["observe", "reflect", "organize", "enrich", "commit"]
                next_stage = next((stage for stage in stage_order if stage in missing), "observe")

                for wid in gated_ids:
                    print(deps.colorize_fn(f"  Cannot resolve {wid} — triage not complete.", "red"))
                print()

                if next_stage == "observe":
                    print(
                        deps.colorize_fn(
                            "  You must analyze the findings before resolving this.",
                            "yellow",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            "  Start by examining themes, root causes, and contradictions:",
                            "dim",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            '    desloppify plan triage --stage observe --report "..."',
                            "dim",
                        )
                    )
                    print()
                    print(
                        deps.colorize_fn(
                            "  The report must be 100+ chars describing what you found.",
                            "dim",
                        )
                    )
                elif next_stage == "reflect":
                    print(
                        deps.colorize_fn(
                            "  Observe is done. Now compare against previously completed work:",
                            "yellow",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            '    desloppify plan triage --stage reflect --report "..."',
                            "dim",
                        )
                    )
                    print()
                    print(
                        deps.colorize_fn(
                            "  The report must mention recurring dimensions if any exist.",
                            "dim",
                        )
                    )
                elif next_stage == "organize":
                    print(
                        deps.colorize_fn(
                            "  Reflect is done. Now create clusters and prioritize:",
                            "yellow",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            '    desloppify plan cluster create <name> --description "..."',
                            "dim",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            "    desloppify plan cluster add <name> <issue-patterns>",
                            "dim",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            '    desloppify plan cluster update <name> --steps "step1" "step2"',
                            "dim",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            '    desloppify plan triage --stage organize --report "..."',
                            "dim",
                        )
                    )
                    print()
                    print(
                        deps.colorize_fn(
                            "  All manual clusters must have descriptions and action_steps.",
                            "dim",
                        )
                    )
                elif next_stage == "enrich":
                    print(
                        deps.colorize_fn(
                            "  Organize is done. Now enrich steps with detail and issue refs:",
                            "yellow",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            '    desloppify plan cluster update <name> --update-step N --detail "sub-details"',
                            "dim",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            '    desloppify plan triage --stage enrich --report "..."',
                            "dim",
                        )
                    )
                elif next_stage == "commit":
                    print(
                        deps.colorize_fn(
                            "  Enrich is done. Finalize the execution plan:",
                            "yellow",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            '    desloppify plan triage --complete --strategy "..."',
                            "dim",
                        )
                    )

                print()
                print(deps.colorize_fn(f"  Remaining stages: {', '.join(sorted(missing))}", "dim"))
                print(
                    deps.colorize_fn(
                        "  To skip triage: --force-resolve --note 'reason for skipping triage'",
                        "dim",
                    )
                )

                deps.append_log_entry_fn(
                    plan,
                    "workflow_blocked",
                    issue_ids=gated_ids,
                    actor="user",
                    note=note,
                    detail={"missing_stages": sorted(missing), "next_stage": next_stage},
                )
                deps.save_plan_fn(plan)
                return

            if missing and force:
                if not note or len(note.strip()) < 50:
                    print(
                        deps.colorize_fn(
                            "  --force-resolve still requires --note (min 50 chars) explaining "
                            "why you're skipping triage.",
                            "red",
                        )
                    )
                    return
                print(deps.colorize_fn("  WARNING: Skipping triage requirement — this is logged.", "yellow"))
                deps.append_log_entry_fn(
                    plan,
                    "workflow_force_skip",
                    issue_ids=gated_ids,
                    actor="user",
                    note=note,
                    detail={"forced": True, "missing_stages": sorted(missing)},
                )
                deps.save_plan_fn(plan)

        if gated_ids:
            scan_count_at_start = plan.get("scan_count_at_plan_start")
            force = getattr(args, "force_resolve", False)
            if scan_count_at_start is not None:
                resolved_state_path = deps.state_path_fn(args)
                state_data = deps.load_state_fn(resolved_state_path)
                current_scan_count = int(state_data.get("scan_count", 0) or 0)
                scan_ran = current_scan_count > scan_count_at_start
                scan_skipped = plan.get("scan_gate_skipped", False)

                if not scan_ran and not scan_skipped and not force:
                    for wid in gated_ids:
                        print(
                            deps.colorize_fn(
                                f"  Cannot resolve {wid} — no scan has run this cycle.",
                                "red",
                            )
                        )
                    print()
                    print(
                        deps.colorize_fn(
                            "  You must run a scan before resolving workflow items:",
                            "yellow",
                        )
                    )
                    print(deps.colorize_fn("    desloppify scan", "dim"))
                    print()
                    print(
                        deps.colorize_fn(
                            f"  Scans at cycle start: {scan_count_at_start}  "
                            f"Current: {current_scan_count}",
                            "dim",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            "  To skip scan requirement: desloppify plan scan-gate --skip "
                            '--note "reason for skipping scan"',
                            "dim",
                        )
                    )
                    print(
                        deps.colorize_fn(
                            "  Or use: --force-resolve --note 'reason for skipping'",
                            "dim",
                        )
                    )

                    deps.append_log_entry_fn(
                        plan,
                        "scan_gate_blocked",
                        issue_ids=gated_ids,
                        actor="user",
                        note=note,
                        detail={
                            "scan_count_at_start": scan_count_at_start,
                            "current_scan_count": current_scan_count,
                        },
                    )
                    deps.save_plan_fn(plan)
                    return

        deps.purge_ids_fn(plan, synthetic_ids)
        step_messages = deps.auto_complete_steps_fn(plan)
        for msg in step_messages:
            print(deps.colorize_fn(msg, "green"))
        deps.append_log_entry_fn(plan, "done", issue_ids=synthetic_ids, actor="user", note=note)
        deps.save_plan_fn(plan)
        for sid in synthetic_ids:
            print(deps.colorize_fn(f"  Resolved: {sid}", "green"))
        if not real_patterns:
            return
        patterns = real_patterns
        args.patterns = patterns

    if not deps.validate_note_length_fn(note):
        deps.show_note_length_requirement_fn(note)
        return

    if not deps.validate_attestation_fn(attestation):
        deps.show_attestation_requirement_fn("Plan resolve", attestation, deps.attest_example)
        return

    plan: dict | None = None
    try:
        runtime = deps.command_runtime_fn(args)
        state = runtime.state
        plan = deps.load_plan_fn()
        if deps.check_cluster_guard_fn(patterns, plan, state):
            return
    except deps.plan_load_exceptions:
        plan = None

    try:
        if plan is None:
            plan = deps.load_plan_fn()
        clusters = plan.get("clusters", {})
        cluster_name = next((pattern for pattern in patterns if pattern in clusters), None)
        deps.append_log_entry_fn(
            plan,
            "done",
            issue_ids=patterns,
            cluster_name=cluster_name,
            actor="user",
            note=note,
        )
        deps.save_plan_fn(plan)
    except deps.plan_load_exceptions as exc:
        deps.log_best_effort_failure_fn(deps.logger, "append plan resolve log entry", exc)
        print(deps.colorize_fn(f"  Note: unable to append plan resolve log entry ({exc}).", "dim"))

    resolve_args = argparse.Namespace(
        status="fixed",
        patterns=patterns,
        note=note,
        attest=attestation,
        confirm_batch_wontfix=False,
        force_resolve=bool(getattr(args, "force_resolve", False)),
        state=getattr(args, "state", None),
        lang=getattr(args, "lang", None),
        path=getattr(args, "path", None),
        exclude=getattr(args, "exclude", None),
    )

    deps.cmd_resolve_fn(resolve_args)


__all__ = ["PlanResolveDeps", "run_plan_resolve"]
