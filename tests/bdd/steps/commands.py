from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
from typing import Any

import pytest
from pytest_bdd import given, then, when

from probedev.cli import main
import probedev.show


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
    editor_calls: list[list[str]] | None = None


@pytest.fixture
def command_context(tmp_path: Path) -> CommandContext:
    return CommandContext(tmp_path)


@pytest.fixture
def marker_prefix() -> str:
    return "TODO" + "(EVO-"


# TODO(EVO-170): Route every remaining marker-shaped fixture literal in this file through `marker_prefix` (or the split-string convention) so `probedev list` stops reporting BDD fixture strings as DUPLICATE/MALFORMED evolutions on self-scan.


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


@given("a workspace with a readable marker and an unreadable source file")
def workspace_with_unreadable_source(
    command_context: CommandContext,
    marker_prefix: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreadable = command_context.root / "unreadable.py"
    write_source(command_context.root, f"# {marker_prefix}010): Existing visible step.\n")
    write_source(command_context.root, f"# {marker_prefix}020): Existing hidden step.\n", "unreadable.py")
    original_read_text = Path.read_text

    def fake_read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if path == unreadable:
            raise PermissionError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)


@given("a workspace with a multiline evolution marker")
def workspace_with_multiline_evolution_marker(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                f"# {marker_prefix}010): recent tracked item payload validation is repetitive;",
                "# consider a structured parser/helper that preserves these precise",
                "# error messages while reducing the long sequence of type checks.",
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


@given("a workspace with ordered evolution markers")
def workspace_with_ordered_evolution_markers(command_context: CommandContext) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                "# TODO(EVO-010): Add the first step.",
                "# TODO(EVO-020): Add the second step.",
            ]
        ),
    )


@given("a workspace with only valid unique evolution ids")
def workspace_with_valid_unique_evolution_ids(command_context: CommandContext) -> None:
    write_source(command_context.root, "# TODO(EVO-010): Keep this valid marker.\n")


@given("the workspace has ordered evolution markers")
def workspace_has_ordered_evolution_markers(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(command_context.root, f"# {marker_prefix}010): Add the first step.\n")


@given("the developer has a configured code editor")
def developer_has_code_editor(command_context: CommandContext, monkeypatch: pytest.MonkeyPatch) -> None:
    install_editor_spy(command_context, monkeypatch)
    monkeypatch.setenv("CODE_EDITOR", "code")
    monkeypatch.delenv("EDITOR", raising=False)


@given("the configured editor launch fails")
def configured_editor_launch_fails(command_context: CommandContext, monkeypatch: pytest.MonkeyPatch) -> None:
    command_context.editor_calls = []

    def fake_run(argv: list[str], **_kwargs: Any) -> None:
        assert command_context.editor_calls is not None
        command_context.editor_calls.append(argv)
        raise FileNotFoundError("code")

    monkeypatch.setattr(probedev.show.subprocess, "run", fake_run)


@given("the developer has both `CODE_EDITOR` and `EDITOR` configured")
def developer_has_both_editors(command_context: CommandContext, monkeypatch: pytest.MonkeyPatch) -> None:
    install_editor_spy(command_context, monkeypatch)
    monkeypatch.setenv("CODE_EDITOR", "code")
    monkeypatch.setenv("EDITOR", "vim")


@given("the developer has `EDITOR` configured")
def developer_has_editor(command_context: CommandContext, monkeypatch: pytest.MonkeyPatch) -> None:
    install_editor_spy(command_context, monkeypatch)
    monkeypatch.setenv("EDITOR", "vim")


@given("the developer does not have `CODE_EDITOR` configured")
def developer_has_no_code_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODE_EDITOR", raising=False)


@given("the developer has no configured editor")
def developer_has_no_configured_editor(command_context: CommandContext, monkeypatch: pytest.MonkeyPatch) -> None:
    install_editor_spy(command_context, monkeypatch)
    monkeypatch.delenv("CODE_EDITOR", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)


@given("the workspace has an available default editor")
def workspace_has_default_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probedev.show.shutil, "which", lambda editor: "/usr/bin/vim" if editor == "vim" else None)


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


@when("the developer runs `probedev show EVO-020`")
def run_show_existing_evolution(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["show", "EVO-020"])


@when("the developer runs `probedev show EVO-999`")
def run_show_missing_evolution(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["show", "EVO-999"])


@when("the developer runs `probedev show EVO-010`")
def run_show_duplicate_evolution(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["show", "EVO-010"])


@when("the developer runs `probedev show EVO`")
def run_show_invalid_evolution(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["show", "EVO"])


def install_editor_spy(command_context: CommandContext, monkeypatch: pytest.MonkeyPatch) -> None:
    command_context.editor_calls = []

    def fake_run(argv: list[str], **_kwargs: Any) -> None:
        assert command_context.editor_calls is not None
        command_context.editor_calls.append(argv)

    monkeypatch.setattr(probedev.show.subprocess, "run", fake_run)


