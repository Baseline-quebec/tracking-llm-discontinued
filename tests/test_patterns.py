"""BDD step definitions for LLM pattern detection tests."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when
from src.patterns import find_matches_in_line


scenarios("features/patterns.feature")


@given(
    parsers.cfparse('a line containing "{line}"'),
    target_fixture="line_text",
)
def given_line(line: str) -> str:
    return line


@when(
    "I scan the line for matches",
    target_fixture="matches",
)
def scan_line(line_text: str) -> list[tuple[str, str, str]]:
    return find_matches_in_line(line_text)


@then(
    parsers.cfparse('I should find model "{model}" from provider "{provider}"'),
)
def check_model_and_provider(
    matches: list[tuple[str, str, str]], model: str, provider: str
) -> None:
    found = [(p, m) for p, m, _ in matches]
    assert (provider, model) in found, f"Expected ({provider}, {model}) in {found}"


@then(
    parsers.cfparse('the match type should be "{match_type}"'),
)
def check_match_type(matches: list[tuple[str, str, str]], match_type: str) -> None:
    types = [t for _, _, t in matches]
    assert match_type in types, f"Expected match_type '{match_type}' in {types}"


@then(
    parsers.cfparse("I should find {count:d} matches"),
)
def check_match_count(matches: list[tuple[str, str, str]], count: int) -> None:
    assert len(matches) == count, f"Expected {count} matches, got {len(matches)}: {matches}"
