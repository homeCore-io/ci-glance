"""The Last column for a release workflow should name the released version.

`release.yml` in these repos fires on tag pushes *and* on every push to
develop. The newest run is therefore usually a develop build whose commit
message carries no version, so a column that simply labelled the newest run
fell through to the branch name and read "develop" for repos that had been
shipping tags perfectly well.
"""
from ci_glance.config import Config, Settings, Workflow, Repo
from ci_glance.render import build_repo_view, extract_label

TZ = "UTC"


def run(status="ok", branch="", title="", sha="abc1234def", url="u"):
    return {
        "status": status,
        "head_branch": branch,
        "display_title": title,
        "head_sha": sha,
        "url": url,
    }


def _cfg():
    return Config(
        title="t",
        subtitle="s",
        footer=None,
        theme={},
        settings=Settings(
            history_length=20,
            flaky_threshold=2,
            sort="config",
            refresh_seconds=0,
            timezone=TZ,
        ),
        workflows=[
            Workflow(id="release", file="release.yml", label="Rel",
                     last_label="version"),
        ],
        repos=[Repo(repo="homeCore-io/hc-sonos", workflows=["release"])],
    )


def _label(history):
    cfg = _cfg()
    view = build_repo_view(cfg, cfg.repos[0], {"release": history}, 0)
    return view["workflows"][0]["last_label"]


class TestExtractLabel:
    def test_a_tag_push_is_labelled_by_its_tag(self):
        # The tag IS the version — no need to parse the commit message, which
        # for a tag push is whatever the merge happened to be called.
        assert extract_label(
            run(branch="v0.1.18", title="Merge develop into main: 0.1.18"),
            "version", TZ) == "v0.1.18"

    def test_a_tag_whose_message_has_no_version_still_labels(self):
        assert extract_label(
            run(branch="v0.1.8", title="Say what this plugin cannot do"),
            "version", TZ) == "v0.1.8"

    def test_a_branch_run_falls_back_to_the_message_then_the_branch(self):
        assert extract_label(
            run(branch="develop", title="Release 0.1.18"), "version", TZ
        ) == "0.1.18"
        assert extract_label(
            run(branch="develop", title="Adopt plugin SDK"), "version", TZ
        ) == "develop"


class TestRunSelection:
    def test_the_newest_tag_wins_over_newer_develop_runs(self):
        # The exact shape on the dashboard: a tagged release, then two develop
        # pushes after it. The column must still name the release.
        history = [
            run(branch="v0.1.7", title="Drop the unused container recipe"),
            run(branch="v0.1.8", title="Say what this plugin cannot do"),
            run(branch="develop", title="Adopt plugin SDK v0.3.6"),
            run(branch="develop", title="Say what this plugin cannot do"),
        ]
        assert _label(history) == "v0.1.8"

    def test_an_untagged_repo_still_shows_something(self):
        # A repo that has never shipped should not render a blank cell.
        history = [run(branch="develop", title="first commit")]
        assert _label(history) == "develop"

    def test_an_in_flight_tag_run_is_not_labelled_yet(self):
        # Only completed runs count, so a release mid-build does not claim a
        # version it has not finished producing.
        history = [
            run(branch="v0.1.8", title="shipped"),
            run(status="none", branch="v0.1.9", title="building"),
        ]
        assert _label(history) == "v0.1.8"

    def test_time_labelled_workflows_are_untouched(self):
        cfg = _cfg()
        cfg.workflows[0] = Workflow(
            id="release", file="release.yml", label="Rel", last_label="branch")
        view = build_repo_view(
            cfg,
            cfg.repos[0],
            {"release": [run(branch="v0.1.8"), run(branch="develop")]},
            0,
        )
        # branch mode still means "the newest run's branch", not the newest tag.
        assert view["workflows"][0]["last_label"] == "develop"
