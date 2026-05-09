from __future__ import annotations

import ast
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
        docstring_end_lines = self._python_docstring_end_lines(file)
        for index, candidate in enumerate(candidates):
            next_line = candidates[index + 1].line if index + 1 < len(candidates) else len(file.lines) + 1
            if not VALID_MARKER_RE.fullmatch(candidate.token) or not candidate.description:
                malformed.append(MalformedEvolution(candidate.text.strip(), file.path, candidate.line))
                continue
            marker_prefix = self._marker_line_prefix(candidate.text)
            docstring_end_line = docstring_end_lines.get(candidate.line)
            continuation = self._collect_continuation_lines(
                file.lines,
                candidate.line,
                next_line,
                marker_prefix,
                bool(marker_prefix.strip()) or docstring_end_line is not None,
                docstring_end_line,
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
        allow_continuations: bool,
        docstring_end_line: int | None,
    ) -> tuple[str, ...]:
        """Collect adjacent lines that share the marker's line prefix.

        A line continues the evolution description when it starts with the
        same leading prefix as the marker line — whether that prefix is a
        ``# `` comment lead, a ``// `` lead, or indentation inside a docstring.
        Scanning stops at the next marker candidate, and docstring markers are
        additionally bounded to the AST docstring span.
        """
        if not allow_continuations:
            return ()
        scan_stop_line = next_candidate_line - 1
        if docstring_end_line is not None:
            scan_stop_line = min(scan_stop_line, docstring_end_line)
        continuation: list[str] = []
        for index in range(marker_line, scan_stop_line):
            if has_ignore_pragma(lines[index]) or CANDIDATE_RE.search(lines[index]):
                break
            text = self._continuation_text(
                lines[index],
                marker_prefix,
                docstring_end_line is not None and index == docstring_end_line - 1,
            )
            if text is None:
                break
            continuation.append(text)
        return tuple(continuation)

    def _marker_line_prefix(self, line: str) -> str:
        """Return the leading whitespace + optional comment lead of a marker line."""
        return line[: len(line) - len(line.lstrip())] + self._comment_lead(line.lstrip())

    def _python_docstring_end_lines(self, file: FileCandidates) -> dict[int, int]:
        """Return real Python docstring line numbers mapped to their end line."""
        if file.path.suffix not in {".py", ".pyi"}:
            return {}
        try:
            module = ast.parse("\n".join(file.lines))
        except SyntaxError:
            return {}

        docstring_end_lines: dict[int, int] = {}

        def add_first_statement_docstring(body: list[ast.stmt]) -> None:
            if not body:
                return
            statement = body[0]
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
                and statement.end_lineno is not None
            ):
                return
            for line_number in range(statement.lineno, statement.end_lineno + 1):
                docstring_end_lines[line_number] = statement.end_lineno

        add_first_statement_docstring(module.body)
        for node in ast.walk(module):
            if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef)):
                add_first_statement_docstring(node.body)
        return docstring_end_lines

    def _continuation_text(
        self,
        line: str,
        marker_prefix: str,
        strip_docstring_delimiter: bool = False,
    ) -> str | None:
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
        if strip_docstring_delimiter:
            for delimiter in ('"""', "'''"):
                if stripped.endswith(delimiter):
                    stripped = stripped[: -len(delimiter)].rstrip()
                    break
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
