from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO

from probedev.plan import ProbePlan, ProbePlanParser, sequence_name
from probedev.refinement import EvolutionRecorder, RefinementRequest


EXIT_SUCCESS = 0
EXIT_FAILURE = 1


@dataclass(frozen=True)
class Workspace:
    """Project filesystem boundary used by command handlers."""

    root: Path

    @property
    def readme(self) -> Path:
        return self.root / "README.md"

    @property
    def process_readme(self) -> Path:
        return self.root / "pdd" / "README.md"

    def read_intent(self) -> str:
        return self.readme.read_text(encoding="utf-8") if self.readme.exists() else ""

    def read_probe_plan(self) -> ProbePlan:
        return ProbePlanParser().scan(self.root)


def main(argv: list[str] | None = None) -> int:
    """Run the probe command line interface.

    :param list[str] argv: Command arguments without the executable name.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    workspace = Workspace(Path(args.root).resolve())
    return args.handler(args, workspace, sys.stdout)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the supported probe commands."""
    parser = argparse.ArgumentParser(prog="probe")
    parser.add_argument("--root", default=".", help="project root to inspect")
    subcommands = parser.add_subparsers(required=True)

    def add_command(
        name: str,
        help_text: str,
        handler: Callable[[argparse.Namespace, Workspace, TextIO], int],
    ) -> argparse.ArgumentParser:
        command = subcommands.add_parser(name, help=help_text)
        command.set_defaults(handler=handler)
        return command

    add_command("discuss", "challenge and improve README intent", run_discuss)
    refine = add_command("refine", "create or evolve the executable probe", run_refine)
    refine.add_argument("title", nargs="*", help="evolution title to add without applying it")
    refine.add_argument("--path", type=Path, help="source file where the evolution marker belongs")
    # TODO(PROBE-080): Place refine markers from README/code context and create small code anchors when no natural location exists.
    add_command("challenge", "challenge probe code against README intent", run_challenge)
    add_command("list", "list ordered TODO(PROBE-...) evolutions", run_list)
    evolve = add_command("evolve", "apply one ordered evolution", run_evolve)
    evolve.add_argument("marker", nargs="?", help="marker id to apply, such as PROBE-010")

    return parser


def run_discuss(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Print README-level product questions for the current workspace.

    :param argparse.Namespace _args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    if not workspace.readme.exists():
        out.write("No README.md found. Start by writing the software intent.\n")
        return EXIT_FAILURE

    out.write(f"Discussing intent in {workspace.readme.relative_to(workspace.root)}\n")
    for prompt in [
        "Who is the first user this tool should serve?",
        "What is the first useful workflow they should complete?",
        "What belongs out of scope until the probe graduates?",
        "What does complete enough mean for the current scope?",
    ]:
        out.write(f"- {prompt}\n")
    # TODO(PROBE-010): Replace static prompts with README-aware discussion that can update intent when requested.
    return EXIT_SUCCESS


def run_refine(args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Print the current refinement target or record one new evolution.

    :param argparse.Namespace args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    intent = workspace.read_intent()
    if not intent:
        out.write("No README.md intent found. Run probe discuss after adding intent.\n")
        return EXIT_FAILURE

    plan = workspace.read_probe_plan()
    out.write("Refinement target\n")
    out.write(f"- intent: {workspace.readme.relative_to(workspace.root)}\n")
    out.write(f"- process: {workspace.process_readme.relative_to(workspace.root)}\n")
    out.write(f"- active evolutions: {len(plan.evolutions)}\n")
    if args.title:
        try:
            recorded = EvolutionRecorder().record(workspace.root, plan, RefinementRequest(" ".join(args.title), args.path))
        except ValueError as exc:
            out.write(f"Could not record evolution: {exc}\n")
            return EXIT_FAILURE
        # TODO(PROBE-090): Support named sequences and explicit insertion between existing evolution markers.
        out.write("Recorded evolution\n")
        out.write(f"- marker: {recorded.marker}\n")
        out.write(f"- title: {recorded.title}\n")
        out.write(f"- location: {recorded.path.relative_to(workspace.root)}:{recorded.line}\n")
        out.write(f"Run probe evolve {recorded.marker} when you are ready to apply it.\n")
        return EXIT_SUCCESS

    out.write("Use the real project entrypoint and keep the probe executable.\n")
    # TODO(PROBE-020): Teach refine to create or evolve code through the real project entrypoint for each supported project state.
    # TODO(PROBE-030): Store the refine result as code-local TODO(PROBE-...) markers that cover every README capability.
    return EXIT_SUCCESS


def run_challenge(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Report baseline challenge findings for intent and probe-plan markers.

    :param argparse.Namespace _args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    problems = []
    if not workspace.readme.exists():
        problems.append("missing README.md intent")
    if not workspace.process_readme.exists():
        problems.append("missing pdd/README.md process reference")

    plan = workspace.read_probe_plan()
    problems.extend(f"duplicate marker {marker}" for marker in plan.duplicate_markers())
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
    return EXIT_FAILURE if problems else EXIT_SUCCESS


def run_list(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Print the ordered probe evolution plan.

    :param argparse.Namespace _args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    plan = workspace.read_probe_plan()
    if not plan.evolutions and not plan.malformed:
        out.write("No TODO(PROBE-...) evolutions found.\n")
        return EXIT_FAILURE

    # TODO(PROBE-055): Report malformed, duplicate, and confusing evolution sequences in list output.
    out.write("Ordered probe plan\n")
    next_by_sequence = plan.next_by_sequence()
    for evolution in plan.evolutions:
        prefix = "next" if next_by_sequence[sequence_name(evolution.marker)] == evolution else "    "
        location = f"{evolution.path.relative_to(workspace.root)}:{evolution.line}"
        out.write(f"{prefix} {evolution.marker} {location} {evolution.title}\n")
    for item in plan.malformed:
        location = f"{item.path.relative_to(workspace.root)}:{item.line}"
        out.write(f"warn MALFORMED {location} {item.text.strip()}\n")
    return EXIT_SUCCESS


def run_evolve(args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Select one evolution for the next implementation step.

    :param argparse.Namespace args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    plan = workspace.read_probe_plan()
    if not plan.evolutions:
        out.write("No TODO(PROBE-...) evolutions found.\n")
        return EXIT_FAILURE
    if args.marker is None and plan.has_ambiguous_default_evolution:
        out.write("Multiple probe sequences found. Specify the evolution marker to apply.\n")
        return EXIT_FAILURE

    selected = plan.select_evolution(args.marker)
    if selected is None:
        out.write(f"Evolution {args.marker} was not found.\n")
        return EXIT_FAILURE

    out.write("Selected evolution\n")
    out.write(f"- marker: {selected.marker}\n")
    out.write(f"- title: {selected.title}\n")
    out.write(f"- location: {selected.path.relative_to(workspace.root)}:{selected.line}\n")
    out.write("Apply exactly this evolution, then remove or replace its marker.\n")
    # TODO(PROBE-060): Add an agent execution boundary that applies one selected evolution and runs targeted verification.
    # TODO(PROBE-070): During evolve, add the smallest linked BDD feature only when the selected evolution needs one.
    return EXIT_SUCCESS
