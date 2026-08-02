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


# ── FLAKY is not permanent ──────────────────────────────────────────────────
#
# Counting every failure in the window meant two reds stuck to a repo forever.
# Fourteen of fifteen repos on the live board read FLAKY, several of them
# green for their last dozen runs, so the column carried no signal at all.


def test_a_green_streak_clears_an_old_flaky():
    history = _h("fail", "fail", *(["ok"] * 6))
    assert derive_state(history, flaky_threshold=2, recovery_streak=5) == "OK"


def test_a_recent_failure_keeps_it_flaky():
    # Green tail, but not long enough to have earned it back.
    history = _h(*(["ok"] * 10), "fail", "fail", "ok", "ok")
    assert derive_state(history, flaky_threshold=2, recovery_streak=5) == "FLAKY"


def test_the_streak_must_be_unbroken():
    history = _h("fail", "fail", "ok", "ok", "fail", "ok", "ok", "ok")
    assert derive_state(history, flaky_threshold=2, recovery_streak=5) == "FLAKY"


def test_a_red_last_run_is_still_fail_however_long_the_history():
    history = _h(*(["ok"] * 19), "fail")
    assert derive_state(history, flaky_threshold=2, recovery_streak=5) == "FAIL"


def test_too_few_runs_to_prove_recovery_stays_flaky():
    # Three greens cannot satisfy a five-run streak; do not round up.
    history = _h("fail", "fail", "ok", "ok", "ok")
    assert derive_state(history, flaky_threshold=2, recovery_streak=5) == "FLAKY"


def test_zero_streak_restores_the_never_forget_behaviour():
    history = _h("fail", "fail", *(["ok"] * 18))
    assert derive_state(history, flaky_threshold=2, recovery_streak=0) == "FLAKY"


def test_pads_and_in_progress_do_not_break_the_streak():
    # A run still building sits between the greens; it is not a failure and
    # must not count as one, nor pad the streak out.
    history = [
        {"status": "fail"}, {"status": "fail"},
        {"status": "ok"}, {"status": "ok"}, {"status": "in_progress"},
        {"status": "ok"}, {"status": "ok"}, {"status": "ok"},
    ]
    assert derive_state(history, flaky_threshold=2, recovery_streak=5) == "OK"
