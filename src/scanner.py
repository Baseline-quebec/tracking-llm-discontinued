"""File scanner that walks a directory tree and detects LLM model references."""

from __future__ import annotations

import logging
from pathlib import Path

from src.models import ScanMatch, ScanResult
from src.patterns import find_matches_in_line


logger = logging.getLogger(__name__)

# Directories to skip during scanning
EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        "venv",
        ".venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".eggs",
    }
)

# File extensions to scan
SCANNABLE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".env",
        ".md",
        ".txt",
        ".dockerfile",
        ".tf",
        ".hcl",
    }
)

# Files to scan regardless of extension
SCANNABLE_FILENAMES: frozenset[str] = frozenset(
    {
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Makefile",
        ".env",
        ".env.example",
        ".env.local",
        ".env.production",
    }
)

# Max file size to scan (1 MB)
MAX_FILE_SIZE: int = 1_048_576


def _should_scan_file(path: Path) -> bool:
    """Determine if a file should be scanned based on extension and name."""
    if path.name in SCANNABLE_FILENAMES:
        return True
    return path.suffix.lower() in SCANNABLE_EXTENSIONS


def _should_skip_dir(dirname: str) -> bool:
    """Determine if a directory should be skipped."""
    return dirname in EXCLUDED_DIRS or dirname.endswith(".egg-info")


def scan_directory(scan_path: Path, repo_name: str) -> ScanResult:
    """Scan a directory tree for LLM model references.

    Args:
        scan_path: Root directory to scan.
        repo_name: Name of the repository (used in results).

    Returns:
        ScanResult with deduplicated matches.
    """
    seen: set[tuple[str, str, str]] = set()  # (model, file, match_type) for dedup
    matches: list[ScanMatch] = []

    for file_path in _walk_files(scan_path):
        relative_path = str(file_path.relative_to(scan_path))
        _scan_file(file_path, relative_path, seen, matches)

    logger.info("Scanned %s: found %d unique matches", repo_name, len(matches))
    return ScanResult(repo_name=repo_name, matches=matches)


def _walk_files(root: Path) -> list[Path]:
    """Walk directory tree returning scannable files (iterative)."""
    files: list[Path] = []

    if not root.is_dir():
        return files

    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), reverse=True)
        except OSError:
            continue
        for item in children:
            if item.is_dir():
                if not _should_skip_dir(item.name):
                    stack.append(item)
            elif (
                item.is_file() and _should_scan_file(item) and item.stat().st_size <= MAX_FILE_SIZE
            ):
                files.append(item)

    return files


def _scan_file(
    file_path: Path,
    relative_path: str,
    seen: set[tuple[str, str, str]],
    matches: list[ScanMatch],
) -> None:
    """Scan a single file for LLM model references."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        logger.warning("Could not read %s: %s", relative_path, exc)
        return

    for line_num, line in enumerate(content.splitlines(), start=1):
        for provider, model_name, match_type in find_matches_in_line(line):
            dedup_key = (model_name, relative_path, match_type)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            matches.append(
                ScanMatch(
                    provider=provider,
                    model=model_name,
                    match_type=match_type,
                    file=relative_path,
                    line=line_num,
                )
            )
