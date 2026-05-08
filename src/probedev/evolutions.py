from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from probedev.plan import ProbePlan, sequence_name
from probedev.scanning import is_source_file


@dataclass(frozen=True)
class AddEvolutionRequest:
    """User request to append one evolution marker to a source file."""

    description: str
    path: Path


@dataclass(frozen=True)
class AddedEvolution:
    """The marker written for one add command."""

    marker: str
    description: str
    path: Path
    line: int


class EvolutionIdAllocator:
    """Allocate new marker ids for the default evolution sequence."""

    def next_default_marker(self, plan: ProbePlan) -> str:
        """Choose the next ``EVO-XXX`` id from a complete, unambiguous plan.

        :param ProbePlan plan: Current active probe plan.
        """
        duplicates = [marker for marker in plan.duplicate_markers() if sequence_name(marker) == "EVO"]
        if duplicates:
            raise ValueError(
                "cannot allocate next EVO id while duplicate default-sequence markers exist: "
                + ", ".join(duplicates)
            )

        default_numbers = [
            int(evolution.marker.rsplit("-", 1)[1])
            for evolution in plan.evolutions
            if sequence_name(evolution.marker) == "EVO"
        ]
        return f"EVO-{(max(default_numbers, default=0) + 10):03d}"


class EvolutionRecorder:
    """Append new probe evolutions as code-local TODO markers.

    The add command's architecture is intentionally narrow: parse a file and
    description at the CLI boundary, scan the current plan, allocate the next
    default-sequence id, then append one marker to the requested file.
    """

    def __init__(self, id_allocator: EvolutionIdAllocator | None = None) -> None:
        self._id_allocator = id_allocator or EvolutionIdAllocator()

    def record(self, root: Path, plan: ProbePlan, request: AddEvolutionRequest) -> AddedEvolution:
        """Add one ordered evolution marker without applying the evolution.

        :param Path root: Workspace root receiving the marker.
        :param ProbePlan plan: Current active probe plan.
        :param AddEvolutionRequest request: Destination file and evolution description.
        """
        description = request.description.strip()
        if not description:
            raise ValueError("evolution description cannot be empty")

        path = self._target_path(root, request)
        # Contract symmetry with the scanner: the scanner only sees files
        # the allowlist accepts, so the allocator's next-id is only accurate
        # over those files. Writing a marker into any other file would hide
        # it from later scans and cause duplicate id allocation.
        if not is_source_file(path):
            raise ValueError(
                f"target path is not a scannable source file: {request.path}; "
                "use a recognized source extension (e.g. .py, .go) or filename (e.g. Makefile)."
            )
        marker = self._id_allocator.next_default_marker(plan)
        line = self._write_marker(path, marker, description)
        return AddedEvolution(marker, description, path, line)

    def _target_path(self, root: Path, request: AddEvolutionRequest) -> Path:
        path = (root / request.path).resolve()
        path.relative_to(root.resolve())
        return path

    def _write_marker(self, path: Path, marker: str, description: str) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        marker_line = f"{self._comment_prefix(path)} TODO({marker}): {description}"
        if not path.exists():
            # TODO(EVO-020): Confirm whether add should create missing files or require the target file to already exist.
            path.write_text(f"{marker_line}\n", encoding="utf-8")
            return 1

        lines = path.read_text(encoding="utf-8").splitlines()
        insertion_index = self._insertion_index(lines)
        if insertion_index > len(lines):
            lines.append("")
            insertion_index = len(lines)
        lines.insert(insertion_index, marker_line)
        # TODO(EVO-030): Preserve original file newline style and write atomically once the append boundary graduates from probe to production.
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return insertion_index + 1

    def _insertion_index(self, lines: list[str]) -> int:
        return len(lines) + (1 if lines and lines[-1].strip() else 0)

    def _comment_prefix(self, path: Path) -> str:
        # TODO(EVO-040): Replace suffix guessing with a small language comment-style table that covers every scannable source type.
        if path.suffix in {".go", ".js", ".ts", ".java", ".c", ".cpp", ".rs"}:
            return "//"
        return "#"
