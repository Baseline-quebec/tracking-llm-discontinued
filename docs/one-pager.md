# LLM Configuration Scanner - One-Pager

## Besoin metier

Les projets de Baseline utilisent des modeles LLM (OpenAI, Anthropic, Google) qui sont regulierement deprecies par leurs fournisseurs. Un modele retire sans migration prealable provoque des **pannes en production**. Il faut detecter proactivement les references a des modeles deprecies dans l'ensemble des depots de code.

## Exigences fonctionnelles

| # | Exigence | Statut |
|---|----------|--------|
| F1 | Scanner les fichiers source (.py, .yml, .json, .ts, etc.) pour detecter les references aux modeles LLM | Implemente |
| F2 | Detecter les modeles de 3 fournisseurs (OpenAI, Anthropic, Google) et les embeddings (OpenAI, Voyage) | Implemente |
| F3 | Comparer les modeles detectes au registre de depreciation JSON (`data/registry.json`) | Implemente |
| F4 | Gerer les suffixes de date (ex: `gpt-4o-2024-08-06` -> `gpt-4o`) | Implemente |
| F5 | Creer automatiquement des issues GitHub avec fichiers affectes et remplacement suggere | Partiel (issues + fichiers OK ; remplacement suggere : a faire, mapping deprecated -> remplacement non implemente dans `issue_reporter._build_body`) |
| F6 | Eviter les doublons d'issues (verification avant creation) | Implemente |
| F7 | Alimenter le registre depuis le flux live deprecations.info | Implemente |
| F8 | Mettre a jour le registre automatiquement toutes les 2 semaines via PR | Implemente |
| F9 | Creer une issue GitHub automatiquement si le flux est inaccessible | Implemente |
| F10 | Valider la couverture regex des nouveaux modeles via Claude lors des mises a jour du registre | Implemente |
| F11 | Envoyer les details des issues par webhook HTTP POST vers un CRM (optionnel, fire-and-forget) | Implemente |

## Exigences techniques

| # | Exigence | Statut |
|---|----------|--------|
| T1 | GitHub Composite Action reutilisable par tous les depots | Implemente |
| T2 | Registre JSON persiste (`data/registry.json`) avec date de mise a jour | Implemente |
| T3 | Workflow de mise a jour bimensuel (`update-registry.yml`) avec PR automatique et auto-merge | Implemente |
| T4 | Tests BDD couvrant : patterns, scanner, depreciations, feed, issues, CLI, registre | Implemente |
| T5 | CI : lint (ruff), tests (pytest), type checking (mypy) | Implemente |
| T6 | Zero dependance runtime (stdlib Python + gh CLI uniquement) | Implemente |
| T7 | Script de validation regex (`src/validate_patterns.py`) pour verifier la couverture des patterns | Implemente |
| T8 | Integration Claude (`claude-code-action`) pour revue automatique des lacunes regex | Implemente |

## Architecture

```
data/
  registry.json          # Registre JSON des modeles deprecies
docs/
  one-pager.md           # Ce document
src/
  patterns.py            # Patterns regex pour la detection de modeles
  scanner.py             # Parcours de repertoire et scan de fichiers
  models.py              # Modeles de donnees (ScanMatch, ScanResult)
  deprecations.py        # Chargement du registre + gestion des suffixes de date
  deprecation_feed.py    # Flux live depuis deprecations.info
  update_registry.py     # Script : fetch -> merge -> save (+ issue en cas d'echec)
  validate_patterns.py   # Validation de couverture regex pour les modeles du registre
  issue_reporter.py      # Creation d'issues GitHub via gh CLI
  webhook.py             # Notifications webhook HTTP POST pour integration CRM
  main.py                # Point d'entree CLI et orchestration du scan
.github/workflows/
  ci.yml                 # CI : lint, tests, type checking
  update-registry.yml    # Cron bimensuel : mise a jour registre + validation Claude
```

## Flux de donnees

1. **Scan** : `scanner.py` parcourt un depot cible, `patterns.py` detecte les modeles
2. **Verification** : chaque modele trouve est compare au registre JSON local
3. **Alerte** : `issue_reporter.py` cree des issues GitHub pour les modeles deprecies
4. **Webhook** : `webhook.py` envoie les details de chaque issue par HTTP POST vers un CRM (optionnel)
5. **Mise a jour** : `update_registry.py` recupere le flux deprecations.info et met a jour `registry.json`
6. **Validation** : Claude verifie que les patterns regex couvrent les nouveaux modeles du registre
