#!/usr/bin/env python3
"""Generate the ci-glance dashboard HTML.

Reads `config.yml`, fetches workflow runs from the GitHub API, and writes
`html/index.html` plus `html/dashboard.css`. Designed to run on a cron via
the bundled GitHub Action, but can be run locally too.

Environment:
  GITHUB_TOKEN       Token used for API calls (required for private repos
                     and recommended for public ones to avoid the 60/hour
                     anonymous rate limit).
  CI_GLANCE_CONFIG   Path to config.yml (default: ./config.yml).
  CI_GLANCE_OUT      Output directory (default: ./html).
  LOG_LEVEL          Python log level (default: INFO).
"""
import logging
import os
import sys
from pathlib import Path

from ci_glance.config import load_config
from ci_glance.github import fetch_runs, runs_to_history
from ci_glance.render import build_repo_view, render_dashboard

ROOT = Path(__file__).resolve().parent

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(levelname)s %(message)s",
)
log = logging.getLogger("ci-glance")


def main() -> int:
    config_path = Path(os.environ.get("CI_GLANCE_CONFIG", ROOT / "config.yml"))
    out_dir = Path(os.environ.get("CI_GLANCE_OUT", ROOT / "html"))
    template_dir = ROOT / "templates"
    static_dir = ROOT / "static"

    if not config_path.exists():
        log.error("Config not found: %s", config_path)
        return 1

    cfg = load_config(config_path)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log.warning(
            "GITHUB_TOKEN not set — using anonymous requests "
            "(60/hour, public repos only)."
        )

    by_id = cfg.workflow_by_id
    repo_views = []
    errors = 0
    for idx, repo in enumerate(cfg.repos):
        log.info("fetching %s", repo.repo)
        wf_data = {}
        for wf_id in repo.workflows:
            wf = by_id[wf_id]
            runs, err = fetch_runs(
                repo.owner,
                repo.name,
                wf.file,
                per_page=cfg.settings.history_length,
                token=token,
            )
            if err:
                log.warning("  %s/%s: %s", repo.repo, wf.file, err)
                errors += 1
                wf_data[wf_id] = runs_to_history([], cfg.settings.history_length)
            else:
                wf_data[wf_id] = runs_to_history(runs or [], cfg.settings.history_length)
        repo_views.append(build_repo_view(cfg, repo, wf_data, idx))

    out = render_dashboard(
        cfg,
        repo_views,
        template_dir=template_dir,
        static_dir=static_dir,
        out_dir=out_dir,
    )
    log.info("wrote %s (errors: %d)", out, errors)
    return 0


if __name__ == "__main__":
    sys.exit(main())
