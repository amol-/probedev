from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from probedev.plan import ProbePlan


@dataclass(frozen=True)
class DoneEvolution:
    """The marker marked as done."""

    marker: str
    path: Path
    line: int


class EvolutionDoner:
    """Mark an evolution as done by changing TODO(EVO-XXX) to DONE(EVO-XXX).

    The done command finds the requested evolution marker and rewrites its
    TODO prefix to DONE, preserving the marker id, description, and all
    surrounding context. It preserves file newline style and permissions.
    """

    def done(self, root: Path, plan: ProbePlan, marker: str) -> DoneEvolution:
        """Mark one evolution as done by rewriting its marker prefix.

        :param Path root: Workspace root containing the evolution.
        :param ProbePlan plan: Current active probe plan.
        :param str marker: Evolution id to mark as done.
        """
        if not self._valid_marker(marker):
            raise ValueError(f"Invalid evolution id: {marker}")

        evolution = plan.select_evolution(marker)
        if evolution is None:
            raise LookupError(f"Evolution {marker} was not found.")

        self._rewrite_file(evolution.path, evolution.line, marker)
        return DoneEvolution(marker, evolution.path, evolution.line)

    def _valid_marker(self, marker: str) -> bool:
        return bool(re.fullmatch(r"EVO-\d{3}", marker))

    def _rewrite_file(self, path: Path, line_number: int, marker: str) -> None:
        """Rewrite one file to change TODO(EVO-XXX) to DONE(EVO-XXX).

        :param Path path: File containing the evolution marker.
        :param int line_number: Line number where the marker appears.
        :param str marker: Evolution id to mark as done.
        """
        content = path.read_bytes().decode("utf-8")
        lines = content.splitlines(keepends=True)

        # Determine newline style from the file
        newline = self._detect_newline(content)

        # Find and replace the marker on the specified line
        updated_lines = []
        for index, line in enumerate(lines, start=1):
            if index == line_number:
                # Replace TODO with DONE on this line
                updated_line = self._replace_todo_with_done(line, marker)
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)

        # Write the updated content back to the file
        updated_content = "".join(updated_lines)
        rewrite_path = path.resolve() if path.is_symlink() else path
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=rewrite_path.parent,
                encoding="utf-8",
                newline="",
                prefix=f".{rewrite_path.name}.",
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(updated_content)
            os.chmod(temp_path, path.stat().st_mode)
            os.replace(temp_path, rewrite_path)
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass

    def _detect_newline(self, content: str) -> str:
        """Detect the newline style used in a file."""
        if "\r\n" in content:
            return "\r\n"
        if "\r" in content:
            return "\r"
        return "\n"

    def _replace_todo_with_done(self, line: str, marker: str) -> str:
        """Replace TODO(EVO-XXX) with DONE(EVO-XXX) on a single line.

        :param str line: The line containing the marker.
        :param str marker: The evolution id to replace.
        """
        # Simple string replacement: TODO(EVO-XXX) -> DONE(EVO-XXX)
        return line.replace(f"TODO({marker})", f"DONE({marker})")
