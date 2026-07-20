from __future__ import annotations

from dataclasses import dataclass, field
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
    command_outputs: dict[str, str] = field(default_factory=dict)
    command_exit_codes: dict[str, int] = field(default_factory=dict)


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


@given("a workspace with a plain text Evolutions.txt evolution body")
def workspace_with_plain_text_evolutions_body(command_context: CommandContext, marker_prefix: str) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                f"{marker_prefix}010): Validate repository durability expectations with operations",
                "Why:",
                "- The probe assumes local durable storage is acceptable.",
                "Done:",
                "- Follow-up evolutions are moved into specific files.",
                "",
                "This note is outside the evolution body.",
            ]
        ),
        "Evolutions.txt",
    )


@given("a workspace with a source evolution body followed by code")
def workspace_with_source_evolution_body_followed_by_code(
    command_context: CommandContext,
    marker_prefix: str,
) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                f"# {marker_prefix}010): Replace in-memory storage with persistence.",
                "# Why:",
                "# - The probe loses data after restart.",
                "def build_repository():",
                "    return MemoryRepository()",
            ]
        ),
    )


@given("a workspace with ignored marker-shaped fixture text")
def workspace_with_ignored_marker_shaped_fixture_text(
    command_context: CommandContext,
    marker_prefix: str,
) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                f"# {marker_prefix}010): Keep the real marker.",
                "# probedev: ignore-next-line",
                f"# {marker_prefix}020): Ignore the quoted fixture marker.",
                "# probedev: ignore-start",
                f"# {marker_prefix}030): Ignore the block fixture marker.",
                "# probedev: ignore-end",
            ]
        ),
    )


@given("a workspace with evolution marker candidates across source languages and marker shapes")
def workspace_with_cross_language_candidate_shapes(
    command_context: CommandContext,
    marker_prefix: str,
) -> None:
    write_source(
        command_context.root,
        "\n".join(
            [
                f"# {marker_prefix}010): A valid marker.",
                f"# {marker_prefix}10): Missing zero padding.",
                "# TODO" + "(EVO-XXX): Placeholder id.",
                "# TODO" + "(EVO): Needs an id.",
            ]
        ),
    )
    write_source(command_context.root, f"// {marker_prefix}20): A Go marker needing an id.\n", "main.go")


# probedev: ignore-start
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


@given("the workspace has an existing source directory")
def workspace_has_existing_source_directory(command_context: CommandContext) -> None:
    command_context.root.joinpath("src").mkdir()


@given("the workspace has a source file with content")
def workspace_has_source_file_with_content(command_context: CommandContext) -> None:
    write_source(
        command_context.root, "def build():\n    return value\n", "src/target.py"
    )


@given("the workspace has no file at the target path")
def workspace_has_no_file_at_target_path(command_context: CommandContext) -> None:
    assert not (command_context.root / "src" / "new.py").exists()


# probedev: ignore-end


@given("the developer has a configured code editor")
def developer_has_code_editor(command_context: CommandContext, monkeypatch: pytest.MonkeyPatch) -> None:
    install_editor_spy(command_context, monkeypatch)
    monkeypatch.setenv("CODE_EDITOR", "code")
    monkeypatch.delenv("EDITOR", raising=False)


