from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


# Shared marker-candidate regex. A candidate is any line that structurally
# looks like ``TODO(EVO...):`` regardless of the surrounding comment syntax.
# Captures the token (e.g. ``EVO-010``, ``EVO-10``, ``EVO``) and the trailing
# description text so that both ``probedev list`` and ``probedev identify``
# agree on the shape of every candidate. Public so that ``identify``'s
# rewrite step can reuse the same pattern when substituting new ids.
CANDIDATE_RE = re.compile(r"TODO\((?P<token>EVO(?:-[^)]+)?)\):\s*(?P<description>.*)")

SKIPPED_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "dist", "build"}
SKIPPED_SUFFIXES = {".md"}


@dataclass(frozen=True)
class MarkerCandidate:
    """One ``TODO(EVO-...)``-shaped line discovered in a source file."""

    path: Path
    line: int
    text: str
    token: str
    description: str


@dataclass(frozen=True)
class FileCandidates:
    """All marker candidates found in one file, alongside its raw lines.

    The full ``lines`` tuple is kept so that consumers that need surrounding
    context (for example continuation-line collection) can work from the same
    in-memory snapshot the scanner already parsed.
    """

    path: Path
    lines: tuple[str, ...]
    candidates: tuple[MarkerCandidate, ...]


@dataclass(frozen=True)
class CandidateScan:
    """Result of one workspace candidate scan."""

    files: tuple[FileCandidates, ...]
    unreadable_paths: tuple[Path, ...]


def scan_candidates(root: Path) -> CandidateScan:
    """Walk a workspace and collect every marker-candidate line.

    This is the single entry point consumed by both ``probedev list`` and
    ``probedev identify``; they agree on candidate shape because they read
    from the same scanner. Directories or files that fail to open are
    reported through :attr:`CandidateScan.unreadable_paths`; undecodable
    files are silently skipped because they cannot contain text markers.

    :param Path root: Workspace root to scan.
    """
    files: list[FileCandidates] = []
    unreadable_paths: list[Path] = []
    for path in _iter_scannable_files(root, unreadable_paths):
        try:
            lines = tuple(path.read_text(encoding="utf-8").splitlines())
        except OSError:
            unreadable_paths.append(path)
            continue
        except UnicodeDecodeError:
            continue
        candidates = tuple(_candidates_in_lines(path, lines))
        files.append(FileCandidates(path, lines, candidates))
    return CandidateScan(tuple(files), tuple(sorted(unreadable_paths)))


def _candidates_in_lines(path: Path, lines: tuple[str, ...]):
    for line_number, line in enumerate(lines, start=1):
        match = CANDIDATE_RE.search(line)
        if match is None:
            continue
        yield MarkerCandidate(
            path=path,
            line=line_number,
            text=line,
            token=match.group("token"),
            description=match.group("description").strip(),
        )


def _iter_scannable_files(root: Path, unreadable_paths: list[Path]):
    def record_unreadable(error: OSError) -> None:
        if error.filename:
            unreadable_paths.append(Path(error.filename))

    for directory, dir_names, file_names in os.walk(root, onerror=record_unreadable):
        dir_names[:] = [name for name in dir_names if name not in SKIPPED_DIRS]
        directory_path = Path(directory)
        for file_name in file_names:
            path = directory_path / file_name
            if path.suffix in SKIPPED_SUFFIXES:
                continue
            try:
                if path.is_file():
                    yield path
            except OSError:
                unreadable_paths.append(path)
