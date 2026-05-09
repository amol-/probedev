from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from probedev.plan import Evolution, ProbePlan


EVOLUTION_ID_RE = re.compile(r"EVO-\d{3}")


@dataclass(frozen=True)
class EditorCommand:
    """Command line used to open one source location in an editor."""

    argv: list[str]


@dataclass(frozen=True)
class ShowResult:
    """Result of locating and opening a requested evolution marker."""

    evolution: Evolution
    command: EditorCommand


class EvolutionShower:
    """Open the source location for one pending evolution.

    Show is the navigation boundary for code-local project management: the
    parser finds the marker, the resolver chooses an editor, and this component
    invokes the editor at the marker line.
    """

    def show(self, plan: ProbePlan, marker: str, env: Mapping[str, str] | None = None) -> ShowResult:
        """Open the requested evolution marker in an editor.

        :param ProbePlan plan: Pending evolutions discovered from the workspace.
        :param str marker: Evolution id requested by the developer.
        :param Mapping[str, str] | None env: Environment used to resolve editor preferences.
        """
        result = self.prepare(plan, marker, env)
        self.launch(result)
        return result

    def prepare(self, plan: ProbePlan, marker: str, env: Mapping[str, str] | None = None) -> ShowResult:
        """Resolve the requested evolution and editor command without launching the editor.

        :param ProbePlan plan: Pending evolutions discovered from the workspace.
        :param str marker: Evolution id requested by the developer.
        :param Mapping[str, str] | None env: Environment used to resolve editor preferences.
        """
        if not EVOLUTION_ID_RE.fullmatch(marker):
            raise ValueError(f"Invalid evolution id: {marker}")

        matches = [evolution for evolution in plan.evolutions if evolution.marker == marker]
        if not matches:
            raise LookupError(f"Evolution {marker} was not found.")
        if len(matches) > 1:
            raise LookupError(f"Evolution {marker} is ambiguous.")

        evolution = matches[0]
        command = EditorResolver(env or os.environ).for_location(evolution.path, evolution.line)
        return ShowResult(evolution, command)

    def launch(self, result: ShowResult) -> None:
        """Launch the editor command from a prepared show result.

        :param ShowResult result: Resolved evolution and editor command to open.
        """
        command_line = shlex.join(result.command.argv)
        try:
            completed = subprocess.run(result.command.argv, check=False)
        except OSError as exc:
            raise RuntimeError(f"Editor launch failed; attempted command: {command_line}: {exc}") from exc
        if completed.returncode != 0:
            raise RuntimeError(
                f"Editor exited with status {completed.returncode}; attempted command: {command_line}"
            )


class EditorResolver:
    """Resolve the editor command for a file and line location."""

    def __init__(self, env: Mapping[str, str]) -> None:
        self._env = env

    def for_location(self, path: Path, line: int) -> EditorCommand:
        """Build an editor command for one file and line.

        :param Path path: Source file to open.
        :param int line: One-based line number to position the editor on.
        """
        configured = self._configured_editor()
        if configured is None:
            configured = self._default_editor()
        if configured is None:
            raise RuntimeError(
                "No editor configured and no default editor found. "
                "Set CODE_EDITOR or EDITOR to your editor command, "
                "for example: CODE_EDITOR='code --wait'."
            )
        return EditorCommand(self._argv_for(configured, path, line))

    def _configured_editor(self) -> list[str] | None:
        for name in ("CODE_EDITOR", "EDITOR"):
            value = self._env.get(name, "").strip()
            if value:
                return shlex.split(value)
        return None

    def _default_editor(self) -> list[str] | None:
        if sys.platform.startswith("win"):
            candidates = (
                "code.cmd",
                "code.exe",
                "code",
                "nvim.exe",
                "vim.exe",
                "vi.exe",
                "nvim",
                "vim",
                "vi",
            )
        else:
            candidates = ("code", "code-insiders", "codium", "nvim", "vim", "vi")

        for editor in candidates:
            resolved = shutil.which(editor)
            if resolved:
                return [resolved]
        return None

    def _argv_for(self, editor: list[str], path: Path, line: int) -> list[str]:
        executable = Path(editor[0]).name.lower().rsplit("\\", 1)[-1]
        for suffix in (".cmd", ".exe"):
            if executable.endswith(suffix):
                executable = executable.removesuffix(suffix)
        if executable in {"code", "code-insiders", "codium"}:
            return [*editor, "--goto", f"{path}:{line}"]
        if executable in {"vim", "vi", "nvim"}:
            return [*editor, f"+{line}", str(path)]
        # TODO(EVO-130): Support line-number argument templates for configured editors outside the initial code/vim family.
        return [*editor, str(path)]
