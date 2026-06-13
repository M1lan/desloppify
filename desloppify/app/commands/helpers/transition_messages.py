"""Emit user-configured messages at lifecycle phase transitions."""

from __future__ import annotations

import json as _json
import logging
import os as _os
import urllib.error as _urlerr
import urllib.request as _urlreq

from desloppify.base.config import load_config
from desloppify.base.output.user_message import print_user_message
from desloppify.engine._plan.refresh_lifecycle import user_facing_mode
logger = logging.getLogger(__name__)

# Phases that are NOT postflight — everything else counts as postflight.
_NON_POSTFLIGHT = frozenset({"execute", "scan"})

_FRAUMES_PORT_FILE = _os.path.expanduser("~/.fraumes/control_api.port")


def _fraumes_available() -> bool:
    """Check if Fraumes integration is enabled in config."""
    try:
        config = load_config()
    except (OSError, ValueError):
        return False
    return bool(config.get("fraumes_enabled", False))


def _fraumes_port() -> int:
    try:
        with open(_FRAUMES_PORT_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 47823


def _fraumes_get(path: str) -> dict:
    """GET a Fraumes control API endpoint. Stdlib-only, no deps."""
    url = f"http://127.0.0.1:{_fraumes_port()}{path}"
    req = _urlreq.Request(url, method="GET",
                          headers={"X-Fraumes-Control": "1"})
    try:
        with _urlreq.urlopen(req, timeout=5) as resp:
            return _json.loads(resp.read())
    except _urlerr.HTTPError as e:
        return _json.loads(e.read())
    except (_urlerr.URLError, OSError) as e:
        return {"error": str(e)}


def _fraumes_send_message(text: str, mode: str = "queue") -> dict:
    """Send a message/command to the running Fraumes agent. Stdlib-only, no deps."""
    url = f"http://127.0.0.1:{_fraumes_port()}/sessions/_any/message"
    data = _json.dumps({"text": text, "mode": mode}).encode()
    req = _urlreq.Request(url, data=data, method="POST",
                          headers={"Content-Type": "application/json",
                                   "X-Fraumes-Control": "1"})
    try:
        with _urlreq.urlopen(req, timeout=5) as resp:
            return _json.loads(resp.read())
    except _urlerr.HTTPError as e:
        return _json.loads(e.read())
    except (_urlerr.URLError, OSError) as e:
        return {"error": str(e)}


def _resolve_fraumes_model(phase: str, fraumes_models: dict) -> str | None:
    """Resolve a phase to a 'provider:model' string from fraumes_models config.

    Lookup: exact phase → 'review' (fallback for non-execute).
    Returns None if no model is configured for this phase.
    """
    spec = fraumes_models.get(phase)
    if not spec and phase not in _NON_POSTFLIGHT:
        spec = fraumes_models.get("review")
    return spec or None


def _switch_fraumes_model(phase: str) -> bool:
    """Switch the running Fraumes agent's model based on the phase.

    Reads model mapping from fraumes_models in config.json.
    Returns True if switch was triggered.
    """
    if not _fraumes_available():
        return False

    try:
        config = load_config()
    except (OSError, ValueError):
        return False

    fraumes_models = config.get("fraumes_models", {})
    if not fraumes_models:
        return False

    spec = _resolve_fraumes_model(phase, fraumes_models)
    if not spec:
        return False

    try:
        result = _fraumes_send_message(f"/model {spec}", mode="interrupt")
        if result.get("success"):
            _fraumes_send_message("continue", mode="queue")
            print(f"🔄 Fraumes model → {spec} (mode: {user_facing_mode(phase)})")
            return True
        else:
            logger.debug("Fraumes model switch failed: %s", result.get("error", ""))
            return False
    except Exception as exc:
        logger.debug("Fraumes model switch skipped: %s", exc)
        return False


_AUTOREPLY_PROMPT = (
    "You are an autonomous code repair agent working through a desloppify queue. "
    "After each task, run the next desloppify command as instructed. "
    "Do not stop or ask for confirmation — keep going until the queue is empty."
)


def _ensure_fraumes_autoreply() -> None:
    """Enable autoreply on the Fraumes session if not already active.

    Checks the session state via GET /sessions/_any. If autoreply is
    already enabled, does nothing — so it's safe to call on every
    phase transition without clobbering an existing config.
    """
    if not _fraumes_available():
        return
    try:
        info = _fraumes_get("/sessions/_any")
        if info.get("autoreply", {}).get("enabled"):
            return
        _fraumes_send_message(
            f"/autoreply {_AUTOREPLY_PROMPT}",
            mode="queue",
        )
        logger.debug("Fraumes autoreply enabled for desloppify session")
    except Exception as exc:
        logger.debug("Fraumes autoreply check skipped: %s", exc)


def emit_transition_message(new_phase: str) -> bool:
    """Print a transition message if one is configured for *new_phase*.

    Lookup order: exact phase → coarse phase → ``postflight`` (if the
    phase is not execute/scan).

    Also triggers a Fraumes model switch if the control API is available.

    Returns True if a message was emitted.
    """
    # Ensure autoreply is enabled so the agent keeps working autonomously
    _ensure_fraumes_autoreply()

    # Switch Fraumes model for this phase (best-effort, non-blocking)
    _switch_fraumes_model(new_phase)

    try:
        config = load_config()
    except (OSError, ValueError) as exc:
        logger.debug("transition message skipped (config load): %s", exc)
        return False

    messages = config.get("transition_messages")
    if not isinstance(messages, dict) or not messages:
        return False

    # Try exact phase first, then postflight fallback.
    text = messages.get(new_phase)
    if text is None and new_phase not in _NON_POSTFLIGHT:
        text = messages.get("postflight")

    if not isinstance(text, str) or not text.strip():
        return False

    clean = text.strip()
    print(f"\n{'─' * 60}")
    print(f"TRANSITION INSTRUCTION — entering {user_facing_mode(new_phase)} mode")
    print(clean)
    print(f"{'─' * 60}")
    print_user_message(f"Hey, did you see the above? Please act on this: {clean}")
    return True


__all__ = ["emit_transition_message"]
