"""Publishing an empty board over a working one is worse than not publishing.

An expired DASH_TOKEN made every request 401. generate.py counted the errors,
ignored the count, rendered a page of dashes, and returned 0 — so the deploy
succeeded and replaced a good dashboard with an empty one that looked like a
healthy estate with no repos in it.
"""
import generate


def _fake_fetch(results):
    """results: list of (runs, err) returned in order."""
    calls = iter(results)

    def fetch(owner, repo, workflow_file, per_page=20, token=None, timeout=10):
        return next(calls)

    return fetch


def _run(monkeypatch, tmp_path, results):
    # main() is configured by environment, not argv.
    monkeypatch.setattr(generate, "fetch_runs", _fake_fetch(results))
    monkeypatch.setenv("CI_GLANCE_OUT", str(tmp_path))
    return generate.main()


def test_all_auth_failures_refuse_to_publish(tmp_path, monkeypatch):
    n = 40  # more than the config has; the iterator is only drawn as needed
    code = _run(monkeypatch, tmp_path, [(None, "http 401")] * n)
    assert code == 1
    assert not (tmp_path / "index.html").exists()


def test_all_network_failures_also_refuse(tmp_path, monkeypatch):
    code = _run(monkeypatch, tmp_path, [(None, "network error: boom")] * 40)
    assert code == 1
    assert not (tmp_path / "index.html").exists()


def test_a_partial_failure_still_publishes(tmp_path, monkeypatch):
    # One repo being unreachable must not blank the whole board — the other
    # rows are still true and still worth showing.
    results = [([], None)] + [(None, "http 401")] * 39
    code = _run(monkeypatch, tmp_path, results)
    assert code == 0
    assert (tmp_path / "index.html").exists()


def test_a_clean_run_publishes(tmp_path, monkeypatch):
    code = _run(monkeypatch, tmp_path, [([], None)] * 40)
    assert code == 0
    assert (tmp_path / "index.html").exists()
