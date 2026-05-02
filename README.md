# ci-glance

A static, themable, fork-and-configure dashboard for GitHub Actions build
status across multiple repositories.

For each repo you list, ci-glance pulls the last 20 runs of each workflow
you care about and renders them as a sparkline of colored squares plus a
state cell — `OK`, `FAIL`, or `FLAKY`. Output is a single static HTML page
suitable for GitHub Pages or any static host.

## Quickstart

1. Click **Use this template** at the top of the GitHub repo page, then
   clone your new copy.
2. Edit `config.yml` — set the title and list the repos and workflows you
   want to track.
3. Create a fine-grained personal access token with `Actions: read` and
   `Metadata: read` on those repos. Add it as a repository secret named
   `DASH_TOKEN`.
4. In the repo's settings: **Pages → Build and deployment → Source →
   GitHub Actions**.
5. The bundled workflow runs every 15 minutes and publishes your dashboard
   to `https://<you>.github.io/<repo>/`.

To trigger a build immediately, run **Build and deploy dashboard** from
the Actions tab, or push any change to `main`.

## Running locally

```sh
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_...
python generate.py
# open html/index.html
```

## Configuration

`config.yml` is the only file most users need to touch.

```yaml
title: My Builds
subtitle: "Workflow status across my repos"

settings:
  history_length: 20      # runs per sparkline
  flaky_threshold: 2      # failures to flag as FLAKY
  sort: failing-first     # failing-first | config | alpha
  refresh_seconds: 300    # auto-reload (0 = disable)
  timezone: America/New_York

workflows:
  - { id: ci,      file: ci.yml,      label: CI,  last_label: time }
  - { id: release, file: release.yml, label: Rel, last_label: version }

repos:
  - { repo: your-org/your-repo,    workflows: [ci, release] }
  - { repo: your-org/another-repo, workflows: [ci] }
```

### State derivation

- All recent runs successful → **OK**
- Most recent run failed → **FAIL**
- ≥`flaky_threshold` failures in history but most recent is OK → **FLAKY**
- No completed runs (yet) → **—**

### Last-column label kinds

| `last_label` | What it shows |
|---|---|
| `time` (default) | `HH:MM` of the most recent run, in your `timezone` |
| `version` | Version tag from the run's display title (e.g. `v1.2.3`), with branch fallback |
| `branch` | Head branch name |
| `sha` | Short commit SHA |

## Theming

Visual customization lives in two places:

- **`config.yml` → `theme:`** lets you override just the three sparkline
  colors (`ok`, `fail`, `flaky`).
- **`static/dashboard.css`** is the full stylesheet, using CSS custom
  properties on `:root`. Light/dark switches automatically via
  `prefers-color-scheme`.

## Tests

```sh
pip install pytest
pytest
```

## License

MIT — see [LICENSE](LICENSE).
