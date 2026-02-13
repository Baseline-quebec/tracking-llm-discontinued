"""Validate that all models in the registry are matched by regex patterns.

Usage:
    PYTHONPATH=. python -m src.validate_patterns [--registry-path data/registry.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.deprecations import _DEFAULT_REGISTRY_PATH, load_registry
from src.patterns import find_matches_in_line


logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate regex pattern coverage for registry models",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=_DEFAULT_REGISTRY_PATH,
        help="Path to the registry JSON file (default: data/registry.json)",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output results as JSON instead of human-readable text",
    )
    return parser.parse_args(argv)


def validate_coverage(registry_path: Path) -> dict[str, list[str]]:
    """Check which registry models are matched by existing patterns.

    Args:
        registry_path: Path to the registry JSON file.

    Returns:
        Dict with 'matched' and 'unmatched' lists of model names.
    """
    registry = load_registry(registry_path)
    matched: list[str] = []
    unmatched: list[str] = []

    for model_name in registry:
        line = f'model = "{model_name}"'
        matches = find_matches_in_line(line)
        matched_models = [m[1] for m in matches]
        if model_name in matched_models:
            matched.append(model_name)
        else:
            unmatched.append(model_name)

    return {"matched": matched, "unmatched": unmatched}


def main(argv: list[str] | None = None) -> None:
    """Entry point for the validation script."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    results = validate_coverage(args.registry_path)

    if args.output_json:
        print(json.dumps(results, indent=2))
    else:
        logger.info("Matched: %d models", len(results["matched"]))
        for model in results["matched"]:
            logger.info("  + %s", model)

        if results["unmatched"]:
            logger.warning("Unmatched: %d models", len(results["unmatched"]))
            for model in results["unmatched"]:
                logger.warning("  - %s", model)
        else:
            logger.info("All registry models are covered by patterns.")

    if results["unmatched"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
