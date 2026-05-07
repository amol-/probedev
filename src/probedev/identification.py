from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from probedev.scanning import CANDIDATE_RE, scan_candidates


VALID_MARKER_RE = re.compile(r"EVO-\d{3}")


@dataclass(frozen=True)
class IdentifiedEvolution:
    """One marker that received a valid unique evolution id."""

    marker: str
    description: str
    path: Path
    line: int


@dataclass(frozen=True)
class IdentifyResult:
    """Summary of one identify command run."""

    identified: list[IdentifiedEvolution]


@dataclass(frozen=True)
class EvolutionCandidate:
    """One scannable evolution marker candidate in a source file."""

    token: str
    description: str
    path: Path
    line: int
    text: str

    @property
    def has_valid_id(self) -> bool:
        return bool(VALID_MARKER_RE.fullmatch(self.token))


class EvolutionIdentifier:
    """Assign valid unique ids to existing pending evolution markers.

    The probe keeps this intentionally file-oriented: scan source comments,
    decide which markers need identifiers, rewrite only those marker tokens,
    and report the ids that were assigned.
    """

    def identify(self, root: Path) -> IdentifyResult:
        """Assign ids to markers that are missing, invalid, placeholder, or conflicting.

        :param Path root: Workspace root to scan and update.
        """
        candidates = self._scan_candidates(root)
        kept_ids = self._kept_valid_ids(candidates)
        next_number = self._next_number(kept_ids)
        identified = []
        replacements = {}
        used_ids = set(kept_ids)

        for candidate in candidates:
            if candidate.has_valid_id and candidate.token in kept_ids and candidate not in self._conflicting_candidates(candidates):
                continue
            marker = self._next_marker(next_number, used_ids)
            next_number = int(marker.rsplit("-", 1)[1]) + 10
            used_ids.add(marker)
            replacements[(candidate.path, candidate.line)] = marker
            identified.append(IdentifiedEvolution(marker, candidate.description, candidate.path, candidate.line))

        for path in {path for path, _line in replacements}:
            self._rewrite_file(path, replacements)

        # TODO(EVO-090): Preserve file newline style and permissions when identify rewrites source files.
        # TODO(EVO-100): Report unchanged valid markers and rewritten conflicts separately for clearer command output.
        return IdentifyResult(identified)

    def _scan_candidates(self, root: Path) -> list[EvolutionCandidate]:
        candidates = [
            EvolutionCandidate(
                shared.token,
                shared.description,
                shared.path,
                shared.line,
                shared.text,
            )
            for file in scan_candidates(root).files
            for shared in file.candidates
        ]
        return sorted(candidates, key=lambda item: (str(item.path), item.line))

    def _kept_valid_ids(self, candidates: list[EvolutionCandidate]) -> set[str]:
        counts = Counter(candidate.token for candidate in candidates if candidate.has_valid_id)
        kept = set()
        for candidate in candidates:
            if candidate.has_valid_id and candidate.token not in kept and counts[candidate.token] >= 1:
                kept.add(candidate.token)
        return kept

    def _conflicting_candidates(self, candidates: list[EvolutionCandidate]) -> set[EvolutionCandidate]:
        seen = set()
        conflicts = set()
        for candidate in candidates:
            if not candidate.has_valid_id:
                continue
            if candidate.token in seen:
                conflicts.add(candidate)
            else:
                seen.add(candidate.token)
        return conflicts

    def _next_number(self, used_ids: set[str]) -> int:
        numbers = [int(marker.rsplit("-", 1)[1]) for marker in used_ids]
        return max(numbers, default=0) + 10

    def _next_marker(self, next_number: int, used_ids: set[str]) -> str:
        marker = f"EVO-{next_number:03d}"
        while marker in used_ids:
            next_number += 10
            marker = f"EVO-{next_number:03d}"
        return marker

    def _rewrite_file(self, path: Path, replacements: dict[tuple[Path, int], str]) -> None:
        lines = path.read_text(encoding="utf-8").splitlines()
        updated = []
        for line_number, line in enumerate(lines, start=1):
            marker = replacements.get((path, line_number))
            if marker is None:
                updated.append(line)
            else:
                updated.append(
                    CANDIDATE_RE.sub(
                        lambda match: f"TODO({marker}): {match.group('description').strip()}",
                        line,
                        count=1,
                    )
                )
        path.write_text("\n".join(updated) + "\n", encoding="utf-8")
