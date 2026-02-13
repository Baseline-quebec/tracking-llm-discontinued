# LLM Configuration Scanner

GitHub Composite Action that scans repositories for LLM model references and creates issues when deprecated models are detected.

## What it does

1. **Scans** source code and config files for LLM model references (OpenAI, Anthropic, Google, Meta, Mistral, Cohere, DeepSeek, xAI)
2. **Detects** deprecated/retiring/shutdown models (e.g. gpt-4o, gpt-3.5-turbo, o1-preview, text-embedding-ada-002)
3. **Creates GitHub Issues** for each deprecated model found, with affected files, replacement suggestions, and shutdown dates
4. **Notifies Slack** (optional) when deprecated models are detected

## Supported models

| Provider | Models detected |
|---|---|
| OpenAI | gpt-4.1, gpt-5, gpt-5.1, gpt-4o, gpt-4-turbo, gpt-3.5-turbo, o1/o3/o4-mini, codex-mini |
| Anthropic | claude-opus-4, claude-sonnet-4, claude-3.5-sonnet/haiku, claude-3-opus/sonnet/haiku |
| Google | gemini-2.5-pro/flash, gemini-2.0-flash, gemini-1.5-pro/flash, gemini-pro |
| Meta | llama-3, llama-2, codellama |
| Mistral | mistral-large/medium/small, mixtral, codestral |
| Cohere | command-r-plus, command-r |
| DeepSeek | deepseek-v3, deepseek-r1, deepseek-coder |
| xAI | grok-2, grok-3 |
| Embeddings | text-embedding-3-small/large, text-embedding-ada-002, embed-english-v3.0, voyage-* |
| Frameworks | langchain, llamaindex, crewai, litellm, haystack, autogen, dspy |

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
| `match-count` | Total model/framework references found |
| `deprecated-count` | Number of deprecated model references |
| `issues-created` | Number of GitHub issues created |
| `deprecated-summary` | JSON summary of deprecated models |

## Local usage

```bash
PYTHONPATH=. python -m src.main --repo-name "my-repo" --scan-path /path/to/repo --dry-run
```

## Tests

```bash
pip install pytest pytest-bdd
python -m pytest tests/ -v --rootdir=.
```

142 BDD tests covering:
- Pattern detection (LLM models, embeddings, frameworks, date suffixes, false positives)
- Scanner (directory traversal, deduplication, exclusions)
- Deprecation registry (deprecated vs active models, coherence checks)
- Issue reporter (title/body formatting, grouping, dry-run, assignee validation)
- CLI orchestration (argument parsing, end-to-end pipelines)

## Architecture

```
src/
  patterns.py       # Regex patterns for model detection
  scanner.py        # Directory traversal and file scanning
  models.py         # Data models (ScanMatch, ScanResult)
  deprecations.py   # Deprecated model registry
  issue_reporter.py # GitHub issue creation via gh CLI
  main.py           # CLI entry point and orchestration
```
