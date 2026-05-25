from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from probedev.plan import Evolution, ProbePlan, sequence_name


BOLD_CYAN = "\033[1;36m"
BOLD_YELLOW = "\033[1;33m"
BOLD_UNDERLINE_WHITE = "\033[1;4;37m"
RESET = "\033[0m"


class EvolutionListPresenter:
    """Format pending evolutions for command-line review.

    The list command exposes the project-management view: files first, then the
    pending evolutions that belong in each file. The parser still owns marker
    discovery; this presenter owns the user-visible grouping.
    """

    def format(self, root: Path, plan: ProbePlan, *, short: bool = False, color: bool = False) -> list[str]:
        """Build grouped output lines for one probe plan.

        :param Path root: Workspace root used to make paths relative.
        :param ProbePlan plan: Pending evolutions and marker issues to display.
        :param bool short: Whether to omit continuation lines from each evolution.
        :param bool color: Whether to highlight important output fields.
        """
        lines = ["Pending evolutions"]
        next_by_sequence = plan.next_by_sequence()
        evolutions_by_file = self._group_by_file(root, plan.evolutions)
        duplicate_markers = set(plan.duplicate_markers())
        duplicate_markers_by_file = defaultdict(set)
        for evolution in plan.evolutions:
            if evolution.marker in duplicate_markers:
                duplicate_markers_by_file[evolution.path.relative_to(root)].add(evolution.marker)
        malformed_by_file = defaultdict(list)
        for item in plan.malformed:
            malformed_by_file[item.path.relative_to(root)].append(item)
        paths = sorted(
            evolutions_by_file.keys() | duplicate_markers_by_file.keys() | malformed_by_file.keys(),
            key=str,
        )
        for path in paths:
            lines.append(self._highlight(str(path), color, BOLD_CYAN))
            for evolution in evolutions_by_file.get(path, []):
                prefix = "next" if next_by_sequence[sequence_name(evolution.marker)] is evolution else "    "
                plain_description_prefix = f"  {prefix} {evolution.marker} "
                marker = self._highlight(evolution.marker, color, BOLD_YELLOW)
                title = self._highlight(evolution.title, color, BOLD_UNDERLINE_WHITE)
                description_prefix = f"  {prefix} {marker} "
                description_indent = " " * len(plain_description_prefix)
                lines.append(f"{description_prefix}{title}")
                if not short:
                    lines.append(f"{description_indent}./{path}:{evolution.line}")
                    for description_line in evolution.continuation_lines:
                        lines.append(f"{description_indent}{description_line}")
            for marker in sorted(duplicate_markers_by_file.get(path, [])):
                lines.append(f"  warn DUPLICATE {marker}")
            for item in malformed_by_file.get(path, []):
                lines.append(f"  warn MALFORMED line {item.line} {item.text.strip()}")

        for path in plan.unreadable_paths:
            lines.append(f"warn UNREADABLE {path.relative_to(root)} skipped during plan scan")
        return lines

    def _highlight(self, text: str, color: bool, style: str) -> str:
        if not color:
            return text
        return f"{style}{text}{RESET}"

    def _group_by_file(self, root: Path, evolutions: list[Evolution]) -> dict[Path, list[Evolution]]:
        grouped = defaultdict(list)
        for evolution in evolutions:
            grouped[evolution.path.relative_to(root)].append(evolution)
        return {
            path: sorted(items, key=lambda item: (sequence_name(item.marker), item.marker, item.line))
            for path, items in sorted(grouped.items(), key=lambda item: str(item[0]))
        }
