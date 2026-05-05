from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO


TODO_RE = re.compile(r"TODO\((PROBE(?:-[A-Z]+)?-\d{3})\):\s*(.+)")
TODO_CANDIDATE_RE = re.compile(r"TODO\(PROBE")
SKIPPED_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "dist", "build"}
SKIPPED_SUFFIXES = {".md"}


@dataclass(frozen=True)
class Evolution:
    marker: str
    title: str
    path: Path
    line: int


@dataclass(frozen=True)
class MalformedEvolution:
    text: str
    path: Path
    line: int


@dataclass(frozen=True)
class ProbePlan:
    evolutions: list[Evolution]
    malformed: list[MalformedEvolution]

    @property
    def sequence_names(self) -> set[str]:
        return {sequence_name(evolution.marker) for evolution in self.evolutions}


@dataclass(frozen=True)
class Workspace:
    root: Path

    @property
    def readme(self) -> Path:
        return self.root / "README.md"

    @property
    def process_readme(self) -> Path:
        return self.root / "pdd" / "README.md"

    def read_intent(self) -> str:
        return self.readme.read_text(encoding="utf-8") if self.readme.exists() else ""


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workspace = Workspace(Path(args.root).resolve())
    return args.handler(args, workspace, sys.stdout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="probe")
    parser.add_argument("--root", default=".", help="project root to inspect")
    subcommands = parser.add_subparsers(required=True)

    discuss = subcommands.add_parser("discuss", help="challenge and improve README intent")
    discuss.set_defaults(handler=run_discuss)

    refine = subcommands.add_parser("refine", help="create or evolve the executable probe")
    refine.set_defaults(handler=run_refine)

    challenge = subcommands.add_parser("challenge", help="challenge probe code against README intent")
    challenge.set_defaults(handler=run_challenge)

    list_plan = subcommands.add_parser("list", help="list ordered TODO(PROBE-...) evolutions")
    list_plan.set_defaults(handler=run_list)

    evolve = subcommands.add_parser("evolve", help="apply one ordered evolution")
    evolve.add_argument("marker", nargs="?", help="marker id to apply, such as PROBE-010")
    evolve.set_defaults(handler=run_evolve)

    return parser


