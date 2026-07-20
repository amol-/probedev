from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from probedev.plan import ProbePlan, sequence_name
from probedev.scanning import SKIPPED_DIRS, SOURCE_FILENAME_PREFIXES, is_source_file


@dataclass(frozen=True)
class AddEvolutionRequest:
    """User request to append one marker.

    The target can be a source file or an existing directory that receives
    the marker in Evolutions.txt. When line_number is provided, the marker
    is inserted before that line instead of appending.
    """

    description: str
    path: Path
    line_number: int | None = None


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

    The add command's architecture is intentionally narrow: parse a file or
    directory and description at the CLI boundary, scan the current plan,
    allocate the next default-sequence id, then append one marker to the
    requested file or to Evolutions.txt inside the requested directory.
    """

    def __init__(self, id_allocator: EvolutionIdAllocator | None = None) -> None:
        self._id_allocator = id_allocator or EvolutionIdAllocator()

    def record(self, root: Path, plan: ProbePlan, request: AddEvolutionRequest) -> AddedEvolution:
        """Add one ordered evolution marker without applying the evolution.

        :param Path root: Workspace root receiving the marker.
        :param ProbePlan plan: Current active probe plan.
        :param AddEvolutionRequest request: Destination file or directory and evolution description.
        """
        description = request.description.strip()
        if not description:
            raise ValueError("evolution description cannot be empty")

        path = self._target_path(root, request)
        # Contract symmetry with the scanner: the scanner only sees files
        # the allowlist accepts outside skipped directories, so the allocator's
        # next-id is only accurate over those files. Writing a marker anywhere
        # else would hide it from later scans and cause duplicate id allocation.
        if not is_source_file(path):
            raise ValueError(
                f"target path is not a scannable source file: {request.path}; "
                "use a recognized source extension (e.g. .py, .go) or filename (e.g. Makefile)."
            )
        marker = self._id_allocator.next_default_marker(plan)
        line = self._write_marker(path, marker, description, request.line_number)
        return AddedEvolution(marker, description, path, line)

    def _target_path(self, root: Path, request: AddEvolutionRequest) -> Path:
        root = root.resolve()
        path = (root / request.path).resolve()
        relative_path = path.relative_to(root)
        target_is_directory = path.is_dir()

        # Reject directory targets with line numbers
        if target_is_directory and request.line_number is not None:
            raise ValueError(
                f"target path is a directory and cannot have a line number: {request.path}"
            )

        parts_to_scan = relative_path.parts if target_is_directory else relative_path.parts[:-1]
        skipped_dir = next((part for part in parts_to_scan if part in SKIPPED_DIRS), None)
        if skipped_dir is not None:
            raise ValueError(
                f"target path is under a directory skipped by probedev list: {request.path} "
                f"(skipped directory: {skipped_dir})"
            )
        if target_is_directory:
            path = path / "Evolutions.txt"
        return path

    def _write_marker(self, path: Path, marker: str, description: str, line_number: int | None = None) -> int:
        comment_style = self._comment_style(path)
        marker_line = f"{comment_style.prefix} TODO({marker}): {description}"
        if comment_style.suffix:
            marker_line = f"{marker_line} {comment_style.suffix}"
        if not path.exists():
            # Missing scannable source files are valid add targets and seed a
            # visible plan at the requested path.
            # For new files, only line 1 is valid (insert at the start).
            if line_number is not None and line_number != 1:
                raise ValueError(f"line number {line_number} is out of range for new file; only line 1 is valid")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{marker_line}\n", encoding="utf-8")
            return 1

        content = path.read_bytes().decode("utf-8")
        newline = "\n"
        for index, character in enumerate(content):
            if character == "\n":
                newline = "\r\n" if index > 0 and content[index - 1] == "\r" else "\n"
                break
            if character == "\r":
                newline = "\r\n" if index + 1 < len(content) and content[index + 1] == "\n" else "\r"
                break

        lines = content.splitlines()

        if line_number is not None:
            # Insert before the specified line (1-indexed)
            if line_number < 1 or line_number > len(lines) + 1:
                raise ValueError(f"line number {line_number} is out of range for file with {len(lines)} lines")

            insertion_index = line_number - 1
            # Preserve leading whitespace from the target line
            if insertion_index < len(lines):
                target_line = lines[insertion_index]
                leading_whitespace = target_line[:len(target_line) - len(target_line.lstrip())]
                if leading_whitespace:
                    marker_line = f"{leading_whitespace}{marker_line}"
        else:
            insertion_index = self._insertion_index(lines)
            if insertion_index > len(lines):
                lines.append("")
                insertion_index = len(lines)

        lines.insert(insertion_index, marker_line)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=path.parent,
                encoding="utf-8",
                newline="",
                prefix=f".{path.name}.",
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(newline.join(lines) + newline)
            os.chmod(temp_path, path.stat().st_mode)
            os.replace(temp_path, path)
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass
        return insertion_index + 1

    def _insertion_index(self, lines: list[str]) -> int:
        return len(lines) + (1 if lines and lines[-1].strip() else 0)

    def _comment_style(self, path: Path) -> _CommentStyle:
        suffix = path.suffix.casefold()
        if suffix in _COMMENT_STYLE_BY_SUFFIX:
            return _COMMENT_STYLE_BY_SUFFIX[suffix]

        name = path.name.casefold()
        for filename, style in _COMMENT_STYLE_BY_FILENAME.items():
            if name == filename.casefold():
                return style
        for filename in SOURCE_FILENAME_PREFIXES:
            if name.startswith(f"{filename.casefold()}."):
                return _COMMENT_STYLE_BY_FILENAME[filename]

        if is_source_file(path):
            raise ValueError(f"no comment style configured for scannable source file: {path}")
        raise ValueError(f"target path is not a scannable source file: {path}")


@dataclass(frozen=True)
class _CommentStyle:
    """Comment delimiters used to write one complete marker line."""

    prefix: str
    suffix: str = ""


_COMMENT_STYLE_BY_SUFFIX = {
    **dict.fromkeys((".py", ".pyi"), _CommentStyle("#")),
    **dict.fromkeys((".go", ".rs"), _CommentStyle("//")),
    **dict.fromkeys((".c", ".h", ".cc", ".cpp", ".hh", ".hpp"), _CommentStyle("//")),
    **dict.fromkeys((".java", ".kt", ".kts"), _CommentStyle("//")),
    ".rb": _CommentStyle("#"),
    ".php": _CommentStyle("//"),
    **dict.fromkeys((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"), _CommentStyle("//")),
    **dict.fromkeys((".sh", ".bash", ".zsh"), _CommentStyle("#")),
    **dict.fromkeys((".swift", ".cs", ".scala"), _CommentStyle("//")),
    **dict.fromkeys((".clj", ".cljs"), _CommentStyle(";;")),
    ".hs": _CommentStyle("--"),
    **dict.fromkeys((".ex", ".exs"), _CommentStyle("#")),
    ".erl": _CommentStyle("%"),
    ".lua": _CommentStyle("--"),
    **dict.fromkeys((".pl", ".pm"), _CommentStyle("#")),
    **dict.fromkeys((".nim", ".cr"), _CommentStyle("#")),
    **dict.fromkeys((".ml", ".mli"), _CommentStyle("(*", "*)")),
    **dict.fromkeys((".fs", ".fsx", ".dart"), _CommentStyle("//")),
}
_COMMENT_STYLE_BY_FILENAME = {
    "Makefile": _CommentStyle("#"),
    "Dockerfile": _CommentStyle("#"),
    "Rakefile": _CommentStyle("#"),
    "Gemfile": _CommentStyle("#"),
    "Jenkinsfile": _CommentStyle("//"),
    "Evolutions.txt": _CommentStyle("#"),
}
