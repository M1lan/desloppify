"""Regression tests for cross-platform state persistence."""

from __future__ import annotations

import importlib


def test_state_lock_imports_and_round_trips_on_current_platform(tmp_path):
    persistence_mod = importlib.import_module("desloppify.engine._state.persistence")

    state_path = tmp_path / "state.json"
    with persistence_mod.state_lock(state_path) as state:
        state["scan_count"] = 3

    loaded = persistence_mod.load_state(state_path)
    assert loaded["scan_count"] == 3
