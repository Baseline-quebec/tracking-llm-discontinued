# LLM Configuration Scanner

Action composite GitHub qui scanne les dépôts pour détecter les références à des modèles LLM et crée des issues lorsque des modèles dépréciés sont détectés.

## Ce que ça fait

1. **Scanne** le code source et les fichiers de configuration pour trouver les références aux modèles LLM (OpenAI, Anthropic, Google)
2. **Vérifie** contre un registre de dépréciation JSON (`data/registry.json`) les modèles dépréciés/en retrait/arrêtés
3. **Crée des issues GitHub** pour chaque modèle déprécié trouvé, avec les fichiers affectés, les suggestions de remplacement et les dates d'arrêt
4. **Notifie Slack** (optionnel) lorsque des modèles dépréciés sont détectés

## Sources de données

| Source | Description |
|---|---|
| `data/registry.json` | Registre JSON des modèles dépréciés, commité dans le dépôt |
| [deprecations.info](https://deprecations.info/) | Flux en direct fusionné dans le registre aux deux semaines via GitHub Actions |
| [OpenAI deprecations](https://platform.openai.com/docs/deprecations) | Source officielle OpenAI |
| [Anthropic deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) | Source officielle Anthropic |
| [Google deprecations](https://ai.google.dev/gemini-api/docs/deprecations) | Source officielle Google |

Le registre est mis à jour aux deux semaines par `.github/workflows/update-registry.yml`. Le pipeline de scan lit uniquement le fichier JSON local — aucun appel réseau lors du scan. Si le flux est inaccessible, une issue GitHub est automatiquement créée.

## Modèles supportés

| Fournisseur | Modèles détectés |
|---|---|
| OpenAI | gpt-4.1, gpt-5, gpt-5.1, gpt-4o, gpt-4-turbo, gpt-3.5-turbo, o1/o3/o4-mini, codex-mini |
| Anthropic | claude-opus-4, claude-sonnet-4, claude-3.5-sonnet/haiku, claude-3-opus/sonnet/haiku |
| Google | gemini-2.5-pro/flash, gemini-2.0-flash, gemini-1.5-pro/flash, gemini-pro |
| Embeddings | text-embedding-3-small/large, text-embedding-ada-002, voyage-* |

## Modèles dépréciés suivis

<!-- REGISTRY_START -->
| Model | Provider | Status | Shutdown date | Replacement |
|---|---|---|---|---|
| claude-3-opus | anthropic | shutdown | 2026-01-05 | claude-opus-4 |
| claude-3-sonnet | anthropic | shutdown | 2025-07-21 | claude-sonnet-4 |
| claude-3.5-haiku | anthropic | deprecated | 2026-02-19 | claude-haiku-4-5 |
| claude-3.5-sonnet | anthropic | shutdown | 2025-10-28 | claude-sonnet-4 |
| gemini-1.5-flash | google | shutdown | 2025-09-23 | gemini-2.5-flash |
| gemini-1.5-pro | google | shutdown | 2025-09-23 | gemini-2.5-pro |
| gemini-2.0-flash | google | retiring | 2026-03-31 | gemini-2.5-flash |
| gemini-pro | google | shutdown | 2025-02-15 | gemini-2.5-pro |
| gpt-3.5-turbo | openai | deprecated | 2025-09-14 | gpt-4.1-mini |
| gpt-4 | openai | retiring | 2026-06-06 | gpt-4.1 |
| gpt-4-turbo | openai | retiring | 2026-06-06 | gpt-4.1 |
| gpt-4-turbo-preview | openai | retiring | 2026-06-06 | gpt-4.1 |
| gpt-4o | openai | retiring | 2026-10-01 | gpt-4.1 |
| gpt-4o-mini | openai | retiring | 2026-10-01 | gpt-4.1-mini |
| o1 | openai | retiring | 2026-07-15 | o3 |
| o1-mini | openai | shutdown | 2025-10-27 | o4-mini |
| o1-preview | openai | shutdown | 2025-07-28 | o3 |
| text-embedding-ada-002 | openai | retiring | 2027-04-15 | text-embedding-3-small |
<!-- REGISTRY_END -->

## Utilisation

### 1. Ajouter le workflow à votre dépôt

Copiez `template-workflow.yml` dans `.github/workflows/llm-scan.yml` de votre dépôt cible :

```yaml
name: LLM Configuration Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: "0 8 1,15 * *"  # Bi-weekly: 1st and 15th of each month
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

### 2. Configurer les secrets/variables de l'organisation

| Nom | Type | Description |
|---|---|---|
| `LLM_SCAN_SLACK_WEBHOOK` | Secret | URL du webhook Slack entrant (optionnel) |
| `LLM_SCAN_ASSIGNEES` | Variable | Noms d'utilisateur GitHub séparés par des virgules |

## Entrées/sorties de l'action

### Entrées

| Entrée | Requis | Défaut | Description |
|---|---|---|---|
| `repo-name` | Oui | | Nom du dépôt |
| `assignees` | Non | `""` | Assignés séparés par des virgules |
| `dry-run` | Non | `false` | Scanner seulement, ne pas créer d'issues |

### Sorties

| Sortie | Description |
|---|---|
| `match-count` | Nombre total de références trouvées |
| `deprecated-count` | Nombre de références à des modèles dépréciés |
| `issues-created` | Nombre d'issues GitHub créées |
| `deprecated-summary` | Résumé JSON des modèles dépréciés |

## Mise à jour du registre

Le registre est mis à jour automatiquement aux deux semaines (lundi à 06:00 UTC). Vous pouvez aussi le déclencher manuellement :

```bash
# Manually update the registry
PYTHONPATH=. python -m src.update_registry

# Specify a custom registry path
PYTHONPATH=. python -m src.update_registry --registry-path data/registry.json
```

Si le flux est inaccessible, une issue GitHub est créée avec les détails en français, assignée aux mainteneurs.

## Utilisation locale

```bash
PYTHONPATH=. python -m src.main --repo-name "my-repo" --scan-path /path/to/repo --dry-run
```

## Tests

```bash
pip install pytest pytest-bdd
python -m pytest tests/ -v --rootdir=.
```

Tests BDD couvrant :
- Détection de patterns (modèles LLM, embeddings, suffixes de date, faux positifs)
- Scanner (parcours de répertoires, déduplication, exclusions)
- Registre de dépréciation (modèles dépréciés vs actifs, gestion des suffixes de date, vérifications de cohérence)
- Mise à jour du registre (ajout de nouveaux modèles, écrasement d'existants, gestion de flux vide)
- Rapporteur d'issues (formatage titre/corps, regroupement, dry-run, validation des assignés)
- Orchestration CLI (parsing d'arguments, pipelines bout-en-bout)

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