def run_probe(
    command_context: CommandContext,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> None:
    command_context.exit_code = main(["--root", str(command_context.root), *args])
    command_context.output = capsys.readouterr().out


@then("the system opens the configured editor at the file containing `EVO-020`")
def assert_configured_editor_opened(command_context: CommandContext) -> None:
    assert_editor_opened(command_context)


@then("the system opens `CODE_EDITOR` at the file containing `EVO-020`")
def assert_code_editor_opened(command_context: CommandContext) -> None:
    argv = assert_editor_opened(command_context)
    assert argv[0] == "code"


@then("the system opens `EDITOR` at the file containing `EVO-020`")
def assert_editor_opened_from_editor(command_context: CommandContext) -> None:
    argv = assert_editor_opened(command_context)
    assert argv[0] == "vim"


@then("the system opens the available default editor at the file containing `EVO-020`")
def assert_default_editor_opened(command_context: CommandContext) -> None:
    argv = assert_editor_opened(command_context)
    assert argv[0] == "/usr/bin/vim"


@then("the editor is positioned on the `EVO-020` marker line")
def assert_editor_positioned_on_marker_line(command_context: CommandContext) -> None:
    argv = assert_editor_opened(command_context)
    assert any(str(command_context.root / "tool.py") in arg for arg in argv)
    assert any(":2" in arg or arg == "+2" for arg in argv)


@then("the system reports the selected editor command")
def assert_selected_editor_command_reported(command_context: CommandContext) -> None:
    argv = assert_editor_opened(command_context)
    assert "Opening evolution" in command_context.output
    assert f"- editor: {shlex.join(argv)}" in command_context.output
    assert "Opened evolution" not in command_context.output


@then("the system reports the editor launch error")
def assert_editor_launch_error_reported(command_context: CommandContext) -> None:
    assert "Could not show evolution: code" in command_context.output


@then("the system does not print an after-launch success message")
def assert_after_launch_success_message_absent(command_context: CommandContext) -> None:
    assert "Opened evolution" not in command_context.output


@then("the system reports that `EVO-999` was not found")
def assert_missing_evolution_reported(command_context: CommandContext) -> None:
    assert "Evolution EVO-999 was not found" in command_context.output


@then("the system reports that `EVO-010` is ambiguous")
def assert_ambiguous_evolution_reported(command_context: CommandContext) -> None:
    assert "Evolution EVO-010 is ambiguous" in command_context.output


@then("the system reports that the requested evolution id is invalid")
def assert_invalid_evolution_reported(command_context: CommandContext) -> None:
    assert "Invalid evolution id: EVO" in command_context.output


@then("no editor is opened")
def assert_no_editor_opened(command_context: CommandContext) -> None:
    assert command_context.editor_calls in (None, [])


def assert_editor_opened(command_context: CommandContext) -> list[str]:
    assert command_context.editor_calls is not None
    assert len(command_context.editor_calls) == 1
    return command_context.editor_calls[0]


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


@then("the system prints the readable evolution marker")
def assert_readable_marker_listed(command_context: CommandContext) -> None:
    assert "next EVO-010 line 1 Existing visible step." in command_context.output


@then("the system prints an unreadable file warning")
def assert_unreadable_warning(command_context: CommandContext) -> None:
    assert "warn UNREADABLE unreadable.py skipped during plan scan" in command_context.output


@then("the system prints the marker id and marker line number once")
def assert_multiline_marker_columns_once(command_context: CommandContext) -> None:
    assert command_context.output.count("EVO-010 line 1") == 1


@then("the system prints all continuation lines as part of the same evolution")
def assert_multiline_continuations_printed(command_context: CommandContext) -> None:
    assert "recent tracked item payload validation is repetitive;" in command_context.output
    assert "consider a structured parser/helper that preserves these precise" in command_context.output
    assert "error messages while reducing the long sequence of type checks." in command_context.output


@then("the continuation lines are aligned with the evolution description column")
def assert_multiline_continuations_aligned(command_context: CommandContext) -> None:
    output_lines = command_context.output.splitlines()
    first = next(line for line in output_lines if "EVO-010 line 1" in line)
    continuation = next(line for line in output_lines if "consider a structured parser/helper" in line)
    expected_indent = first.index("recent tracked")
    assert continuation.index("consider") == expected_indent


@then("the system reports that no probe evolutions were found")
def assert_no_probe_evolutions(command_context: CommandContext) -> None:
    assert "No TODO(EVO-...) evolutions found" in command_context.output


@then("the system reports that add could not scan the complete plan")
def assert_add_reports_incomplete_plan(command_context: CommandContext) -> None:
    assert "Could not add evolution: plan scan skipped unreadable files" in command_context.output


@then("no new marker is appended to the requested file")
def assert_no_marker_appended(command_context: CommandContext) -> None:
    assert (command_context.root / "tool.py").read_text(encoding="utf-8") == (
        "# TODO(EVO-010): Existing visible step.\n"
    )


@then("the system assigns the first evolution id")
def assert_first_evolution_id(command_context: CommandContext) -> None:
    assert "- marker: EVO-010" in command_context.output


@then("the command succeeds.")
def assert_command_succeeds(command_context: CommandContext) -> None:
    assert command_context.exit_code == 0


@then("the command fails.")
def assert_command_fails(command_context: CommandContext) -> None:
    assert command_context.exit_code == 1
