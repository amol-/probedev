from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_bdd import given, then, when

from probedev.cli import main


@dataclass
class CommandContext:
    """State shared by one BDD scenario.

    :param Path root: Temporary project root used by the CLI.
    :param int | None exit_code: Exit code from the last command execution.
    :param str output: Captured stdout from the last command execution.
    """

    root: Path
    exit_code: int | None = None
    output: str = ""


@pytest.fixture
def command_context(tmp_path: Path) -> CommandContext:
    return CommandContext(tmp_path)


@pytest.fixture
def marker_prefix() -> str:
    return "TODO" + "(PROBE-"


def write_readme(root: Path) -> None:
    root.joinpath("README.md").write_text("Tool intent\n", encoding="utf-8")


def write_process_readme(root: Path) -> None:
    process_dir = root / "pdd"
    process_dir.mkdir(exist_ok=True)
    process_dir.joinpath("README.md").write_text("Process intent\n", encoding="utf-8")


def write_source(root: Path, text: str, filename: str = "tool.py") -> None:
    root.joinpath(filename).write_text(text, encoding="utf-8")


@given("a workspace with README intent")
def workspace_with_readme(command_context: CommandContext) -> None:
    write_readme(command_context.root)
    write_process_readme(command_context.root)


@given("a workspace without README intent")
def workspace_without_readme(command_context: CommandContext) -> None:
    write_process_readme(command_context.root)


@given("a workspace with multiple ordered probe markers")
@given("a workspace with multiple markers in one probe sequence")
def workspace_with_ordered_markers(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                f"# {marker_prefix}020): Add the second step.",
                f"# {marker_prefix}010): Add the first step.",
            ]
        ),
    )


@given("a workspace with a malformed probe marker candidate")
def workspace_with_malformed_candidate(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(command_context.root, f"# {marker_prefix}10): Missing zero padding.\n")


@given("a workspace with no probe evolution markers")
def workspace_with_no_markers(command_context: CommandContext) -> None:
    write_source(command_context.root, "print('hello')\n")


@given("a workspace with multiple probe sequences")
def workspace_with_multiple_sequences(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                f"# {marker_prefix}AUTH-010): Add login.",
                f"# {marker_prefix}SHARING-010): Add sharing.",
            ]
        ),
    )


