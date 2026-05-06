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
    return "TODO" + "(EVO-"


def write_readme(root: Path) -> None:
    root.joinpath("README.md").write_text("Tool intent\n", encoding="utf-8")


def write_process_readme(root: Path) -> None:
    process_dir = root / "pdd"
    process_dir.mkdir(exist_ok=True)
    process_dir.joinpath("README.md").write_text("Process intent\n", encoding="utf-8")


def write_source(root: Path, text: str, filename: str = "tool.py") -> None:
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@given("a workspace with README intent")
def workspace_with_readme(command_context: CommandContext) -> None:
    write_readme(command_context.root)
    write_process_readme(command_context.root)


@given("a workspace with multiple ordered probe markers")
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
    write_source(command_context.root, f"# {marker_prefix}030): Add the third step.\n", "src/service.py")


@given("a workspace with a malformed probe marker candidate")
def workspace_with_malformed_candidate(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(command_context.root, f"# {marker_prefix}10): Missing zero padding.\n")


@given("a workspace with no probe evolution markers")
def workspace_with_no_markers(command_context: CommandContext) -> None:
    write_source(command_context.root, "print('hello')\n")


@given("a workspace with duplicate probe markers")
def workspace_with_duplicate_markers(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                f"# {marker_prefix}010): Add the first copy.",
                f"# {marker_prefix}010): Add the duplicate copy.",
            ]
        ),
    )


@given("a workspace with pending evolutions that have no ids")
def workspace_with_missing_evolution_ids(command_context: CommandContext) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                "# TODO(EVO): Add the first unnamed step.",
                "# TODO(EVO): Add the second unnamed step.",
            ]
        ),
    )


@given("a workspace with pending evolutions that have placeholder or invalid ids")
def workspace_with_placeholder_or_invalid_ids(command_context: CommandContext) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                "# TODO(EVO-XXX): Add the placeholder step.",
                "# TODO(EVO-10): Add the invalid step.",
            ]
        ),
    )


@given("a workspace with duplicate evolution ids")
def workspace_with_duplicate_evolution_ids(command_context: CommandContext) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                "# TODO(EVO-010): Keep the first duplicate.",
                "# TODO(EVO-010): Identify the second duplicate.",
            ]
        ),
    )


@given("a workspace with only valid unique evolution ids")
def workspace_with_valid_unique_evolution_ids(command_context: CommandContext) -> None:
    write_source(command_context.root, "# TODO(EVO-010): Keep this valid marker.\n")


