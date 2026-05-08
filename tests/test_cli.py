from __future__ import annotations

import argparse
import os
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

import probedev.show
from probedev.cli import Workspace, build_parser, main, run_show
from probedev.identification import EvolutionIdentifier
from probedev.plan import ProbePlanParser
from probedev.scanning import scan_candidates


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


def test_scan_candidates_discovers_two_markers_on_one_source_line(tmp_path: Path) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(
        f"# {marker}010): Add the first step.  # {marker}020): Add the second step.\n",
        encoding="utf-8",
    )

    scan = scan_candidates(tmp_path)
    candidates = [candidate for file in scan.files for candidate in file.candidates]

    assert [(candidate.token, candidate.description, candidate.line) for candidate in candidates] == [
        ("EVO-010", "Add the first step.", 1),
        ("EVO-020", "Add the second step.", 1),
    ]


def test_probe_list_prints_two_markers_on_one_source_line(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(
        f"# {marker}010): Add the first step.  # {marker}020): Add the second step.\n",
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "tool.py",
        "  next EVO-010 line 1 Add the first step.",
        "       EVO-020 line 1 Add the second step.",
    ]


def test_probe_list_marks_only_first_identical_same_line_duplicate_as_next(
    tmp_path: Path,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(f"# {marker}010): Same. # {marker}010): Same.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "tool.py",
        "  next EVO-010 line 1 Same.",
        "       EVO-010 line 1 Same.",
        "warn DUPLICATE EVO-010",
    ]


def test_probe_list_reports_malformed_markers(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(f"# {marker}10): Missing zero padding.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert "warn MALFORMED tool.py:1" in capsys.readouterr().out


def test_probe_list_discovers_markers_inside_docstrings(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(
        "\n".join(
            [
                "def handler():",
                '    """Do the thing.',
                "",
                f"    {marker}010): Honour the env override once the parser stabilizes.",
                '    """',
                "    return None",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert "next EVO-010 line 4 Honour the env override once the parser stabilizes." in capsys.readouterr().out


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


def test_probe_list_prints_multiline_evolution_description_with_aligned_continuations(
    tmp_path: Path,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(
        "\n".join(
            [
                f"# {marker}010): recent tracked item payload validation is repetitive;",
                "# consider a structured parser/helper that preserves these precise",
                "# error messages while reducing the long sequence of type checks.",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "tool.py",
        "  next EVO-010 line 1 recent tracked item payload validation is repetitive;",
        "                      consider a structured parser/helper that preserves these precise",
        "                      error messages while reducing the long sequence of type checks.",
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
    assert target.read_text(encoding="utf-8") == f"# {marker}010): Existing visible step.\n"


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
    assert target.read_text(encoding="utf-8") == f"# {marker}010): Existing visible step.\n"


def test_probe_add_records_new_evolution_at_end_of_file(project_root: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    exit_code = main(["--root", str(project_root), "add", "tool.py", "Add README-aware refinement."])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Added evolution" in output
    assert "- marker: EVO-020" in output
    assert "- description: Add README-aware refinement." in output
    assert "Run probedev list" in output
    assert (project_root / "tool.py").read_text(encoding="utf-8").splitlines() == [
        f"# {marker}010): Add the first step.",
        "",
        f"# {marker}020): Add README-aware refinement.",
    ]


def test_probe_add_reports_actual_line_when_appending_to_existing_path(project_root: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
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
        f"# {marker}020): Add an appended evolution.",
    ]


def test_probe_add_records_first_evolution_when_plan_is_empty(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    exit_code = main(["--root", str(tmp_path), "add", "src/tool.py", "Add the first evolution."])

    assert exit_code == 0
    assert "- marker: EVO-010" in capsys.readouterr().out
    assert (tmp_path / "src" / "tool.py").read_text(encoding="utf-8") == f"# {marker}010): Add the first evolution.\n"


def test_probe_add_refuses_non_source_target_path(tmp_path: Path, capsys) -> None:
    """``add`` must refuse non-source targets so the allocator stays sound.

    The scanner's allowlist decides which files contribute to the plan. If
    ``add`` wrote a marker into a file the scanner ignores (e.g. ``.toml``),
    later ``add`` invocations would be blind to that marker and allocate the
    same id again. Symmetric contract enforcement at the ``add`` boundary
    prevents the allocator from silently producing duplicate ids.
    """
    marker = "TODO" + "(EVO-"
    config = tmp_path / "config.toml"

    exit_code = main(["--root", str(tmp_path), "add", "config.toml", "First."])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert output.startswith("Could not add evolution: ")
    assert "not a scannable source file" in output
    assert not config.exists()

    exit_code = main(["--root", str(tmp_path), "add", "tool.py", "Second."])

    assert exit_code == 0
    assert "- marker: EVO-010" in capsys.readouterr().out
    assert (tmp_path / "tool.py").read_text(encoding="utf-8") == f"# {marker}010): Second.\n"


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


def test_probe_identify_rewrites_same_line_candidates_needing_ids(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO"
    source = tmp_path / "tool.py"
    source.write_text(
        f"# {marker}-010): Keep this id.  # {marker}): Add first missing id.  "
        f"# {marker}-XXX): Add second missing id.\n",
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "identify"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Identified evolutions",
        "- marker: EVO-020",
        "  description: Add first missing id.",
        "  location: tool.py:1",
        "- marker: EVO-030",
        "  description: Add second missing id.",
        "  location: tool.py:1",
    ]
    assert source.read_text(encoding="utf-8") == (
        f"# {marker}-010): Keep this id.  # {marker}-020): Add first missing id.  "
        f"# {marker}-030): Add second missing id.\n"
    )


# TODO(EVO-160): Pin the language-agnostic / shared-scanner contract in a BDD scenario on list.feature so the behavior covered by the test below is also specified in the product-visible spec, not only in pytest.
def test_list_and_identify_agree_on_candidates_across_languages_and_shapes(tmp_path: Path) -> None:
    """Pin the EVO-080 invariant observably.

    The invariant is that ``probedev list`` and ``probedev identify`` discover
    the same set of marker candidates regardless of source language or marker
    shape. Verified against public command output, not the private scanner
    seam, so it catches drift anywhere downstream of ``scan_candidates``
    (per-command filters, language gates, regex tweaks).
    """
    marker = "TODO" + "(EVO-"
    (tmp_path / "README.md").write_text("Tool intent\n", encoding="utf-8")
    # Four candidate shapes across two languages: valid, invalid-id,
    # placeholder, and unindexed. A regex or filter regression that affects
    # any one shape — or a per-command language gate that hides the Go
    # file — breaks the equality below.
    (tmp_path / "tool.py").write_text(
        "\n".join(
            [
                f"# {marker}010): A valid marker.",
                f"# {marker}10): Missing zero padding.",
                "# TODO" + "(EVO-XXX): Placeholder id.",
                "# TODO" + "(EVO): Needs an id.",
            ]
        ),
        encoding="utf-8",
    )
    # Malformed on purpose — identify must rewrite it. If identify ever
    # gains a per-language filter that drops non-Python files, this line
    # stays malformed and identify's observable output set loses it.
    (tmp_path / "main.go").write_text(f"// {marker}20): A Go marker needing an id.\n", encoding="utf-8")

    # List: scan and collect (path, line) for every candidate list observes,
    # whether well-formed (evolutions) or not (malformed).
    plan = ProbePlanParser().scan(tmp_path)
    list_candidates = {(item.path, item.line) for item in plan.evolutions} | {
        (item.path, item.line) for item in plan.malformed
    }

    # Identify: apply the command and collect the observable (path, line)
    # set — markers it rewrote, plus already-valid markers it left alone
    # (those surface through ProbePlanParser after identify runs).
    result = EvolutionIdentifier().identify(tmp_path)
    post_plan = ProbePlanParser().scan(tmp_path)
    identify_candidates = {(item.path, item.line) for item in result.identified} | {
        (evolution.path, evolution.line) for evolution in post_plan.evolutions
    }

    assert list_candidates == identify_candidates
    # Guard against both commands silently seeing nothing: all four shapes
    # on tool.py plus the Go marker must be represented.
    assert {path.name for path, _ in list_candidates} == {"tool.py", "main.go"}
    tool_lines = {line for path, line in list_candidates if path.name == "tool.py"}
    assert tool_lines == {1, 2, 3, 4}


def test_probe_plan_ignores_non_source_extensions(tmp_path: Path) -> None:
    """Files outside the programming-language allowlist must not be scanned.

    Product contracts (``.feature``), config files, and other non-source
    text files can legitimately contain ``TODO(EVO-...)``-shaped lines
    (quoted examples, specs about the marker syntax itself). Those must
    not appear as pending evolutions.
    """
    marker = "TODO" + "(EVO-"
    (tmp_path / "spec.feature").write_text(f"# {marker}010): Not a source file.\n", encoding="utf-8")
    (tmp_path / "notes.unknownext").write_text(f"# {marker}020): Unknown extension.\n", encoding="utf-8")
    (tmp_path / "tool.py").write_text(f"# {marker}030): A real source marker.\n", encoding="utf-8")

    plan = ProbePlanParser().scan(tmp_path)

    scanned = {evolution.path.name for evolution in plan.evolutions}
    assert scanned == {"tool.py"}


def test_probe_plan_includes_recognized_extensionless_source_files(tmp_path: Path) -> None:
    """Extensionless build/infra files like ``Makefile`` are real source.

    They must be scanned for markers even though they have no suffix.
    """
    marker = "TODO" + "(EVO-"
    (tmp_path / "Makefile").write_text(f"# {marker}010): A marker in a Makefile.\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text(f"# {marker}020): A marker in a Dockerfile.\n", encoding="utf-8")

    plan = ProbePlanParser().scan(tmp_path)

    scanned = {evolution.path.name for evolution in plan.evolutions}
    assert scanned == {"Makefile", "Dockerfile"}


def test_probe_plan_ignores_marker_candidates_with_pragmas(tmp_path: Path) -> None:
    """Ignore pragmas let tests and fixtures quote marker-shaped text."""
    marker = "TODO" + "(EVO-"
    ignore_file = "probedev:" + " ignore-file"
    source = tmp_path / "tool.py"
    source.write_text(
        "\n".join(
            [
                f"# {marker}010): Keep this real marker.",
                "# probedev: ignore-next-line",
                f"# {marker}020): Ignore the next-line marker.",
                f"# {marker}030): Ignore the same-line marker.  # probedev: ignore-line",
                "# probedev: ignore-start",
                f"# {marker}040): Ignore the block marker.",
                f"# {marker}40): Ignore the malformed block marker.",
                "# probedev: ignore-end",
                f"# {marker}050): Keep the marker after the block.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "fixtures.py").write_text(
        f"# {ignore_file}\n# {marker}060): Ignore the whole file.\n",
        encoding="utf-8",
    )

    plan = ProbePlanParser().scan(tmp_path)
    result = EvolutionIdentifier().identify(tmp_path)

    assert [(evolution.marker, evolution.title) for evolution in plan.evolutions] == [
        ("EVO-010", "Keep this real marker."),
        ("EVO-050", "Keep the marker after the block."),
    ]
    assert plan.malformed == []
    assert result.identified == []
    assert f"# {marker}40): Ignore the malformed block marker." in source.read_text(encoding="utf-8")