@given("a workspace with probe evolution markers")
def workspace_with_probe_markers(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(command_context.root, f"# {marker_prefix}010): Add the first step.\n")


@given("a workspace with duplicate probe markers")
def workspace_with_duplicate_markers(command_context: CommandContext, marker_prefix: str) -> None:
    write_readme(command_context.root)
    write_process_readme(command_context.root)
    write_source(
        command_context.root,
        "\n".join(
            [
                f"# {marker_prefix}010): Add the first copy.",
                f"# {marker_prefix}010): Add the duplicate copy.",
            ]
        ),
    )


@given("the workspace contains a malformed probe marker")
def add_malformed_marker(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(command_context.root, f"# {marker_prefix}10): Missing zero padding.\n")


@given("the workspace has the process reference")
def workspace_has_process_reference(command_context: CommandContext) -> None:
    write_process_readme(command_context.root)


@given("the workspace has ordered evolution markers")
def workspace_has_ordered_evolution_markers(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(command_context.root, f"# {marker_prefix}010): Add the first step.\n")


@when("the developer runs `probe discuss`")
def run_discuss(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["discuss"])


@when("the developer runs `probe refine`")
def run_refine(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["refine"])


@when("the developer runs `probe challenge`")
def run_challenge(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["challenge"])


@when("the developer runs `probe list`")
def run_list(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["list"])


@when("the developer runs `probe evolve`")
@when("the developer runs `probe evolve` without a marker id")
def run_evolve(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["evolve"])


@when("the developer runs `probe evolve` with one marker id")
def run_evolve_with_marker(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["evolve", "PROBE-SHARING-010"])


@when("the developer runs `probe evolve` with an unknown marker id")
def run_evolve_with_unknown_marker(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["evolve", "PROBE-999"])


def run_probe(
    command_context: CommandContext,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> None:
    command_context.exit_code = main(["--root", str(command_context.root), *args])
    command_context.output = capsys.readouterr().out


@then("the system reports the README being discussed")
def assert_readme_discussed(command_context: CommandContext) -> None:
    assert "Discussing intent in README.md" in command_context.output


@then("the system prints questions about users, workflows, scope, and completion.")
def assert_discussion_questions(command_context: CommandContext) -> None:
    assert "Who is the first user" in command_context.output
    assert "first useful workflow" in command_context.output
    assert "out of scope" in command_context.output
    assert "complete enough" in command_context.output


@then("the system reports that no README was found")
def assert_no_readme(command_context: CommandContext) -> None:
    assert "No README.md found" in command_context.output


@then("the system reports the refinement target")
def assert_refinement_target(command_context: CommandContext) -> None:
    assert "Refinement target" in command_context.output


@then("the system includes the intent file, process file, and active evolution count.")
def assert_refinement_details(command_context: CommandContext) -> None:
    assert "- intent: README.md" in command_context.output
    assert "- process: pdd/README.md" in command_context.output
    assert "- active evolutions:" in command_context.output


@then("the system tells the developer to add intent before refinement")
def assert_refine_requires_intent(command_context: CommandContext) -> None:
    assert "No README.md intent found" in command_context.output


@then("the system prints challenge findings")
def assert_challenge_findings(command_context: CommandContext) -> None:
    assert "Challenge findings" in command_context.output


@then("the findings include missing README intent")
def assert_missing_readme_finding(command_context: CommandContext) -> None:
    assert "missing README.md intent" in command_context.output


@then("the findings include the malformed marker location")
def assert_malformed_location(command_context: CommandContext) -> None:
    assert "malformed marker at tool.py:1" in command_context.output


@then("the findings include the duplicate marker id")
def assert_duplicate_marker(command_context: CommandContext) -> None:
    assert "duplicate marker PROBE-010" in command_context.output


@then("the system reports that the baseline probe materials are present")
def assert_baseline_present(command_context: CommandContext) -> None:
    assert "README, process reference, and evolution markers are present" in command_context.output


@then("the system prints the ordered probe plan")
def assert_ordered_probe_plan(command_context: CommandContext) -> None:
    assert "Ordered probe plan" in command_context.output


@then("the first marker in the sequence is marked as next")
def assert_first_marker_next(command_context: CommandContext) -> None:
    assert "next PROBE-010" in command_context.output


@then("each marker includes its file location and title.")
def assert_marker_location_and_title(command_context: CommandContext) -> None:
    assert "tool.py:2 Add the first step." in command_context.output
    assert "tool.py:1 Add the second step." in command_context.output


@then("the system prints a malformed marker warning")
def assert_malformed_warning(command_context: CommandContext) -> None:
    assert "warn MALFORMED tool.py:1" in command_context.output


@then("the system reports that no probe evolutions were found")
def assert_no_probe_evolutions(command_context: CommandContext) -> None:
    assert "No TODO(PROBE-...) evolutions found" in command_context.output


@then("the system selects the first ordered marker")
def assert_first_evolution_selected(command_context: CommandContext) -> None:
    assert "- marker: PROBE-010" in command_context.output


@then("the system tells the developer to apply exactly that evolution.")
def assert_apply_exactly_selected(command_context: CommandContext) -> None:
    assert "Apply exactly this evolution" in command_context.output


@then("the system selects the requested marker")
def assert_requested_marker_selected(command_context: CommandContext) -> None:
    assert "- marker: PROBE-SHARING-010" in command_context.output


@then("the system prints its title and location.")
def assert_selected_title_and_location(command_context: CommandContext) -> None:
    assert "- title: Add sharing." in command_context.output
    assert "- location: tool.py:2" in command_context.output


@then("the system tells the developer to specify the evolution marker")
def assert_requires_marker(command_context: CommandContext) -> None:
    assert "Multiple probe sequences found" in command_context.output


@then("the system reports that the evolution was not found")
def assert_evolution_not_found(command_context: CommandContext) -> None:
    assert "Evolution PROBE-999 was not found" in command_context.output


@then("the command succeeds.")
def assert_command_succeeds(command_context: CommandContext) -> None:
    assert command_context.exit_code == 0


@then("the command fails.")
def assert_command_fails(command_context: CommandContext) -> None:
    assert command_context.exit_code == 1
