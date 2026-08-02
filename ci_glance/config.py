"""Config loader for ci-glance.

The config schema is intentionally small. Add knobs here only when a real
use case demands one — `config.yml` is the user-facing API.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml


VALID_SORT = ("failing-first", "config", "alpha")
VALID_LAST_LABEL = ("time", "version", "branch", "sha")


@dataclass
class Workflow:
    id: str
    file: str
    label: str
    last_label: str = "time"


@dataclass
class Repo:
    repo: str  # "owner/name"
    workflows: List[str] = field(default_factory=list)

    @property
    def owner(self) -> str:
        return self.repo.split("/", 1)[0]

    @property
    def name(self) -> str:
        return self.repo.split("/", 1)[1]


@dataclass
class Theme:
    ok: str = "#1D9E75"
    fail: str = "#E24B4A"
    flaky: str = "#BA7517"


@dataclass
class Settings:
    history_length: int = 20
    flaky_threshold: int = 2
    # Consecutive green runs that clear a FLAKY flag. 0 = never forget.
    recovery_streak: int = 5
    sort: str = "failing-first"
    refresh_seconds: int = 300
    timezone: str = "America/New_York"


@dataclass
class Config:
    title: str = "Builds"
    subtitle: str = ""
    footer: str = ""
    theme: Theme = field(default_factory=Theme)
    settings: Settings = field(default_factory=Settings)
    workflows: List[Workflow] = field(default_factory=list)
    repos: List[Repo] = field(default_factory=list)

    @property
    def workflow_by_id(self) -> Dict[str, Workflow]:
        return {w.id: w for w in self.workflows}


def _filter_keys(d: dict, allowed: set) -> dict:
    return {k: v for k, v in (d or {}).items() if k in allowed}


def load_config(path: Path) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    cfg = Config()
    cfg.title = raw.get("title", cfg.title)
    cfg.subtitle = raw.get("subtitle", cfg.subtitle)
    cfg.footer = raw.get("footer", cfg.footer)
    cfg.theme = Theme(**_filter_keys(raw.get("theme"), {"ok", "fail", "flaky"}))
    cfg.settings = Settings(
        **_filter_keys(
            raw.get("settings"),
            {"history_length", "flaky_threshold", "recovery_streak", "sort",
             "refresh_seconds", "timezone"},
        )
    )

    cfg.workflows = [
        Workflow(
            id=w["id"],
            file=w["file"],
            label=w.get("label", w["id"].upper()),
            last_label=w.get("last_label", "time"),
        )
        for w in (raw.get("workflows") or [])
    ]

    cfg.repos = [
        Repo(
            repo=r["repo"],
            workflows=list(r.get("workflows") or [w.id for w in cfg.workflows]),
        )
        for r in (raw.get("repos") or [])
    ]

    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    if cfg.settings.sort not in VALID_SORT:
        raise ValueError(
            f"settings.sort must be one of {VALID_SORT}, got {cfg.settings.sort!r}"
        )
    for w in cfg.workflows:
        if w.last_label not in VALID_LAST_LABEL:
            raise ValueError(
                f"workflow {w.id!r}: last_label must be one of "
                f"{VALID_LAST_LABEL}, got {w.last_label!r}"
            )
    valid_ids = {w.id for w in cfg.workflows}
    for r in cfg.repos:
        if "/" not in r.repo:
            raise ValueError(f"repo {r.repo!r} must be in 'owner/name' form")
        unknown = [w for w in r.workflows if w not in valid_ids]
        if unknown:
            raise ValueError(
                f"repo {r.repo!r} references unknown workflow ids {unknown}; "
                f"define them under 'workflows:' first"
            )
