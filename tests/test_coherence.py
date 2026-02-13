"""Coherence tests: verify patterns and deprecation registry are aligned."""

from __future__ import annotations

import pytest

from src.deprecations import DEPRECATION_REGISTRY
from src.patterns import find_matches_in_line


@pytest.mark.parametrize("model_name", list(DEPRECATION_REGISTRY.keys()))
def test_all_deprecated_models_are_detectable(model_name: str) -> None:
    """Every model in the deprecation registry must be detected by at least one pattern."""
    line = f'model = "{model_name}"'
    matches = find_matches_in_line(line)
    matched_models = [m[1] for m in matches]
    assert model_name in matched_models, (
        f"Deprecated model '{model_name}' is not detectable by any pattern. "
        f"Line: '{line}', matches found: {matched_models}"
    )