@given("the workspace has ordered evolution markers")
def workspace_has_ordered_evolution_markers(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(command_context.root, f"# {marker_prefix}010): Add the first step.\n")


@when("the developer runs `probedev list`")
def run_list(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["list"])


@when("the developer runs `probedev add` with a file and new evolution description")
def run_add_with_description(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["add", "tool.py", "Add README-aware refinement."])


@when("the developer runs `probedev add` with a target file and new evolution description")
def run_add_with_target_file(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["add", "src/tool.py", "Add a path-specific evolution."])


@when("the developer runs `probedev identify`")
def run_identify(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["identify"])


def run_probe(
    command_context: CommandContext,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> None:
    command_context.exit_code = main(["--root", str(command_context.root), *args])
    command_context.output = capsys.readouterr().out


@then("the system records a new evolution marker")
def assert_add_records_marker(command_context: CommandContext) -> None:
    assert "Added evolution" in command_context.output
    assert "- marker: EVO-020" in command_context.output
    assert "- description: Add README-aware refinement." in command_context.output


@then("the marker is visible to `probedev list`")
def assert_recorded_marker_is_listed(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--root", str(command_context.root), "list"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "EVO-" in output
    assert "Add README-aware refinement." in output


@then("the marker is appended at the end of the requested file")
def assert_marker_appended_at_end(command_context: CommandContext) -> None:
    assert (command_context.root / "tool.py").read_text(encoding="utf-8").splitlines()[-1] == (
        "# TODO(EVO-020): Add README-aware refinement."
    )


@then("the marker is written to the requested path")
def assert_marker_written_to_requested_path(command_context: CommandContext) -> None:
    assert "- location: src/tool.py:1" in command_context.output
    assert (command_context.root / "src" / "tool.py").read_text(encoding="utf-8") == (
        "# TODO(EVO-020): Add a path-specific evolution.\n"
    )


@then("the system assigns unique evolution ids")
def assert_unique_ids_assigned(command_context: CommandContext) -> None:
    assert "Identified evolutions" in command_context.output
    assert "- marker: EVO-010" in command_context.output
    assert "- marker: EVO-020" in command_context.output
    assert "# TODO(EVO-010): Add the first unnamed step." in (command_context.root / "tool.py").read_text(
        encoding="utf-8"
    )
    assert "# TODO(EVO-020): Add the second unnamed step." in (command_context.root / "tool.py").read_text(
        encoding="utf-8"
    )


@then("the system replaces them with unique evolution ids")
def assert_invalid_ids_replaced(command_context: CommandContext) -> None:
    content = (command_context.root / "tool.py").read_text(encoding="utf-8")
    assert "# TODO(EVO-010): Add the placeholder step." in content
    assert "# TODO(EVO-020): Add the invalid step." in content


@then("each identified marker keeps its description and file location")
def assert_identified_marker_context_preserved(command_context: CommandContext) -> None:
    content = (command_context.root / "tool.py").read_text(encoding="utf-8")
    assert "Add the" in content
    assert "location: tool.py:" in command_context.output


@then("the markers are visible to `probedev list`")
def assert_identified_markers_are_listed(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--root", str(command_context.root), "list"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Pending evolutions" in output
    assert "EVO-010" in output


@then("the system keeps one existing id")
def assert_one_duplicate_id_kept(command_context: CommandContext) -> None:
    content = (command_context.root / "tool.py").read_text(encoding="utf-8")
    assert "# TODO(EVO-010): Keep the first duplicate." in content


@then("the system assigns new unique ids to the conflicting markers")
def assert_conflicting_markers_get_new_ids(command_context: CommandContext) -> None:
    content = (command_context.root / "tool.py").read_text(encoding="utf-8")
    assert "# TODO(EVO-020): Identify the second duplicate." in content


@then("the system reports that no markers needed identifiers")
def assert_no_markers_needed_identifiers(command_context: CommandContext) -> None:
    assert "No evolution markers needed identifiers." in command_context.output


@then("the system prints the pending evolution files")
def assert_pending_evolution_files(command_context: CommandContext) -> None:
    assert "Pending evolutions" in command_context.output
    assert "tool.py" in command_context.output
    assert "src/service.py" in command_context.output


@then("the first marker in the sequence is marked as next")
def assert_first_marker_next(command_context: CommandContext) -> None:
    assert "next EVO-010" in command_context.output


@then("each marker includes its id, line number, and description.")
def assert_marker_id_line_and_description(command_context: CommandContext) -> None:
    assert "EVO-010 line 2 Add the first step." in command_context.output
    assert "EVO-020 line 1 Add the second step." in command_context.output
    assert "EVO-030 line 1 Add the third step." in command_context.output


@then("the system prints a malformed marker warning")
def assert_malformed_warning(command_context: CommandContext) -> None:
    assert "warn MALFORMED tool.py:1" in command_context.output


@then("the system prints a duplicate marker warning")
def assert_duplicate_warning(command_context: CommandContext) -> None:
    assert "warn DUPLICATE EVO-010" in command_context.output


@then("the system reports that no probe evolutions were found")
def assert_no_probe_evolutions(command_context: CommandContext) -> None:
    assert "No TODO(EVO-...) evolutions found" in command_context.output


@then("the system assigns the first evolution id")
def assert_first_evolution_id(command_context: CommandContext) -> None:
    assert "- marker: EVO-010" in command_context.output


@then("the command succeeds.")
def assert_command_succeeds(command_context: CommandContext) -> None:
    assert command_context.exit_code == 0


@then("the command fails.")
def assert_command_fails(command_context: CommandContext) -> None:
    assert command_context.exit_code == 1
