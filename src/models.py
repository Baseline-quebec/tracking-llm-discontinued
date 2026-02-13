"""Data models for LLM configuration scan results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MatchType = Literal["llm", "embedding"]


@dataclass(frozen=True)
class ScanMatch:
    """A single LLM/embedding model reference found in a file."""

    provider: str
    model: str
    match_type: MatchType
    file: str
    line: int


@dataclass
class ScanResult:
    """Aggregated scan results for a repository."""

    repo_name: str
    matches: list[ScanMatch]

    @property
    def match_count(self) -> int:
        """Return the total number of scan matches."""
        return len(self.matches)
