from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TODO_RE = re.compile(r"TODO\((EVO-\d{3})\):\s*(.+)")
TODO_CANDIDATE_RE = re.compile(r"TODO\(EVO")
SKIPPED_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "dist", "build"}
SKIPPED_SUFFIXES = {".md"}


@dataclass(frozen=True)
class Evolution:
    """One well-formed code-local probe evolution marker."""

    marker: str
    title: str
    path: Path
    line: int


@dataclass(frozen=True)
class MalformedEvolution:
    """One comment that looks like a probe marker but does not parse."""

    text: str
    path: Path
    line: int


@dataclass(frozen=True)
class ProbePlan:
    """Ordered probe evolutions and marker issues discovered in a workspace."""

    evolutions: list[Evolution]
    malformed: list[MalformedEvolution]
    unreadable_paths: list[Path]

    @property
    def sequence_names(self) -> set[str]:
        return {sequence_name(evolution.marker) for evolution in self.evolutions}

    @property
    def has_ambiguous_default_evolution(self) -> bool:
        return len(self.sequence_names) > 1

    def duplicate_markers(self) -> list[str]:
        """List marker IDs that appear more than once in the plan."""
        return sorted(
            marker
            for marker in {e.marker for e in self.evolutions}
            if sum(1 for item in self.evolutions if item.marker == marker) > 1
        )

    def next_by_sequence(self) -> dict[str, Evolution]:
        """Map each active sequence to its first unapplied evolution."""
        return {sequence: self.next_in_sequence(sequence) for sequence in self.sequence_names}

    def next_in_sequence(self, sequence: str) -> Evolution:
        """Find the first evolution in one sequence.

        :param str sequence: Sequence name such as ``EVO``.
        """
        return next(evolution for evolution in self.evolutions if sequence_name(evolution.marker) == sequence)

    def select_evolution(self, marker: str | None) -> Evolution | None:
        """Select an explicit marker or the first ordered evolution.

        :param str | None marker: Marker ID requested by the user.
        """
        if marker is None:
            return self.evolutions[0] if self.evolutions else None
        for evolution in self.evolutions:
            if evolution.marker == marker:
                return evolution
        return None


class ProbePlanParser:
    """Parse code-local ``TODO(EVO-...)`` markers from a workspace."""

    def scan(self, root: Path) -> ProbePlan:
        """Scan a project root for active probe evolution markers.

        :param Path root: Project root to scan.
        """
        evolutions = []
        malformed = []
        unreadable_paths = []
        for path in self._iter_scannable_files(root, unreadable_paths):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                unreadable_paths.append(path)
                continue
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                self._append_marker(evolutions, malformed, path, line_number, line)
        return ProbePlan(
            sorted(evolutions, key=lambda item: (sequence_name(item.marker), item.marker, str(item.path), item.line)),
            sorted(malformed, key=lambda item: (str(item.path), item.line)),
            sorted(unreadable_paths),
        )

    def _append_marker(
        self,
        evolutions: list[Evolution],
        malformed: list[MalformedEvolution],
        path: Path,
        line_number: int,
        line: str,
    ) -> None:
        if not self._is_comment_marker_candidate(line):
            return
        if match := TODO_RE.search(line):
            evolutions.append(Evolution(match.group(1), match.group(2).strip(), path, line_number))
        else:
            malformed.append(MalformedEvolution(line.strip(), path, line_number))

    def _iter_scannable_files(self, root: Path, unreadable_paths: list[Path]) -> Iterable[Path]:
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

    def _is_comment_marker_candidate(self, line: str) -> bool:
        stripped = line.lstrip()
        return stripped.startswith(("#", "//", "/*", "*", "<!--")) and bool(TODO_CANDIDATE_RE.search(stripped))


def sequence_name(marker: str) -> str:
    """Extract the sequence portion of a marker ID.

    :param str marker: Marker ID such as ``EVO-010``.
    """
    return marker.rsplit("-", 1)[0]
