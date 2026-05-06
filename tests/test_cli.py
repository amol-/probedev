from __future__ import annotations

from pathlib import Path

import pytest

from probedev.cli import build_parser, main


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    marker = "TODO" + "(PROBE-"
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
    marker = "TODO" + "(PROBE-"
    source = tmp_path / "main.go"
    source.write_text(f"// {marker}010): Add the Go step.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert "next PROBE-010 main.go:1 Add the Go step." in capsys.readouterr().out


def test_probe_list_reports_malformed_markers(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(PROBE-"
    source = tmp_path / "tool.py"
    source.write_text(f"# {marker}10): Missing zero padding.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert "warn MALFORMED tool.py:1" in capsys.readouterr().out


def test_probe_list_ignores_marker_text_inside_string_literals(tmp_path: Path, capsys) -> None:
    source = tmp_path / "tool.py"
    source.write_text('message = "TODO(PROBE-010): Not a real marker."\n', encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 1
    assert capsys.readouterr().out == "No TODO(PROBE-...) evolutions found.\n"


def test_probe_challenge_fails_when_findings_are_present(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(PROBE-"
    source = tmp_path / "tool.py"
    source.write_text(f"# {marker}10): Missing zero padding.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "challenge"])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "missing README.md intent" in output
    assert "malformed marker at tool.py:1" in output


def test_probe_challenge_fails_when_duplicate_markers_are_present(project_root: Path, capsys) -> None:
    marker = "TODO" + "(PROBE-"
    source = project_root / "tool.py"
    source.write_text(
        "\n".join(
            [
                f"# {marker}010): Add the first copy.",
                f"# {marker}010): Add the duplicate copy.",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--root", str(project_root), "challenge"])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "duplicate marker PROBE-010" in output


def test_probe_evolve_requires_marker_for_multiple_sequences(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(PROBE-"
    source = tmp_path / "tool.py"
    source.write_text(
        "\n".join(
            [
                f"# {marker}AUTH-010): Add login.",
                f"# {marker}SHARING-010): Add sharing.",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "evolve"])

    assert exit_code == 1
    assert "Multiple probe sequences found" in capsys.readouterr().out


def test_probe_evolve_selects_first_marker_in_default_sequence(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(PROBE-"
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

    exit_code = main(["--root", str(tmp_path), "evolve"])

    assert exit_code == 0
    assert "- marker: PROBE-010" in capsys.readouterr().out


def test_probe_evolve_selects_explicit_marker_across_multiple_sequences(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(PROBE-"
    source = tmp_path / "tool.py"
    source.write_text(
        "\n".join(
            [
                f"# {marker}AUTH-010): Add login.",
                f"# {marker}SHARING-010): Add sharing.",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "evolve", "PROBE-SHARING-010"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Selected evolution",
        "- marker: PROBE-SHARING-010",
        "- title: Add sharing.",
        "- location: tool.py:2",
        "Apply exactly this evolution, then remove or replace its marker.",
    ]


def test_probe_list_prints_ordered_evolutions(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(PROBE-"
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

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Ordered probe plan",
        "next PROBE-010 tool.py:2 Add the first step.",
        "     PROBE-020 tool.py:1 Add the second step.",
    ]


def test_probe_refine_records_new_evolution_without_applying_it(project_root: Path, capsys) -> None:
    exit_code = main(["--root", str(project_root), "refine", "Add README-aware refinement."])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Recorded evolution" in output
    assert "- marker: PROBE-020" in output
    assert "- title: Add README-aware refinement." in output
    assert "Run probedev evolve PROBE-020" in output
    assert "TODO(PROBE-020): Add README-aware refinement." in (project_root / "tool.py").read_text(encoding="utf-8")


def test_probe_refine_records_new_evolution_in_requested_path(project_root: Path, capsys) -> None:
    exit_code = main(
        [
            "--root",
            str(project_root),
            "refine",
            "--path",
            "src/tool.py",
            "Add a path-specific evolution.",
        ]
    )

    assert exit_code == 0
    assert "- location: src/tool.py:1" in capsys.readouterr().out
    assert (project_root / "src" / "tool.py").read_text(encoding="utf-8") == (
        "# TODO(PROBE-020): Add a path-specific evolution.\n"
    )


def test_probe_refine_reports_actual_line_when_appending_to_existing_path(project_root: Path, capsys) -> None:
    target = project_root / "src" / "tool.py"
    target.parent.mkdir()
    target.write_text("print('ready')\n", encoding="utf-8")

    exit_code = main(
        [
            "--root",
            str(project_root),
            "refine",
            "--path",
            "src/tool.py",
            "Add an appended evolution.",
        ]
    )

    assert exit_code == 0
    assert "- location: src/tool.py:3" in capsys.readouterr().out
    assert target.read_text(encoding="utf-8").splitlines() == [
        "print('ready')",
        "",
        "# TODO(PROBE-020): Add an appended evolution.",
    ]
