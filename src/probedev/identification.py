from __future__ import annotations

import os
import re
import tempfile
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
        conflicts = self._conflicting_candidate_indexes(candidates)
        line_counts = Counter()
        candidate_slots = []
        for candidate in candidates:
            key = (candidate.path, candidate.line)
            candidate_slots.append((candidate, line_counts[key]))
            line_counts[key] += 1
            replacements.setdefault(key, []).append(None)

        for candidate_index, (candidate, match_index) in enumerate(candidate_slots):
            if candidate.has_valid_id and candidate.token in kept_ids and candidate_index not in conflicts:
                continue
            marker = self._next_marker(next_number, used_ids)
            next_number = int(marker.rsplit("-", 1)[1]) + 10
            used_ids.add(marker)
            replacements[(candidate.path, candidate.line)][match_index] = marker
            identified.append(IdentifiedEvolution(marker, candidate.description, candidate.path, candidate.line))

        for path in {path for (path, _line), markers in replacements.items() if any(markers)}:
            self._rewrite_file(path, replacements)

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

    def _conflicting_candidate_indexes(self, candidates: list[EvolutionCandidate]) -> set[int]:
        seen = set()
        conflicts = set()
        for index, candidate in enumerate(candidates):
            if not candidate.has_valid_id:
                continue
            if candidate.token in seen:
                conflicts.add(index)
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

    def _rewrite_file(self, path: Path, replacements: dict[tuple[Path, int], list[str | None]]) -> None:
        updated = []
        for line_number, line in enumerate(
            path.read_bytes().decode("utf-8").splitlines(keepends=True),
            start=1,
        ):
            newline = ""
            if line.endswith("\r\n"):
                line, newline = line[:-2], "\r\n"
            elif line.endswith(("\n", "\r")):
                line, newline = line[:-1], line[-1]

            markers = replacements.get((path, line_number))
            if markers is not None:
                match_index = 0

                def replace(match: re.Match[str]) -> str:
                    nonlocal match_index
                    marker = markers[match_index] if match_index < len(markers) else None
                    match_index += 1
                    if marker is None:
                        return match.group(0)
                    return f"TODO({marker}): {match.group('description').strip()}"

                line = CANDIDATE_RE.sub(replace, line)
            updated.append(f"{line}{newline}")

        rewrite_path = path.resolve() if path.is_symlink() else path
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "wb",
                delete=False,
                dir=rewrite_path.parent,
                prefix=f".{rewrite_path.name}.",
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write("".join(updated).encode("utf-8"))
            os.chmod(temp_path, path.stat().st_mode)
            os.replace(temp_path, rewrite_path)
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass
