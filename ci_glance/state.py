"""Status normalization and dashboard state derivation.

Pure functions, no I/O. The most testable layer of the app.
"""
from typing import List, Optional

# Map GitHub run conclusion -> our internal status.
_CONCLUSION_MAP = {
    "success": "ok",
    "failure": "fail",
    "timed_out": "fail",
    "startup_failure": "fail",
    "cancelled": "cancelled",
    "skipped": "cancelled",
    "neutral": "cancelled",
    "action_required": "cancelled",
    "stale": "cancelled",
    None: "in_progress",  # null conclusion = run not yet complete
}

COMPLETED = ("ok", "fail", "cancelled")


def normalize_conclusion(conclusion: Optional[str]) -> str:
    """Map a GitHub Actions run conclusion to one of:
    'ok' | 'fail' | 'cancelled' | 'in_progress'.
    Unknown values fall back to 'cancelled' (amber, "not sure").
    """
    return _CONCLUSION_MAP.get(conclusion, "cancelled")


def derive_state(history: List[dict], flaky_threshold: int) -> str:
    """Compute the dashboard state cell from a sparkline history.

    `history` is oldest -> newest. Pad entries (status == 'none') and
    in-progress runs are ignored when picking the most recent state.
    Returns one of: 'OK' | 'FAIL' | 'FLAKY' | '—'.
    """
    completed = [h for h in history if h.get("status") in COMPLETED]
    if not completed:
        return "—"

    last = completed[-1]["status"]
    fail_count = sum(1 for h in completed if h["status"] == "fail")

    if last == "fail":
        return "FAIL"
    if fail_count >= flaky_threshold:
        return "FLAKY"
    return "OK"