def run_discuss(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    if not workspace.readme.exists():
        out.write("No README.md found. Start by writing the software intent.\n")
        return 1

    out.write(f"Discussing intent in {workspace.readme.relative_to(workspace.root)}\n")
    for prompt in [
        "Who is the first user this tool should serve?",
        "What is the first useful workflow they should complete?",
        "What belongs out of scope until the probe graduates?",
        "What does complete enough mean for the current scope?",
    ]:
        out.write(f"- {prompt}\n")
    # TODO(PROBE-010): Replace static prompts with README-aware discussion that can update intent when requested.
    return 0


def run_refine(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    intent = workspace.read_intent()
    if not intent:
        out.write("No README.md intent found. Run probe discuss after adding intent.\n")
        return 1

    plan = scan_plan(workspace.root)
    out.write("Refinement target\n")
    out.write(f"- intent: {workspace.readme.relative_to(workspace.root)}\n")
    out.write(f"- process: {workspace.process_readme.relative_to(workspace.root)}\n")
    out.write(f"- active evolutions: {len(plan.evolutions)}\n")
    out.write("Use the real project entrypoint and keep the probe executable.\n")
    # TODO(PROBE-020): Teach refine to create or evolve code through the real project entrypoint for each supported project state.
    # TODO(PROBE-030): Store the refine result as code-local TODO(PROBE-...) markers that cover every README capability.
    return 0


def run_challenge(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    problems = []
    if not workspace.readme.exists():
        problems.append("missing README.md intent")
    if not workspace.process_readme.exists():
        problems.append("missing pdd/README.md process reference")

    plan = scan_plan(workspace.root)
    duplicate_markers = sorted(
        marker
        for marker in {e.marker for e in plan.evolutions}
        if sum(1 for item in plan.evolutions if item.marker == marker) > 1
    )
    problems.extend(f"duplicate marker {marker}" for marker in duplicate_markers)
    problems.extend(f"malformed marker at {item.path.relative_to(workspace.root)}:{item.line}" for item in plan.malformed)
    if not plan.evolutions:
        problems.append("no ordered TODO(PROBE-...) evolutions found")

    if problems:
        out.write("Challenge findings\n")
        for problem in problems:
            out.write(f"- {problem}\n")
    else:
        out.write("Challenge findings\n- README, process reference, and evolution markers are present.\n")

    # TODO(PROBE-040): Compare README capabilities to executable commands and flag missing or stale evolutions.
    # TODO(PROBE-050): Validate optional BDD feature links for user-observable evolutions during challenge.
    return 0


def run_list(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    plan = scan_plan(workspace.root)
    if not plan.evolutions and not plan.malformed:
        out.write("No TODO(PROBE-...) evolutions found.\n")
        return 1

    # TODO(PROBE-055): Report malformed, duplicate, and confusing evolution sequences in list output.
    out.write("Ordered probe plan\n")
    next_by_sequence = {sequence: next_in_sequence(plan.evolutions, sequence) for sequence in plan.sequence_names}
    for evolution in plan.evolutions:
        prefix = "next" if next_by_sequence[sequence_name(evolution.marker)] == evolution else "    "
        location = f"{evolution.path.relative_to(workspace.root)}:{evolution.line}"
        out.write(f"{prefix} {evolution.marker} {location} {evolution.title}\n")
    for item in plan.malformed:
        location = f"{item.path.relative_to(workspace.root)}:{item.line}"
        out.write(f"warn MALFORMED {location} {item.text.strip()}\n")
    return 0


def run_evolve(args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    plan = scan_plan(workspace.root)
    if not plan.evolutions:
        out.write("No TODO(PROBE-...) evolutions found.\n")
        return 1
    if args.marker is None and len(plan.sequence_names) > 1:
        out.write("Multiple probe sequences found. Specify the evolution marker to apply.\n")
        return 1

    selected = select_evolution(plan.evolutions, args.marker)
    if selected is None:
        out.write(f"Evolution {args.marker} was not found.\n")
        return 1

    out.write("Selected evolution\n")
    out.write(f"- marker: {selected.marker}\n")
    out.write(f"- title: {selected.title}\n")
    out.write(f"- location: {selected.path.relative_to(workspace.root)}:{selected.line}\n")
    out.write("Apply exactly this evolution, then remove or replace its marker.\n")
    # TODO(PROBE-060): Add an agent execution boundary that applies one selected evolution and runs targeted verification.
    # TODO(PROBE-070): During evolve, add the smallest linked BDD feature only when the selected evolution needs one.
    return 0


def scan_plan(root: Path) -> ProbePlan:
    evolutions = []
    malformed = []
    for path in iter_scannable_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if match := TODO_RE.search(line):
                evolutions.append(Evolution(match.group(1), match.group(2).strip(), path, line_number))
            elif is_comment_marker_candidate(line):
                malformed.append(MalformedEvolution(line.strip(), path, line_number))
    return ProbePlan(
        sorted(evolutions, key=lambda item: (sequence_name(item.marker), item.marker, str(item.path), item.line)),
        sorted(malformed, key=lambda item: (str(item.path), item.line)),
    )


def iter_scannable_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in SKIPPED_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix not in SKIPPED_SUFFIXES:
            yield path


def select_evolution(evolutions: list[Evolution], marker: str | None) -> Evolution | None:
    if marker is None:
        return evolutions[0]
    for evolution in evolutions:
        if evolution.marker == marker:
            return evolution
    return None


def is_comment_marker_candidate(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(("#", "//", "/*", "*", "<!--")) and bool(TODO_CANDIDATE_RE.search(stripped))


def next_in_sequence(evolutions: list[Evolution], sequence: str) -> Evolution:
    return next(evolution for evolution in evolutions if sequence_name(evolution.marker) == sequence)


def sequence_name(marker: str) -> str:
    parts = marker.split("-")
    return "PROBE" if len(parts) == 2 else "-".join(parts[:-1])
