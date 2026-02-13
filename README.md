# LLM Configuration Scanner

GitHub Composite Action that scans repositories for LLM model references and creates issues when deprecated models are detected.

## What it does

1. **Scans** source code and config files for LLM model references (OpenAI, Anthropic, Google)
2. **Checks** against a JSON deprecation registry (`data/registry.json`) for deprecated/retiring/shutdown models
3. **Creates GitHub Issues** for each deprecated model found, with affected files, replacement suggestions, and shutdown dates
4. **Notifies Slack** (optional) when deprecated models are detected

## Data sources

| Source | Description |
|---|---|
| `data/registry.json` | JSON registry of deprecated models, committed in the repo |
| [deprecations.info](https://deprecations.info/) | Live feed merged into the registry every two weeks via GitHub Actions |
| [OpenAI deprecations](https://platform.openai.com/docs/deprecations) | Official OpenAI source |
| [Anthropic deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) | Official Anthropic source |
| [Google deprecations](https://ai.google.dev/gemini-api/docs/deprecations) | Official Google source |

The registry is updated every two weeks by `.github/workflows/update-registry.yml`. The scan pipeline reads from the local JSON file only — no network calls at scan time. If the feed is unreachable, a GitHub issue is automatically created.

## Supported models

| Provider | Models detected |
|---|---|
| OpenAI | gpt-4.1, gpt-5, gpt-5.1, gpt-4o, gpt-4-turbo, gpt-3.5-turbo, o1/o3/o4-mini, codex-mini |
| Anthropic | claude-opus-4, claude-sonnet-4, claude-3.5-sonnet/haiku, claude-3-opus/sonnet/haiku |
| Google | gemini-2.5-pro/flash, gemini-2.0-flash, gemini-1.5-pro/flash, gemini-pro |
| Embeddings | text-embedding-3-small/large, text-embedding-ada-002, voyage-* |

## Usage

### 1. Add the workflow to your repository

Copy `template-workflow.yml` to `.github/workflows/llm-scan.yml` in your target repository:

```yaml
name: LLM Configuration Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: "0 8 * * 1"  # Weekly on Monday
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: Baseline-quebec/tracking-llm-discontinued@main
        with:
          repo-name: ${{ github.repository }}
          assignees: ${{ vars.LLM_SCAN_ASSIGNEES || '' }}
```

### 2. Configure organization secrets/variables

| Name | Type | Description |
|---|---|---|
| `LLM_SCAN_SLACK_WEBHOOK` | Secret | Slack incoming webhook URL (optional) |
| `LLM_SCAN_ASSIGNEES` | Variable | Comma-separated GitHub usernames |

## Action inputs/outputs

### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `repo-name` | Yes | | Repository name |
| `assignees` | No | `""` | Comma-separated assignees for issues |
| `dry-run` | No | `false` | Scan only, don't create issues |

### Outputs

| Output | Description |
|---|---|
| `match-count` | Total model references found |
| `deprecated-count` | Number of deprecated model references |
| `issues-created` | Number of GitHub issues created |
| `deprecated-summary` | JSON summary of deprecated models |

## Registry update

The registry is updated automatically every two weeks (lundi a 06:00 UTC). You can also trigger it manually:

```bash
# Manually update the registry
PYTHONPATH=. python -m src.update_registry

# Specify a custom registry path
PYTHONPATH=. python -m src.update_registry --registry-path data/registry.json
```

If the feed is unreachable, a GitHub issue is created with details in French, assigned to the maintainers.

## Local usage

```bash
PYTHONPATH=. python -m src.main --repo-name "my-repo" --scan-path /path/to/repo --dry-run
```

## Tests

```bash
pip install pytest pytest-bdd
python -m pytest tests/ -v --rootdir=.
```

BDD tests covering:
- Pattern detection (LLM models, embeddings, date suffixes, false positives)
- Scanner (directory traversal, deduplication, exclusions)
- Deprecation registry (deprecated vs active models, date suffix handling, coherence checks)
- Registry update (add new models, overwrite existing, empty feed handling)
- Issue reporter (title/body formatting, grouping, dry-run, assignee validation)
- CLI orchestration (argument parsing, end-to-end pipelines)

## Architecture

```
data/
  registry.json          # JSON registry of deprecated models
src/
  patterns.py            # Regex patterns for model detection
  scanner.py             # Directory traversal and file scanning
  models.py              # Data models (ScanMatch, ScanResult)
  deprecations.py        # Registry loader + date suffix handling
  deprecation_feed.py    # Feed fetcher from deprecations.info
  update_registry.py     # Script: fetch -> merge -> save (+ issue on failure)
  issue_reporter.py      # GitHub issue creation via gh CLI
  main.py                # CLI entry point and orchestration
.github/workflows/
  ci.yml                 # CI: lint, tests, type checking
  update-registry.yml    # Biweekly cron to update registry from feed
```
