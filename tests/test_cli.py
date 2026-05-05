from __future__ import annotations

from pathlib import Path

import pytest

from probedev.cli import main


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


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("discuss", "Discussing intent in README.md"),
        ("refine", "Refinement target"),
        ("challenge", "Challenge findings"),
        ("list", "Ordered probe plan"),
        ("evolve", "Selected evolution"),
    ],
)
def test_probe_commands_smoke(project_root: Path, capsys, command: str, expected: str) -> None:
    exit_code = main(["--root", str(project_root), command])

    assert exit_code == 0
    assert expected in capsys.readouterr().out


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