@given("the developer has `CODE_EDITOR` configured as `zed --reuse-window {path}:{line}`")
def developer_has_code_editor_line_template(
    command_context: CommandContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_editor_spy(command_context, monkeypatch)
    monkeypatch.setenv("CODE_EDITOR", "zed --reuse-window {path}:{line}")
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


@when("the developer runs `probedev list --short`")
def run_short_list(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["list", "--short"])


@when("the developer runs `probedev list --color`")
def run_color_list(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["list", "--color"])


@when("the developer runs `probedev list` and then `probedev identify`")
def run_list_then_identify(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["list"])
    assert command_context.exit_code is not None
    command_context.command_outputs["list"] = command_context.output
    command_context.command_exit_codes["list"] = command_context.exit_code

    run_probe(command_context, capsys, ["identify"])
    assert command_context.exit_code is not None
    command_context.command_outputs["identify"] = command_context.output
    command_context.command_exit_codes["identify"] = command_context.exit_code

    run_probe(command_context, capsys, ["list"])
    assert command_context.exit_code is not None
    command_context.command_outputs["post-identify-list"] = command_context.output
    command_context.command_exit_codes["post-identify-list"] = command_context.exit_code
    command_context.exit_code = command_context.command_exit_codes["identify"]
    command_context.output = command_context.command_outputs["identify"]


@when("the developer runs `probedev add` with a file and new evolution description")
def run_add_with_description(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["add", "tool.py", "Add README-aware refinement."])


@when("the developer runs `probedev add` with a target file and new evolution description")
def run_add_with_target_file(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["add", "src/tool.py", "Add a path-specific evolution."])


@when("the developer runs `probedev add` with a directory and new evolution description")
def run_add_with_directory(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(command_context, capsys, ["add", "src", "Add a directory evolution."])


@when("the developer runs `probedev add` with a file:line target and new evolution description")
def run_add_with_file_line_target(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(
        command_context,
        capsys,
        ["add", "src/target.py:2", "Add a line-specific evolution."],
    )


@when("the developer runs `probedev add` with a directory:line target and new evolution description")
def run_add_with_directory_line_target(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(
        command_context, capsys, ["add", "src:2", "Add a line-specific evolution."]
    )


@when("the developer runs `probedev add` with a file:line target where line is not a number")
def run_add_with_non_numeric_line_target(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(
        command_context,
        capsys,
        ["add", "src/target.py:not-a-number", "Add a line-specific evolution."],
    )


@when("the developer runs `probedev add` with a file:line target where line is out of range")
def run_add_with_out_of_range_line_target(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(
        command_context,
        capsys,
        ["add", "src/target.py:4", "Add a line-specific evolution."],
    )


@when("the developer runs `probedev add` with a file:line target where line is greater than 1 for a non-existent file")
def run_add_with_missing_file_line_target(command_context: CommandContext, capsys: pytest.CaptureFixture[str]) -> None:
    run_probe(
        command_context,
        capsys,
        ["add", "src/new.py:2", "Add a line-specific evolution."],
    )


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

    def fake_run(argv: list[str], **_kwargs: Any) -> probedev.show.subprocess.CompletedProcess[list[str]]:
        assert command_context.editor_calls is not None
        command_context.editor_calls.append(argv)
        return probedev.show.subprocess.CompletedProcess(argv, 0)

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


@then("the system opens `CODE_EDITOR` using the configured line template for `EVO-020`")
def assert_code_editor_template_opened(command_context: CommandContext) -> None:
    argv = assert_editor_opened(command_context)
    assert argv == ["zed", "--reuse-window", f"{command_context.root / 'tool.py'}:2"]


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
    assert "Editor launch failed" in command_context.output
    assert f"attempted command: code --goto {command_context.root / 'tool.py'}:2" in command_context.output


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
    recorded = {}
    for line in command_context.output.splitlines():
        if line.startswith("- marker: "):
            recorded["marker"] = line.removeprefix("- marker: ")
        elif line.startswith("- description: "):
            recorded["description"] = line.removeprefix("- description: ")
        elif line.startswith("- location: "):
            recorded["path"] = line.removeprefix("- location: ").rsplit(":", 1)[0]

    exit_code = main(["--root", str(command_context.root), "list"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert recorded["path"] in output
    assert recorded["marker"] in output
    assert recorded["description"] in output


# probedev: ignore-start
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


@then("the system creates or appends to Evolutions.txt in that directory")
def assert_evolutions_txt_created_or_appended(command_context: CommandContext) -> None:
    assert "- location: src/Evolutions.txt:1" in command_context.output
    evolutions_file = command_context.root / "src" / "Evolutions.txt"
    assert evolutions_file.exists()
    content = evolutions_file.read_text(encoding="utf-8")
    assert "# TODO(EVO-020): Add a directory evolution." in content


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


@then("each marker includes its id, source location, and description.")
def assert_marker_id_location_and_description(command_context: CommandContext) -> None:
    assert "EVO-010 Add the first step." in command_context.output
    assert "./tool.py:2" in command_context.output
    assert "EVO-020 Add the second step." in command_context.output
    assert "./tool.py:1" in command_context.output
    assert "EVO-030 Add the third step." in command_context.output
    assert "./src/service.py:1" in command_context.output


@then("the system prints a malformed marker warning")
def assert_malformed_warning(command_context: CommandContext) -> None:
    output_lines = command_context.output.splitlines()
    file_index = output_lines.index("tool.py")
    assert output_lines[file_index + 1] == "  warn MALFORMED line 1 # TODO(EVO-10): Missing zero padding."


@then("the system prints a duplicate marker warning")
def assert_duplicate_warning(command_context: CommandContext) -> None:
    assert "warn DUPLICATE EVO-010" in command_context.output


@then("the system prints the readable evolution marker")
def assert_readable_marker_listed(command_context: CommandContext) -> None:
    assert "next EVO-010 Existing visible step." in command_context.output
    assert "./tool.py:1" in command_context.output


@then("the system prints an unreadable file warning")
def assert_unreadable_warning(command_context: CommandContext) -> None:
    assert "warn UNREADABLE unreadable.py skipped during plan scan" in command_context.output


@then("the system prints the marker id and source location once")
def assert_multiline_marker_and_location_once(command_context: CommandContext) -> None:
    assert command_context.output.count("EVO-010") == 1
    assert command_context.output.count("./tool.py:1") == 1


@then("the system prints the marker id once")
def assert_marker_id_once(command_context: CommandContext) -> None:
    assert command_context.output.count("EVO-010") == 1
    assert "EVO-010 line " not in command_context.output


@then("the system prints all continuation lines as part of the same evolution")
def assert_multiline_continuations_printed(command_context: CommandContext) -> None:
    assert "recent tracked item payload validation is repetitive;" in command_context.output
    assert "consider a structured parser/helper that preserves these precise" in command_context.output
    assert "error messages while reducing the long sequence of type checks." in command_context.output


@then("the continuation lines are aligned with the evolution description column")
def assert_multiline_continuations_aligned(command_context: CommandContext) -> None:
    output_lines = command_context.output.splitlines()
    first = next(line for line in output_lines if "EVO-010" in line)
    continuation = next(line for line in output_lines if "consider a structured parser/helper" in line)
    expected_indent = first.index("recent tracked")
    assert continuation.index("consider") == expected_indent


@then("the system prints only the first line of the evolution")
def assert_short_list_omits_evolution_body(command_context: CommandContext) -> None:
    assert "recent tracked item payload validation is repetitive;" in command_context.output
    assert "consider a structured parser/helper" not in command_context.output
    assert "error messages while reducing the long sequence of type checks." not in command_context.output


@then("the system highlights the evolution file, id, and title")
def assert_color_list_highlights_heading_fields(command_context: CommandContext) -> None:
    assert "\033[1;36mtool.py\033[0m" in command_context.output
    assert "\033[1;33mEVO-010\033[0m" in command_context.output
    assert "\033[1;4;37mrecent tracked item payload validation is repetitive;\033[0m" in command_context.output


@then("the system leaves the source location unhighlighted")
def assert_color_list_leaves_location_plain(command_context: CommandContext) -> None:
    assert "               ./tool.py:1" in command_context.output
    assert "\033[1;36m./tool.py:1\033[0m" not in command_context.output
    assert "\033[1;33m./tool.py:1\033[0m" not in command_context.output
    assert "\033[1;4;37m./tool.py:1\033[0m" not in command_context.output


@then("the system prints the Evolutions.txt evolution body")
def assert_plain_text_evolutions_body_printed(command_context: CommandContext) -> None:
    assert "Evolutions.txt" in command_context.output
    assert "Validate repository durability expectations with operations" in command_context.output
    assert "Why:" in command_context.output
    assert "- The probe assumes local durable storage is acceptable." in command_context.output
    assert "Done:" in command_context.output
    assert "- Follow-up evolutions are moved into specific files." in command_context.output


@then("the system does not include text after the blank line")
def assert_text_after_blank_line_omitted(command_context: CommandContext) -> None:
    assert "This note is outside the evolution body." not in command_context.output


@then("the system prints the source evolution comment body")
def assert_source_evolution_comment_body_printed(command_context: CommandContext) -> None:
    assert "Replace in-memory storage with persistence." in command_context.output
    assert "Why:" in command_context.output
    assert "- The probe loses data after restart." in command_context.output


@then("the system does not include executable code after the evolution body")
def assert_executable_code_after_body_omitted(command_context: CommandContext) -> None:
    assert "def build_repository" not in command_context.output
    assert "return MemoryRepository" not in command_context.output


@then("the system reports that no probe evolutions were found")
def assert_no_probe_evolutions(command_context: CommandContext) -> None:
    assert "No TODO(EVO-...) evolutions found" in command_context.output


@then("the system reports that add could not scan the complete plan")
def assert_add_reports_incomplete_plan(command_context: CommandContext) -> None:
    assert "Could not add evolution: plan scan skipped unreadable files" in command_context.output


@then("the system prints only the non-ignored evolution marker")
def assert_only_non_ignored_marker_printed(command_context: CommandContext) -> None:
    assert "EVO-010 Keep the real marker." in command_context.output
    assert "./tool.py:1" in command_context.output
    assert "EVO-020" not in command_context.output
    assert "EVO-030" not in command_context.output


@then("list and identify observe the same source marker candidate locations")
def assert_list_and_identify_candidate_locations_agree(command_context: CommandContext) -> None:
    def list_locations(output: str, *, include_malformed: bool) -> set[tuple[str, int]]:
        locations: set[tuple[str, int]] = set()
        current_path: str | None = None
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("warn MALFORMED "):
                if include_malformed:
                    line_number = stripped.split()[3]
                    assert current_path is not None
                    locations.add((current_path, int(line_number)))
                continue
            if line and not line.startswith(" ") and not line.startswith("warn ") and line != "Pending evolutions":
                current_path = line
                continue
            if stripped.startswith("./"):
                path, line_number = stripped.removeprefix("./").rsplit(":", 1)
                locations.add((path, int(line_number)))
        return locations

    def identify_locations(output: str) -> set[tuple[str, int]]:
        locations: set[tuple[str, int]] = set()
        for line in output.splitlines():
            if line.startswith("  location: "):
                path, line_number = line.removeprefix("  location: ").rsplit(":", 1)
                locations.add((path, int(line_number)))
        return locations

    list_candidates = list_locations(command_context.command_outputs["list"], include_malformed=True)
    identify_candidates = identify_locations(command_context.command_outputs["identify"]) | list_locations(
        command_context.command_outputs["post-identify-list"], include_malformed=False
    )

    assert command_context.command_exit_codes["list"] == 0
    assert command_context.command_exit_codes["post-identify-list"] == 0
    assert list_candidates == identify_candidates
    assert list_candidates == {("tool.py", 1), ("tool.py", 2), ("tool.py", 3), ("tool.py", 4), ("main.go", 1)}


@then("no new marker is appended to the requested file")
def assert_no_marker_appended(command_context: CommandContext) -> None:
    assert (command_context.root / "tool.py").read_text(encoding="utf-8") == (
        "# TODO(EVO-010): Existing visible step.\n"
    )


@then("the system inserts the marker before the specified line")
def assert_marker_inserted_before_specified_line(command_context: CommandContext) -> None:
    assert "- location: src/target.py:2" in command_context.output
    assert (command_context.root / "src" / "target.py").read_text(encoding="utf-8").splitlines() == [
        "def build():",
        "    # TODO(EVO-020): Add a line-specific evolution.",
        "    return value",
    ]


@then("the marker uses the target line's leading whitespace")
def assert_marker_uses_target_indentation(command_context: CommandContext) -> None:
    marker_line = (
        (command_context.root / "src" / "target.py")
        .read_text(encoding="utf-8")
        .splitlines()[1]
    )
    assert marker_line.startswith("    ")


@then("the system reports that directories cannot have line numbers")
def assert_directory_line_number_rejected(command_context: CommandContext) -> None:
    assert "directory and cannot have a line number" in command_context.output


@then("no Evolutions.txt is created")
def assert_no_evolutions_file_created(command_context: CommandContext) -> None:
    assert not (command_context.root / "src" / "Evolutions.txt").exists()


@then("the system reports the invalid line number")
def assert_invalid_line_number_reported(command_context: CommandContext) -> None:
    assert "invalid line number 'not-a-number'" in command_context.output
    assert (command_context.root / "src" / "target.py").read_text(encoding="utf-8") == "def build():\n    return value\n"


@then("the system reports the line number is out of range")
def assert_out_of_range_line_number_reported(command_context: CommandContext) -> None:
    assert "line number 4 is out of range for file with 2 lines" in command_context.output
    assert (command_context.root / "src" / "target.py").read_text(encoding="utf-8") == "def build():\n    return value\n"


@then("the system reports the line number is out of range for the new file")
def assert_missing_file_line_number_rejected(command_context: CommandContext) -> None:
    assert "line number 2 is out of range for new file; only line 1 is valid" in command_context.output


@then("no file is created")
def assert_no_file_created(command_context: CommandContext) -> None:
    assert not (command_context.root / "src").exists()


# probedev: ignore-end


@then("the system assigns the first evolution id")
def assert_first_evolution_id(command_context: CommandContext) -> None:
    assert "- marker: EVO-010" in command_context.output


@then("the command succeeds.")
def assert_command_succeeds(command_context: CommandContext) -> None:
    assert command_context.exit_code == 0


@then("the command fails.")
def assert_command_fails(command_context: CommandContext) -> None:
    assert command_context.exit_code == 1
