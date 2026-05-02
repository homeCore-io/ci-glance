"""Build the per-repo view objects and render the dashboard HTML."""
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ci_glance.config import Config, Workflow
from ci_glance.state import COMPLETED, derive_state

VERSION_RE = re.compile(r"v?\d+\.\d+(?:\.\d+)?")
STATE_RANK = {"FAIL": 0, "FLAKY": 1, "—": 2, "OK": 3}


def _zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def extract_label(run: dict, kind: str, tz: str) -> str:
    """Derive the 'Last' column label for a single (most-recent) completed run."""
    if not run or run.get("status") == "none":
        return ""

    if kind == "version":
        title = run.get("display_title") or ""
        m = VERSION_RE.search(title)
        if m:
            return m.group(0)
        # Fall back to branch, then short sha
        return run.get("head_branch") or (run.get("head_sha") or "")[:7]

    if kind == "branch":
        return run.get("head_branch", "")

    if kind == "sha":
        return (run.get("head_sha") or "")[:7]

    # default: time
    iso = run.get("created_at") or ""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return dt.astimezone(_zone(tz)).strftime("%H:%M")


def _state_class(state: str) -> str:
    return {"OK": "ok", "FAIL": "fail", "FLAKY": "flaky", "—": "none"}.get(state, "none")


def build_repo_view(cfg: Config, repo, workflow_data: dict, idx: int) -> dict:
    by_id = cfg.workflow_by_id
    rendered = []
    for wf_id in repo.workflows:
        wf: Optional[Workflow] = by_id.get(wf_id)
        if wf is None:
            continue
        history = workflow_data.get(wf_id, [])
        last_real = next(
            (h for h in reversed(history) if h.get("status") in COMPLETED),
            None,
        )
        state = derive_state(history, cfg.settings.flaky_threshold)
        rendered.append({
            "id": wf.id,
            "label": wf.label,
            "history": history,
            "last_label": extract_label(last_real or {}, wf.last_label, cfg.settings.timezone),
            "last_url": (last_real or {}).get("url", ""),
            "state": state,
            "state_class": _state_class(state),
        })

    return {
        "name": repo.name,
        "full_name": repo.repo,
        "url": f"https://github.com/{repo.repo}",
        "workflows": rendered,
        "_index": idx,
    }


def repo_sort_key(repo_view: dict, mode: str):
    if mode == "alpha":
        return (repo_view["name"].lower(),)
    if mode == "config":
        return (repo_view["_index"],)
    # failing-first: worst state first, alpha within
    states = [w["state"] for w in repo_view["workflows"]] or ["—"]
    worst = min(STATE_RANK.get(s, 9) for s in states)
    return (worst, repo_view["name"].lower())


def summarize(repo_views: List[dict]) -> dict:
    """Count repos by their worst workflow state."""
    counts = {"OK": 0, "FAIL": 0, "FLAKY": 0, "—": 0}
    for rv in repo_views:
        if not rv["workflows"]:
            counts["—"] += 1
            continue
        worst = min(rv["workflows"], key=lambda w: STATE_RANK.get(w["state"], 9))["state"]
        counts[worst] = counts.get(worst, 0) + 1
    return counts


def render_dashboard(
    cfg: Config,
    repo_views: List[dict],
    *,
    template_dir: Path,
    static_dir: Path,
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    repo_views = sorted(repo_views, key=lambda rv: repo_sort_key(rv, cfg.settings.sort))
    summary = summarize(repo_views)
    now_local = datetime.now(timezone.utc).astimezone(_zone(cfg.settings.timezone))
    synced = now_local.strftime("%H:%M")
    last_updated = now_local.strftime("%H:%M %b %d, %Y")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("dashboard.html.j2")
    html = template.render(
        cfg=cfg,
        repos=repo_views,
        summary=summary,
        synced=synced,
        last_updated=last_updated,
    )

    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    shutil.copy(static_dir / "dashboard.css", out_dir / "dashboard.css")
    return index_path
