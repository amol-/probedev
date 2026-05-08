from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from probedev.scanning import CANDIDATE_RE, FileCandidates, has_ignore_pragma, scan_candidates


VALID_MARKER_RE = re.compile(r"EVO-\d{3}")


@dataclass(frozen=True)
class Evolution:
    """One well-formed code-local probe evolution marker."""

    marker: str
    title: str
    path: Path
    line: int
    continuation_lines: tuple[str, ...] = ()

    @property
    def description_lines(self) -> tuple[str, ...]:
        """Return the listable description lines for this evolution."""
        return (self.title, *self.continuation_lines)


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
        evolutions: list[Evolution] = []
        malformed: list[MalformedEvolution] = []
        scan = scan_candidates(root)
        for file in scan.files:
            self._classify_file(file, evolutions, malformed)
        return ProbePlan(
            sorted(evolutions, key=lambda item: (sequence_name(item.marker), item.marker, str(item.path), item.line)),
            sorted(malformed, key=lambda item: (str(item.path), item.line)),
            list(scan.unreadable_paths),
        )

    def _classify_file(
        self,
        file: FileCandidates,
        evolutions: list[Evolution],
        malformed: list[MalformedEvolution],
    ) -> None:
        # Candidates arrive in line order. Each well-formed marker consumes
        # continuation lines up to (but not including) the next candidate so
        # continuation scanning never crosses into the next evolution.
        candidates = list(file.candidates)
        for index, candidate in enumerate(candidates):
            next_line = candidates[index + 1].line if index + 1 < len(candidates) else len(file.lines) + 1
            if not VALID_MARKER_RE.fullmatch(candidate.token) or not candidate.description:
                malformed.append(MalformedEvolution(candidate.text.strip(), file.path, candidate.line))
                continue
            continuation = self._collect_continuation_lines(
                file.lines, candidate.line, next_line, self._marker_line_prefix(candidate.text)
            )
            evolutions.append(
                Evolution(candidate.token, candidate.description, file.path, candidate.line, continuation)
            )

    def _collect_continuation_lines(
        self,
        lines: tuple[str, ...],
        marker_line: int,
        next_candidate_line: int,
        marker_prefix: str,
    ) -> tuple[str, ...]:
        """Collect adjacent lines that share the marker's line prefix.

        A line continues the evolution description when it starts with the
        same leading prefix as the marker line — whether that prefix is a
        ``# `` comment lead, a ``// `` lead, or plain indentation inside a
        docstring. This keeps the parser language-agnostic without needing a
        comment-syntax table. Scanning stops at the next marker candidate so
        continuations never cross into another evolution.
        """
        continuation: list[str] = []
        for index in range(marker_line, next_candidate_line - 1):
            if has_ignore_pragma(lines[index]) or CANDIDATE_RE.search(lines[index]):
                break
            text = self._continuation_text(lines[index], marker_prefix)
            if text is None:
                break
            continuation.append(text)
        return tuple(continuation)

    def _marker_line_prefix(self, line: str) -> str:
        """Return the leading whitespace + optional comment lead of a marker line."""
        # TODO(EVO-140): Guard continuation-line collection when the marker prefix has no comment lead (column-0 plain-text markers and indent-only markers inside string literals) so unrelated following lines at the same indent are not swallowed as continuations.
        return line[: len(line) - len(line.lstrip())] + self._comment_lead(line.lstrip())

    def _continuation_text(self, line: str, marker_prefix: str) -> str | None:
        """Return the stripped continuation text, or None if the line is not a continuation.

        Accepts two prefix shapes so that block-style comments work:
        the original marker prefix (e.g. ``# ``, ``// ``, indentation for
        docstrings), and the block-continuation variant of a ``/* `` marker
        line which opens subsequent lines with `` * ``.
        """
        remainder = self._strip_prefix(line, marker_prefix)
        if remainder is None:
            block_prefix = self._block_continuation_prefix(marker_prefix)
            if block_prefix is None:
                return None
            remainder = self._strip_prefix(line, block_prefix)
            if remainder is None:
                return None
        stripped = remainder.strip().removesuffix("*/").removesuffix("-->").strip()
        if not stripped:
            return None
        # Treat bare docstring/block closers as end-of-continuation, not
        # as a description line. This keeps language-agnostic scanning
        # from swallowing the closing fence of a multiline string.
        if stripped in {'"""', "'''"}:
            return None
        return stripped

    def _strip_prefix(self, line: str, prefix: str) -> str | None:
        if not line.startswith(prefix):
            return None
        return line[len(prefix):]

    def _block_continuation_prefix(self, marker_prefix: str) -> str | None:
        """Derive ``/* ... *`` block continuation lead from a marker prefix.

        When the marker opened with ``    /* `` the natural continuation is
        ``     * `` — same indent, then ``*`` aligned under the ``*`` of
        ``/*``. The probe recognizes exactly that shape.
        """
        indent_len = len(marker_prefix) - len(marker_prefix.lstrip())
        lead = marker_prefix[indent_len:]
        if not lead.startswith("/*"):
            return None
        indent = marker_prefix[:indent_len]
        return indent + " " + lead[1:]

    def _comment_lead(self, stripped: str) -> str:
        for prefix in ("///", "//", "#", ";;", "--", "%", "/*", "(*", "*", "<!--"):
            if stripped.startswith(prefix):
                lead = stripped[: len(prefix)]
                rest = stripped[len(prefix):]
                trailing_space = len(rest) - len(rest.lstrip(" "))
                return lead + " " * trailing_space
        return ""


def sequence_name(marker: str) -> str:
    """Extract the sequence portion of a marker ID.

    :param str marker: Marker ID such as ``EVO-010``.
    """
    return marker.rsplit("-", 1)[0]
