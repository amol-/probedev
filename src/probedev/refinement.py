from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from probedev.plan import ProbePlan, sequence_name


@dataclass(frozen=True)
class RefinementRequest:
    """One requested evolution to record in the code-local probe plan."""

    title: str
    path: Path | None = None


@dataclass(frozen=True)
class RecordedEvolution:
    """The marker written for one refinement request."""

    marker: str
    title: str
    path: Path
    line: int


class EvolutionRecorder:
    """Record new probe evolutions as code-local TODO markers."""

    def record(self, root: Path, plan: ProbePlan, request: RefinementRequest) -> RecordedEvolution:
        """Add one ordered evolution marker without applying the evolution.

        :param Path root: Workspace root receiving the marker.
        :param ProbePlan plan: Current active probe plan.
        :param RefinementRequest request: Evolution title and optional target path.
        """
        title = request.title.strip()
        if not title:
            raise ValueError("evolution title cannot be empty")

        marker = self._next_marker(plan)
        path = self._target_path(root, plan, request)
        line = self._write_marker(path, marker, title, plan)
        return RecordedEvolution(marker, title, path, line)

    def _next_marker(self, plan: ProbePlan) -> str:
        default_numbers = [
            int(evolution.marker.rsplit("-", 1)[1])
            for evolution in plan.evolutions
            if sequence_name(evolution.marker) == "PROBE"
        ]
        return f"PROBE-{(max(default_numbers, default=0) + 10):03d}"

    def _target_path(self, root: Path, plan: ProbePlan, request: RefinementRequest) -> Path:
        if request.path is not None:
            path = (root / request.path).resolve()
            path.relative_to(root.resolve())
            return path
        if plan.evolutions:
            return plan.evolutions[-1].path
        return root / "probe_plan.py"

    def _write_marker(self, path: Path, marker: str, title: str, plan: ProbePlan) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        marker_line = f"{self._comment_prefix(path)} TODO({marker}): {title}"
        if not path.exists():
            path.write_text(f"{marker_line}\n", encoding="utf-8")
            return 1

        lines = path.read_text(encoding="utf-8").splitlines()
        insertion_index = self._insertion_index(path, plan, lines)
        if insertion_index > len(lines):
            lines.append("")
            insertion_index = len(lines)
        lines.insert(insertion_index, marker_line)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return insertion_index + 1

    def _insertion_index(self, path: Path, plan: ProbePlan, lines: list[str]) -> int:
        marker_lines = [evolution.line for evolution in plan.evolutions if evolution.path == path]
        if marker_lines:
            return max(marker_lines)
        return len(lines) + (1 if lines and lines[-1].strip() else 0)

    def _comment_prefix(self, path: Path) -> str:
        if path.suffix in {".go", ".js", ".ts", ".java", ".c", ".cpp", ".rs"}:
            return "//"
        return "#"
