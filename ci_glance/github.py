"""GitHub Actions API client.

Single endpoint: list workflow runs. Returns runs oldest-first so callers
can render them left-to-right without re-thinking direction.
"""
import logging
from typing import List, Optional, Tuple

import requests

from ci_glance.state import normalize_conclusion

log = logging.getLogger(__name__)

API_ROOT = "https://api.github.com"


def _headers(token: Optional[str]) -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ci-glance",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_runs(
    owner: str,
    repo: str,
    workflow_file: str,
    *,
    per_page: int = 20,
    token: Optional[str] = None,
    timeout: int = 15,
) -> Tuple[Optional[List[dict]], Optional[str]]:
    """Fetch the most recent `per_page` runs of a workflow.

    Returns (runs, error). Runs are oldest-first. On 404 (workflow file
    doesn't exist in the repo) returns ([], None) so the caller can render
    an empty sparkline rather than crashing the whole dashboard.
    """
    url = (
        f"{API_ROOT}/repos/{owner}/{repo}/actions/workflows/"
        f"{workflow_file}/runs?per_page={per_page}"
    )
    try:
        resp = requests.get(url, headers=_headers(token), timeout=timeout)
    except requests.RequestException as e:
        return None, f"network error: {e}"

    if resp.status_code == 404:
        return [], None
    if resp.status_code != 200:
        return None, f"http {resp.status_code}"

    runs = resp.json().get("workflow_runs", [])
    runs.reverse()  # API returns newest-first; we want oldest-first
    return runs, None


def runs_to_history(runs: List[dict], history_length: int) -> List[dict]:
    """Map raw run JSON to history entries and pad to `history_length`.

    Pad squares (status == 'none') are prepended so the newest run stays on
    the right edge of the sparkline.
    """
    history = [
        {
            "status": normalize_conclusion(r.get("conclusion")),
            "url": r.get("html_url", ""),
            "id": r.get("id"),
            "created_at": r.get("created_at", ""),
            "head_branch": r.get("head_branch", ""),
            "head_sha": r.get("head_sha", ""),
            "display_title": r.get("display_title", ""),
            "name": r.get("name", ""),
        }
        for r in runs
    ]
    history = history[-history_length:]
    pad = history_length - len(history)
    if pad > 0:
        history = [{"status": "none"}] * pad + history
    return history
