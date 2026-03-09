"""Resolve command handler for plan overrides."""

from __future__ import annotations

import argparse
import logging

from desloppify import state as state_mod
from desloppify.app.commands.helpers.attestation import (
    show_attestation_requirement,
    show_note_length_requirement,
    validate_attestation,
    validate_note_length,
)
from desloppify.app.commands.helpers.runtime import command_runtime
from desloppify.app.commands.helpers.state import state_path
from desloppify.app.commands.plan.triage.helpers import (
    has_triage_in_queue,
    inject_triage_stages,
)
from desloppify.app.commands.resolve.cmd import cmd_resolve
from desloppify.base.exception_sets import PLAN_LOAD_EXCEPTIONS
from desloppify.base.output.fallbacks import log_best_effort_failure
from desloppify.base.output.terminal import colorize
from desloppify.engine._work_queue.core import ATTEST_EXAMPLE
from desloppify.engine.plan import (
    WORKFLOW_CREATE_PLAN_ID,
    WORKFLOW_SCORE_CHECKPOINT_ID,
    append_log_entry,
    auto_complete_steps,
    load_plan,
    purge_ids,
    save_plan,
)

from .override_resolve_flow import PlanResolveDeps, run_plan_resolve
from .override_resolve_helpers import (
    blocked_triage_stages,
    check_cluster_guard,
    resolve_synthetic_ids,
)

logger = logging.getLogger(__name__)


def cmd_plan_resolve(args: argparse.Namespace) -> None:
    """Mark issues as fixed and delegate to resolve command UX."""
    deps = PlanResolveDeps(
        colorize_fn=colorize,
        resolve_synthetic_ids_fn=resolve_synthetic_ids,
        load_plan_fn=load_plan,
        blocked_triage_stages_fn=blocked_triage_stages,
        has_triage_in_queue_fn=has_triage_in_queue,
        inject_triage_stages_fn=inject_triage_stages,
        save_plan_fn=save_plan,
        append_log_entry_fn=append_log_entry,
        purge_ids_fn=purge_ids,
        auto_complete_steps_fn=auto_complete_steps,
        state_path_fn=state_path,
        load_state_fn=state_mod.load_state,
        validate_note_length_fn=validate_note_length,
        show_note_length_requirement_fn=show_note_length_requirement,
        validate_attestation_fn=validate_attestation,
        show_attestation_requirement_fn=show_attestation_requirement,
        command_runtime_fn=command_runtime,
        check_cluster_guard_fn=check_cluster_guard,
        cmd_resolve_fn=cmd_resolve,
        log_best_effort_failure_fn=log_best_effort_failure,
        logger=logger,
        workflow_score_checkpoint_id=WORKFLOW_SCORE_CHECKPOINT_ID,
        workflow_create_plan_id=WORKFLOW_CREATE_PLAN_ID,
        attest_example=ATTEST_EXAMPLE,
        plan_load_exceptions=PLAN_LOAD_EXCEPTIONS,
    )
    run_plan_resolve(args, deps=deps)


__all__ = ["cmd_plan_resolve"]
