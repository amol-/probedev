from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from probedev.plan import Evolution, ProbePlan, sequence_name


class EvolutionListPresenter:
    """Format pending evolutions for command-line review.

    The list command exposes the project-management view: files first, then the
    pending evolutions that belong in each file. The parser still owns marker
    discovery; this presenter owns the user-visible grouping.
    """

    def format(self, root: Path, plan: ProbePlan) -> list[str]:
        """Build grouped output lines for one probe plan.

        :param Path root: Workspace root used to make paths relative.
        :param ProbePlan plan: Pending evolutions and marker issues to display.
        """
        lines = ["Pending evolutions"]
        next_by_sequence = plan.next_by_sequence()
        for path, evolutions in self._group_by_file(root, plan.evolutions).items():
            lines.append(str(path))
            for evolution in evolutions:
                prefix = "next" if next_by_sequence[sequence_name(evolution.marker)] is evolution else "    "
                description_prefix = f"  {prefix} {evolution.marker} line {evolution.line} "
                description_indent = " " * len(description_prefix)
                for index, description_line in enumerate(evolution.description_lines):
                    if index == 0:
                        lines.append(f"{description_prefix}{description_line}")
                    else:
                        lines.append(f"{description_indent}{description_line}")

        # TODO(EVO-060): Group duplicate and malformed marker warnings by file once the main grouped list shape is accepted.
        for marker in plan.duplicate_markers():
            lines.append(f"warn DUPLICATE {marker}")
        for item in plan.malformed:
            location = f"{item.path.relative_to(root)}:{item.line}"
            lines.append(f"warn MALFORMED {location} {item.text.strip()}")
        for path in plan.unreadable_paths:
            lines.append(f"warn UNREADABLE {path.relative_to(root)} skipped during plan scan")
        # TODO(EVO-070): Add explicit coverage for ignored directories and Markdown exclusions in grouped list output.
        return lines

    def _group_by_file(self, root: Path, evolutions: list[Evolution]) -> dict[Path, list[Evolution]]:
        grouped = defaultdict(list)
        for evolution in evolutions:
            grouped[evolution.path.relative_to(root)].append(evolution)
        return {
            path: sorted(items, key=lambda item: (sequence_name(item.marker), item.marker, item.line))
            for path, items in sorted(grouped.items(), key=lambda item: str(item[0]))
        }
