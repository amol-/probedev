from __future__ import annotations

import argparse
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO

from probedev.evolutions import AddEvolutionRequest, EvolutionRecorder
from probedev.identification import EvolutionIdentifier
from probedev.listing import EvolutionListPresenter
from probedev.plan import ProbePlan, ProbePlanParser
from probedev.show import EvolutionShower


EXIT_SUCCESS = 0
EXIT_FAILURE = 1


@dataclass(frozen=True)
class Workspace:
    """Project filesystem boundary used by command handlers."""

    root: Path

    def read_probe_plan(self) -> ProbePlan:
        return ProbePlanParser().scan(self.root)


def main(argv: list[str] | None = None) -> int:
    """Run the probedev command line interface.

    :param list[str] argv: Command arguments without the executable name.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    workspace = Workspace(Path(args.root).resolve())
    return args.handler(args, workspace, sys.stdout)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the supported probe commands."""
    parser = argparse.ArgumentParser(prog="probedev")
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

    add_command("list", "list ordered TODO(EVO-...) evolutions", run_list)
    add_command("identify", "assign unique EVO ids to pending evolutions", run_identify)
    show = add_command("show", "open one evolution marker in an editor", run_show)
    show.add_argument("marker", help="evolution id to open, such as EVO-010")
    add = add_command("add", "add one ordered evolution marker", run_add)
    add.add_argument("path", type=Path, help="source file where the evolution marker belongs")
    add.add_argument("description", nargs="+", help="evolution description to record")

    return parser


def run_show(args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Open one pending evolution in the configured editor.

    :param argparse.Namespace args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    plan = workspace.read_probe_plan()

    try:
        shower = EvolutionShower()
        result = shower.prepare(plan, args.marker)
        out.write("Opening evolution\n")
        out.write(f"- marker: {result.evolution.marker}\n")
        out.write(f"- editor: {shlex.join(result.command.argv)}\n")
        out.write(f"- location: {result.evolution.path.relative_to(workspace.root)}:{result.evolution.line}\n")
        out.flush()
        shower.launch(result)
    except ValueError as exc:
        out.write(f"Could not show evolution: {exc}\n")
        return EXIT_FAILURE
    except LookupError as exc:
        out.write(f"Could not show evolution: {exc}\n")
        return EXIT_FAILURE
    except RuntimeError as exc:
        out.write(f"Could not show evolution: {exc}\n")
        return EXIT_FAILURE
    except OSError as exc:
        out.write(f"Could not show evolution: {exc}\n")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def run_add(args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Record one new evolution marker in the probe plan.

    :param argparse.Namespace args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    plan = workspace.read_probe_plan()
    if plan.unreadable_paths:
        out.write("Could not add evolution: plan scan skipped unreadable files; fix file access and try again.\n")
        return EXIT_FAILURE

    try:
        recorded = EvolutionRecorder().record(
            workspace.root,
            plan,
            AddEvolutionRequest(" ".join(args.description), args.path),
        )
    except ValueError as exc:
        out.write(f"Could not add evolution: {exc}\n")
        return EXIT_FAILURE
    out.write("Added evolution\n")
    out.write(f"- marker: {recorded.marker}\n")
    out.write(f"- description: {recorded.description}\n")
    out.write(f"- location: {recorded.path.relative_to(workspace.root)}:{recorded.line}\n")
    out.write("Run probedev list to review the ordered plan.\n")
    return EXIT_SUCCESS


def run_identify(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Assign valid unique ids to existing pending evolution markers.

    :param argparse.Namespace _args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    result = EvolutionIdentifier().identify(workspace.root)
    if not result.identified:
        out.write("No evolution markers needed identifiers.\n")
        return EXIT_SUCCESS

    out.write("Identified evolutions\n")
    for evolution in result.identified:
        out.write(f"- marker: {evolution.marker}\n")
        out.write(f"  description: {evolution.description}\n")
        out.write(f"  location: {evolution.path.relative_to(workspace.root)}:{evolution.line}\n")
    return EXIT_SUCCESS


def run_list(_args: argparse.Namespace, workspace: Workspace, out: TextIO) -> int:
    """Print the ordered probe evolution plan.

    :param argparse.Namespace _args: Parsed command arguments.
    :param Workspace workspace: Project workspace to inspect.
    :param TextIO out: Output stream for command text.
    """
    plan = workspace.read_probe_plan()
    if not plan.evolutions and not plan.malformed and not plan.unreadable_paths:
        out.write("No TODO(EVO-...) evolutions found.\n")
        return EXIT_FAILURE

    for line in EvolutionListPresenter().format(workspace.root, plan):
        out.write(f"{line}\n")
    return EXIT_SUCCESS
