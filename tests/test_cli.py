from __future__ import annotations

import argparse
import os
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

import probedev.show
from probedev.cli import Workspace, build_parser, main, run_show
from probedev.plan import ProbePlanParser


class TrackingOutput(StringIO):
    """Output stream that records whether CLI output was flushed."""

    flushed = False

    def flush(self) -> None:
        self.flushed = True
        super().flush()


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    marker = "TODO" + "(EVO-"
    (tmp_path / "README.md").write_text("Tool intent\n", encoding="utf-8")
    pdd = tmp_path / "pdd"
    pdd.mkdir()
    (pdd / "README.md").write_text("Process intent\n", encoding="utf-8")
    source = tmp_path / "tool.py"
    source.write_text(f"# {marker}010): Add the first step.\n", encoding="utf-8")
    return tmp_path


def test_help_uses_probedev_program_name(capsys) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.splitlines()[0].startswith("usage: probedev")


def test_package_installs_probedev_command() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")

    assert 'probedev = "probedev.cli:main"' in content
    assert 'probe = "probedev.cli:main"' not in content


def test_probe_list_discovers_non_python_source_markers(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "main.go"
    source.write_text(f"// {marker}010): Add the Go step.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert "  next EVO-010 line 1 Add the Go step." in capsys.readouterr().out


def test_probe_list_reports_malformed_markers(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(f"# {marker}10): Missing zero padding.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert "warn MALFORMED tool.py:1" in capsys.readouterr().out


def test_probe_list_ignores_marker_text_inside_string_literals(tmp_path: Path, capsys) -> None:
    source = tmp_path / "tool.py"
    source.write_text('message = "TODO(EVO-010): Not a real marker."\n', encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 1
    assert capsys.readouterr().out == "No TODO(EVO-...) evolutions found.\n"


def test_probe_list_prints_ordered_evolutions(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(
        "\n".join(
            [
                f"# {marker}020): Add the second step.",
                f"# {marker}010): Add the first step.",
            ]
        ),
        encoding="utf-8",
    )
    service = tmp_path / "src" / "service.py"
    service.parent.mkdir()
    service.write_text(f"# {marker}030): Add the third step.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "src/service.py",
        "       EVO-030 line 1 Add the third step.",
        "tool.py",
        "  next EVO-010 line 2 Add the first step.",
        "       EVO-020 line 1 Add the second step.",
    ]


def test_probe_plan_skips_files_that_cannot_be_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = "TODO" + "(EVO-"
    readable = tmp_path / "readable.py"
    unreadable = tmp_path / "unreadable.py"
    readable.write_text(f"# {marker}010): Keep scanning readable files.\n", encoding="utf-8")
    unreadable.write_text(f"# {marker}020): This file cannot be read.\n", encoding="utf-8")
    original_read_text = Path.read_text

    def fake_read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if path == unreadable:
            raise PermissionError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    plan = ProbePlanParser().scan(tmp_path)

    assert [(evolution.marker, evolution.title) for evolution in plan.evolutions] == [
        ("EVO-010", "Keep scanning readable files.")
    ]
    assert plan.unreadable_paths == [unreadable]


def test_probe_list_warns_about_files_that_cannot_be_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    readable = tmp_path / "readable.py"
    unreadable = tmp_path / "unreadable.py"
    readable.write_text(f"# {marker}010): Keep scanning readable files.\n", encoding="utf-8")
    unreadable.write_text(f"# {marker}020): This file cannot be read.\n", encoding="utf-8")
    original_read_text = Path.read_text

    def fake_read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if path == unreadable:
            raise PermissionError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "next EVO-010 line 1 Keep scanning readable files." in output
    assert "warn UNREADABLE unreadable.py skipped during plan scan" in output


def test_probe_plan_records_files_that_cannot_be_checked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = "TODO" + "(EVO-"
    readable = tmp_path / "readable.py"
    unreadable = tmp_path / "unreadable.py"
    readable.write_text(f"# {marker}010): Keep scanning readable files.\n", encoding="utf-8")
    unreadable.write_text(f"# {marker}020): This file cannot be checked.\n", encoding="utf-8")
    original_is_file = Path.is_file

    def fake_is_file(path: Path) -> bool:
        if path == unreadable:
            raise PermissionError("permission denied")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", fake_is_file)

    plan = ProbePlanParser().scan(tmp_path)

    assert [(evolution.marker, evolution.title) for evolution in plan.evolutions] == [
        ("EVO-010", "Keep scanning readable files.")
    ]
    assert plan.unreadable_paths == [unreadable]


def test_probe_add_refuses_to_allocate_from_incomplete_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    target = tmp_path / "readable.py"
    unreadable = tmp_path / "unreadable.py"
    target.write_text(f"# {marker}010): Existing visible step.\n", encoding="utf-8")
    unreadable.write_text(f"# {marker}020): Existing hidden step.\n", encoding="utf-8")
    original_read_text = Path.read_text

    def fake_read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if path == unreadable:
            raise PermissionError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    exit_code = main(["--root", str(tmp_path), "add", "readable.py", "Must not allocate duplicate id."])

    assert exit_code == 1
    assert capsys.readouterr().out == (
        "Could not add evolution: plan scan skipped unreadable files; fix file access and try again.\n"
    )
    assert target.read_text(encoding="utf-8") == "# TODO(EVO-010): Existing visible step.\n"


def test_probe_add_refuses_to_allocate_when_directory_scan_is_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    target = tmp_path / "readable.py"
    blocked = tmp_path / "blocked"
    target.write_text(f"# {marker}010): Existing visible step.\n", encoding="utf-8")
    blocked.mkdir()
    original_walk = os.walk

    def fake_walk(path: Path, *args: Any, **kwargs: Any):
        onerror = kwargs.get("onerror")
        if onerror:
            onerror(PermissionError(13, "permission denied", str(blocked)))
        yield from original_walk(path, *args, **kwargs)

    monkeypatch.setattr(os, "walk", fake_walk)

    exit_code = main(["--root", str(tmp_path), "add", "readable.py", "Must not allocate hidden id."])

    assert exit_code == 1
    assert capsys.readouterr().out == (
        "Could not add evolution: plan scan skipped unreadable files; fix file access and try again.\n"
    )
    assert target.read_text(encoding="utf-8") == "# TODO(EVO-010): Existing visible step.\n"


def test_probe_add_records_new_evolution_at_end_of_file(project_root: Path, capsys) -> None:
    exit_code = main(["--root", str(project_root), "add", "tool.py", "Add README-aware refinement."])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Added evolution" in output
    assert "- marker: EVO-020" in output
    assert "- description: Add README-aware refinement." in output
    assert "Run probedev list" in output
    assert (project_root / "tool.py").read_text(encoding="utf-8").splitlines() == [
        "# TODO(EVO-010): Add the first step.",
        "",
        "# TODO(EVO-020): Add README-aware refinement.",
    ]


def test_probe_add_reports_actual_line_when_appending_to_existing_path(project_root: Path, capsys) -> None:
    target = project_root / "src" / "tool.py"
    target.parent.mkdir()
    target.write_text("print('ready')\n", encoding="utf-8")

    exit_code = main(
        [
            "--root",
            str(project_root),
            "add",
            "src/tool.py",
            "Add an appended evolution.",
        ]
    )

    assert exit_code == 0
    assert "- location: src/tool.py:3" in capsys.readouterr().out
    assert target.read_text(encoding="utf-8").splitlines() == [
        "print('ready')",
        "",
        "# TODO(EVO-020): Add an appended evolution.",
    ]


def test_probe_add_records_first_evolution_when_plan_is_empty(tmp_path: Path, capsys) -> None:
    exit_code = main(["--root", str(tmp_path), "add", "src/tool.py", "Add the first evolution."])

    assert exit_code == 0
    assert "- marker: EVO-010" in capsys.readouterr().out
    assert (tmp_path / "src" / "tool.py").read_text(encoding="utf-8") == "# TODO(EVO-010): Add the first evolution.\n"


def test_probe_show_prints_editor_command_before_launch(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    editor_calls: list[list[str]] = []
    out = TrackingOutput()

    def fake_run(argv: list[str], **_kwargs: Any) -> None:
        editor_calls.append(argv)
        assert f"- editor: code --wait --goto {project_root / 'tool.py'}:1" in out.getvalue()
        assert out.flushed

    monkeypatch.setenv("CODE_EDITOR", "code --wait")
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(probedev.show.subprocess, "run", fake_run)

    exit_code = run_show(argparse.Namespace(marker="EVO-010"), Workspace(project_root), out)

    assert exit_code == 0
    assert editor_calls == [["code", "--wait", "--goto", f"{project_root / 'tool.py'}:1"]]
    assert "Opening evolution" in out.getvalue()
    assert f"- editor: code --wait --goto {project_root / 'tool.py'}:1" in out.getvalue()
    assert "Opened evolution" not in out.getvalue()


def test_probe_show_launch_exception_does_not_print_opened_success(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = TrackingOutput()

    def fake_run(_argv: list[str], **_kwargs: Any) -> None:
        raise FileNotFoundError("code")

    monkeypatch.setenv("CODE_EDITOR", "code")
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(probedev.show.subprocess, "run", fake_run)

    exit_code = run_show(argparse.Namespace(marker="EVO-010"), Workspace(project_root), out)

    assert exit_code == 1
    assert "Opening evolution" in out.getvalue()
    assert "Could not show evolution: code" in out.getvalue()
    assert "Opened evolution" not in out.getvalue()
    assert out.flushed
