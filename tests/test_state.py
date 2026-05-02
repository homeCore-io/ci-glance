from ci_glance.state import derive_state, normalize_conclusion


def _h(*statuses):
    return [{"status": s} for s in statuses]


def test_empty_history_returns_dash():
    assert derive_state([], flaky_threshold=2) == "—"


def test_only_pads_returns_dash():
    assert derive_state(_h("none", "none"), flaky_threshold=2) == "—"


def test_all_ok():
    assert derive_state(_h(*(["ok"] * 20)), flaky_threshold=2) == "OK"


def test_last_fail_is_fail():
    assert derive_state(_h("ok", "ok", "fail"), flaky_threshold=2) == "FAIL"


def test_flaky_when_recent_ok_with_failures_in_history():
    history = _h("ok", "fail", "ok", "fail", "ok", "fail", "ok")
    assert derive_state(history, flaky_threshold=2) == "FLAKY"


def test_below_flaky_threshold_is_ok():
    assert derive_state(_h("ok", "fail", "ok", "ok"), flaky_threshold=2) == "OK"


def test_in_progress_skipped_when_picking_last():
    history = _h("ok", "ok", "fail") + [{"status": "in_progress"}]
    assert derive_state(history, flaky_threshold=2) == "FAIL"


def test_pads_skipped_when_picking_last():
    history = _h("none", "none", "ok")
    assert derive_state(history, flaky_threshold=2) == "OK"


def test_normalize_conclusion():
    assert normalize_conclusion("success") == "ok"
    assert normalize_conclusion("failure") == "fail"
    assert normalize_conclusion("timed_out") == "fail"
    assert normalize_conclusion("startup_failure") == "fail"
    assert normalize_conclusion("cancelled") == "cancelled"
    assert normalize_conclusion("skipped") == "cancelled"
    assert normalize_conclusion(None) == "in_progress"
    assert normalize_conclusion("something_unknown") == "cancelled"
