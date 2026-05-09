from __future__ import annotations

import argparse
import os
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

import probedev.evolutions
import probedev.show
from probedev.cli import Workspace, build_parser, main, run_show
from probedev.identification import EvolutionIdentifier
from probedev.plan import ProbePlanParser
from probedev.scanning import SOURCE_FILENAME_PREFIXES, SOURCE_FILENAMES, SOURCE_SUFFIXES, scan_candidates


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


def test_scan_candidates_discovers_two_ocaml_markers_on_one_line(tmp_path: Path) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.ml"
    source.write_text(
        f"(* {marker}010): Add the first step. *) (* {marker}020): Add the second step. *)\n",
        encoding="utf-8",
    )

    scan = scan_candidates(tmp_path)
    candidates = [candidate for file in scan.files for candidate in file.candidates]

    assert [(candidate.token, candidate.description, candidate.line) for candidate in candidates] == [
        ("EVO-010", "Add the first step.", 1),
        ("EVO-020", "Add the second step.", 1),
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
        "  warn DUPLICATE EVO-010",
    ]


def test_probe_list_reports_malformed_markers_by_file(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(f"# {marker}10): Missing zero padding.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "tool.py",
        f"  warn MALFORMED line 1 # {marker}10): Missing zero padding.",
    ]


def test_probe_list_groups_duplicate_and_malformed_warnings_by_file(
    tmp_path: Path,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text(f"# {marker}010): Shared marker in first file.\n", encoding="utf-8")
    second.write_text(
        f"# {marker}010): Shared marker in second file.\n"
        f"# {marker}10): Missing zero padding in second file.\n",
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "first.py",
        "  next EVO-010 line 1 Shared marker in first file.",
        "  warn DUPLICATE EVO-010",
        "second.py",
        "       EVO-010 line 1 Shared marker in second file.",
        "  warn DUPLICATE EVO-010",
        f"  warn MALFORMED line 2 # {marker}10): Missing zero padding in second file.",
    ]


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


def test_probe_list_grouped_output_excludes_ignored_directories_and_markdown(
    tmp_path: Path,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "src" / "tool.py"
    source.parent.mkdir()
    source.write_text(f"# {marker}020): Keep the real source marker.\n", encoding="utf-8")
    hidden_venv = tmp_path / ".venv"
    hidden_venv.mkdir()
    (hidden_venv / "hidden.py").write_text(f"# {marker}010): Hidden virtualenv marker.\n", encoding="utf-8")
    hidden_cache = tmp_path / "__pycache__"
    hidden_cache.mkdir()
    (hidden_cache / "cached.py").write_text(f"# {marker}030): Hidden cache marker.\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(f"# {marker}040): Markdown marker text.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "src/tool.py",
        "  next EVO-020 line 1 Keep the real source marker.",
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


def test_probe_plan_does_not_collect_continuations_for_no_comment_non_docstring_markers(
    tmp_path: Path,
) -> None:
    marker = "TODO" + "(EVO-"
    plain = tmp_path / "plain.py"
    plain.write_text(
        "\n".join(
            [
                f"{marker}010): Add the plain step.",
                "unrelated plain text at column zero",
            ]
        ),
        encoding="utf-8",
    )
    string_literal = tmp_path / "fixture.py"
    string_literal.write_text(
        "\n".join(
            [
                'EXAMPLE = """',
                f"    {marker}020): Add the fixture step.",
                "    unrelated fixture text at the same indent",
                '    """',
            ]
        ),
        encoding="utf-8",
    )

    plan = ProbePlanParser().scan(tmp_path)

    assert [(evolution.marker, evolution.title, evolution.continuation_lines) for evolution in plan.evolutions] == [
        ("EVO-010", "Add the plain step.", ()),
        ("EVO-020", "Add the fixture step.", ()),
    ]


def test_probe_plan_does_not_collect_continuations_for_standalone_triple_quote_assignment(
    tmp_path: Path,
) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "fixture.py"
    source.write_text(
        "\n".join(
            [
                "EXAMPLE = (",
                '    """',
                f"    {marker}010): Add the fixture step.",
                "    unrelated fixture text at the same indent",
                '    """',
                ")",
            ]
        ),
        encoding="utf-8",
    )

    plan = ProbePlanParser().scan(tmp_path)

    assert [(evolution.marker, evolution.title, evolution.continuation_lines) for evolution in plan.evolutions] == [
        ("EVO-010", "Add the fixture step.", ()),
    ]


def test_probe_plan_collects_continuations_for_docstring_markers(
    tmp_path: Path,
) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(
        "\n".join(
            [
                "def handler():",
                '    """Do the thing.',
                "",
                f"    {marker}010): Honour the env override once the parser stabilizes.",
                "    keep this docstring detail with the evolution.",
                '    """',
                "    return None",
            ]
        ),
        encoding="utf-8",
    )

    plan = ProbePlanParser().scan(tmp_path)

    assert [(evolution.marker, evolution.title, evolution.continuation_lines) for evolution in plan.evolutions] == [
        (
            "EVO-010",
            "Honour the env override once the parser stabilizes.",
            ("keep this docstring detail with the evolution.",),
        )
    ]


def test_probe_plan_bounds_docstring_continuations_when_closing_quote_shares_final_text(
    tmp_path: Path,
) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(
        "\n".join(
            [
                "def handler():",
                '    """Do the thing.',
                f"    {marker}010): Keep the docstring detail.",
                '    final detail shares the closing delimiter."""',
                "    return 'executable code is not continuation text'",
            ]
        ),
        encoding="utf-8",
    )

    plan = ProbePlanParser().scan(tmp_path)

    assert [(evolution.marker, evolution.title, evolution.continuation_lines) for evolution in plan.evolutions] == [
        (
            "EVO-010",
            "Keep the docstring detail.",
            ("final detail shares the closing delimiter.",),
        )
    ]


def test_probe_list_does_not_swallow_ocaml_code_after_one_line_marker(
    tmp_path: Path,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.ml"
    source.write_text(
        "\n".join(
            [
                f"(* {marker}010): Add the OCaml step. *)",
                "let value = 1",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "tool.ml",
        "  next EVO-010 line 1 Add the OCaml step.",
    ]


def test_probe_list_does_not_swallow_clojure_code_after_line_comment_marker(
    tmp_path: Path,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.clj"
    source.write_text(
        "\n".join(
            [
                f";; {marker}010): Add the Clojure step.",
                "(def value 1)",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "tool.clj",
        "  next EVO-010 line 1 Add the Clojure step.",
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


def test_probe_add_refuses_to_allocate_with_duplicate_default_sequence_marker(
    tmp_path: Path,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    target = tmp_path / "tool.py"
    original = f"# {marker}010): First duplicate.\n# {marker}010): Second duplicate.\n"
    target.write_text(original, encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "add", "tool.py", "Must not allocate after duplicates."])

    assert exit_code == 1
    assert capsys.readouterr().out == (
        "Could not add evolution: cannot allocate next EVO id while duplicate default-sequence markers exist: "
        "EVO-010\n"
    )
    assert target.read_text(encoding="utf-8") == original


ADD_COMMENT_STYLE_SUFFIX_CASES = [
    (".py", "#", ""),
    (".pyi", "#", ""),
    (".go", "//", ""),
    (".rs", "//", ""),
    (".c", "//", ""),
    (".h", "//", ""),
    (".cc", "//", ""),
    (".cpp", "//", ""),
    (".hh", "//", ""),
    (".hpp", "//", ""),
    (".java", "//", ""),
    (".kt", "//", ""),
    (".kts", "//", ""),
    (".rb", "#", ""),
    (".php", "//", ""),
    (".js", "//", ""),
    (".jsx", "//", ""),
    (".ts", "//", ""),
    (".tsx", "//", ""),
    (".mjs", "//", ""),
    (".cjs", "//", ""),
    (".sh", "#", ""),
    (".bash", "#", ""),
    (".zsh", "#", ""),
    (".swift", "//", ""),
    (".cs", "//", ""),
    (".scala", "//", ""),
    (".clj", ";;", ""),
    (".cljs", ";;", ""),
    (".hs", "--", ""),
    (".ex", "#", ""),
    (".exs", "#", ""),
    (".erl", "%", ""),
    (".lua", "--", ""),
    (".pl", "#", ""),
    (".pm", "#", ""),
    (".nim", "#", ""),
    (".cr", "#", ""),
    (".ml", "(*", "*)"),
    (".mli", "(*", "*)"),
    (".fs", "//", ""),
    (".fsx", "//", ""),
    (".dart", "//", ""),
]
ADD_COMMENT_STYLE_FILENAME_CASES = [
    ("Makefile", "#", ""),
    ("Dockerfile", "#", ""),
    ("Rakefile", "#", ""),
    ("Gemfile", "#", ""),
    ("Jenkinsfile", "//", ""),
]


def test_probe_add_comment_style_cases_cover_scanner_allowlist() -> None:
    assert {suffix for suffix, _prefix, _suffix in ADD_COMMENT_STYLE_SUFFIX_CASES} == SOURCE_SUFFIXES
    filename_cases = {name for name, _prefix, _suffix in ADD_COMMENT_STYLE_FILENAME_CASES}
    assert filename_cases == SOURCE_FILENAMES
    assert SOURCE_FILENAME_PREFIXES <= filename_cases


@pytest.mark.parametrize(("suffix", "prefix", "comment_suffix"), ADD_COMMENT_STYLE_SUFFIX_CASES)
def test_probe_add_uses_language_comment_style_for_scannable_suffix(
    tmp_path: Path,
    capsys,
    suffix: str,
    prefix: str,
    comment_suffix: str,
) -> None:
    marker = "TODO" + "(EVO-"

    exit_code = main(["--root", str(tmp_path), "add", f"target{suffix}", "Add a style-specific evolution."])

    assert exit_code == 0
    assert "- marker: EVO-010" in capsys.readouterr().out
    assert (tmp_path / f"target{suffix}").read_text(encoding="utf-8") == (
        f"{prefix} {marker}010): Add a style-specific evolution."
        f"{f' {comment_suffix}' if comment_suffix else ''}\n"
    )


@pytest.mark.parametrize(("file_name", "prefix", "comment_suffix"), ADD_COMMENT_STYLE_FILENAME_CASES)
def test_probe_add_uses_language_comment_style_for_scannable_filename(
    tmp_path: Path,
    capsys,
    file_name: str,
    prefix: str,
    comment_suffix: str,
) -> None:
    marker = "TODO" + "(EVO-"

    exit_code = main(["--root", str(tmp_path), "add", file_name, "Add a filename-specific evolution."])

    assert exit_code == 0
    assert "- marker: EVO-010" in capsys.readouterr().out
    assert (tmp_path / file_name).read_text(encoding="utf-8") == (
        f"{prefix} {marker}010): Add a filename-specific evolution."
        f"{f' {comment_suffix}' if comment_suffix else ''}\n"
    )


@pytest.mark.parametrize("target_name", ["target.PY", "makefile", "Dockerfile.prod", "Makefile.inc"])
def test_probe_add_records_common_source_filename_casing_and_variants(
    tmp_path: Path,
    capsys,
    target_name: str,
) -> None:
    marker = "TODO" + "(EVO-"

    exit_code = main(["--root", str(tmp_path), "add", target_name, "Add a variant source marker."])

    assert exit_code == 0
    assert "- marker: EVO-010" in capsys.readouterr().out
    assert (tmp_path / target_name).read_text(encoding="utf-8") == (
        f"# {marker}010): Add a variant source marker.\n"
    )

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        target_name,
        "  next EVO-010 line 1 Add a variant source marker.",
    ]


@pytest.mark.parametrize("target_name", ["Dockerfile.md", "Dockerfile.prod.md", "Makefile.toml", "Makefile.inc.json"])
def test_probe_add_rejects_prefixed_doc_config_variants(
    tmp_path: Path,
    capsys,
    target_name: str,
) -> None:
    exit_code = main(["--root", str(tmp_path), "add", target_name, "Add a hidden marker."])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert output.startswith("Could not add evolution: target path is not a scannable source file:")
    assert not (tmp_path / target_name).exists()


@pytest.mark.parametrize(
    ("suffix", "prefix", "comment_suffix"),
    [case for case in ADD_COMMENT_STYLE_SUFFIX_CASES if case[2]],
)
def test_probe_add_suffix_style_marker_lists_requested_description(
    tmp_path: Path,
    capsys,
    suffix: str,
    prefix: str,
    comment_suffix: str,
) -> None:
    marker = "TODO" + "(EVO-"
    target_name = f"target{suffix}"

    exit_code = main(["--root", str(tmp_path), "add", target_name, "Add a suffix-delimited evolution."])

    assert exit_code == 0
    assert (tmp_path / target_name).read_text(encoding="utf-8") == (
        f"{prefix} {marker}010): Add a suffix-delimited evolution. {comment_suffix}\n"
    )
    capsys.readouterr()

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        target_name,
        "  next EVO-010 line 1 Add a suffix-delimited evolution.",
    ]


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


def test_probe_add_preserves_existing_crlf_newline_style(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    target = tmp_path / "tool.py"
    target.write_bytes(f"# {marker}010): Existing step.\r\n".encode("utf-8"))

    exit_code = main(["--root", str(tmp_path), "add", "tool.py", "Add a CRLF-preserved step."])

    assert exit_code == 0
    assert "- location: tool.py:3" in capsys.readouterr().out
    assert target.read_bytes() == (
        f"# {marker}010): Existing step.\r\n"
        "\r\n"
        f"# {marker}020): Add a CRLF-preserved step.\r\n"
    ).encode("utf-8")


def test_probe_add_rewrites_existing_file_through_single_atomic_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    marker = "TODO" + "(EVO-"
    target = tmp_path / "tool.py"
    target.write_bytes(f"# {marker}010): Existing step.\n".encode("utf-8"))
    original_replace = os.replace
    replace_calls: list[tuple[Path, Path]] = []

    def tracking_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        replace_calls.append((Path(source), Path(destination)))
        original_replace(source, destination)

    original_write_text = Path.write_text

    def guarded_write_text(path: Path, *args: Any, **kwargs: Any) -> int:
        if path == target:
            raise AssertionError("existing add target must be replaced atomically")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(probedev.evolutions.os, "replace", tracking_replace)
    monkeypatch.setattr(Path, "write_text", guarded_write_text)

    exit_code = main(["--root", str(tmp_path), "add", "tool.py", "Add an atomically replaced step."])

    assert exit_code == 0
    assert "- location: tool.py:3" in capsys.readouterr().out
    assert len(replace_calls) == 1
    temp_path, replaced_path = replace_calls[0]
    assert replaced_path == target
    assert temp_path.parent == target.parent
    assert target.read_bytes() == (
        f"# {marker}010): Existing step.\n"
        "\n"
        f"# {marker}020): Add an atomically replaced step.\n"
    ).encode("utf-8")


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


def test_probe_add_creates_missing_scannable_source_file_when_plan_is_empty(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    target = tmp_path / "src" / "tool.py"
    assert not target.exists()

    exit_code = main(["--root", str(tmp_path), "add", "src/tool.py", "Add the first evolution."])

    assert exit_code == 0
    assert "- marker: EVO-010" in capsys.readouterr().out
    assert target.read_text(encoding="utf-8") == f"# {marker}010): Add the first evolution.\n"


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

    def fake_run(argv: list[str], **_kwargs: Any) -> probedev.show.subprocess.CompletedProcess[list[str]]:
        editor_calls.append(argv)
        assert f"- editor: code --wait --goto {project_root / 'tool.py'}:1" in out.getvalue()
        assert out.flushed
        return probedev.show.subprocess.CompletedProcess(argv, 0)

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

    output = out.getvalue()
    assert exit_code == 1
    assert "Opening evolution" in output
    expected_error = (
        "Editor launch failed; attempted command: code --goto "
        f"{project_root / 'tool.py'}:1: code"
    )
    assert expected_error in output
    assert "Opened evolution" not in output
    assert out.flushed


def test_probe_show_nonzero_editor_exit_fails_with_attempted_command(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = TrackingOutput()

    def fake_run(argv: list[str], **_kwargs: Any) -> probedev.show.subprocess.CompletedProcess[list[str]]:
        return probedev.show.subprocess.CompletedProcess(argv, 23)

    monkeypatch.setenv("CODE_EDITOR", "code")
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(probedev.show.subprocess, "run", fake_run)

    exit_code = run_show(argparse.Namespace(marker="EVO-010"), Workspace(project_root), out)

    output = out.getvalue()
    assert exit_code == 1
    assert "Opening evolution" in output
    expected_error = (
        "Editor exited with status 23; attempted command: code --goto "
        f"{project_root / 'tool.py'}:1"
    )
    assert expected_error in output
    assert "Opened evolution" not in output
    assert out.flushed


@pytest.mark.parametrize(
    ("platform", "available_editor", "resolved_editor", "expected_lookup", "expected_argv"),
    [
        (
            "linux",
            "nvim",
            "/usr/bin/nvim",
            ["code", "code-insiders", "codium", "nvim"],
            ["/usr/bin/nvim", "+7", "tool.py"],
        ),
        (
            "darwin",
            "codium",
            "/usr/local/bin/codium",
            ["code", "code-insiders", "codium"],
            ["/usr/local/bin/codium", "--goto", "tool.py:7"],
        ),
        (
            "win32",
            "nvim.exe",
            r"C:\Program Files\Neovim\bin\nvim.exe",
            ["code.cmd", "code.exe", "code", "nvim.exe"],
            [r"C:\Program Files\Neovim\bin\nvim.exe", "+7", "tool.py"],
        ),
    ],
)
def test_editor_resolver_discovers_platform_default_editors_with_line_positioning(
    platform: str,
    available_editor: str,
    resolved_editor: str,
    expected_lookup: list[str],
    expected_argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    looked_up: list[str] = []

    def fake_which(editor: str) -> str | None:
        looked_up.append(editor)
        return resolved_editor if editor == available_editor else None

    monkeypatch.setattr(probedev.show.sys, "platform", platform)
    monkeypatch.setattr(probedev.show.shutil, "which", fake_which)

    command = probedev.show.EditorResolver({}).for_location(Path("tool.py"), 7)

    assert command.argv == expected_argv
    assert looked_up == expected_lookup


@pytest.mark.parametrize("available_editor", ["nvim.exe", "vim.exe", "vi.exe"])
def test_editor_resolver_positions_windows_vim_family_default_executables(
    available_editor: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved_editor = rf"C:\Tools\{available_editor}"

    def fake_which(editor: str) -> str | None:
        return resolved_editor if editor == available_editor else None

    monkeypatch.setattr(probedev.show.sys, "platform", "win32")
    monkeypatch.setattr(probedev.show.shutil, "which", fake_which)

    command = probedev.show.EditorResolver({}).for_location(Path("tool.py"), 7)

    assert command.argv == [resolved_editor, "+7", "tool.py"]


def test_probe_show_without_any_editor_reports_setup_hint(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = TrackingOutput()

    monkeypatch.delenv("CODE_EDITOR", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(probedev.show.shutil, "which", lambda _editor: None)

    exit_code = run_show(argparse.Namespace(marker="EVO-010"), Workspace(project_root), out)

    output = out.getvalue()
    assert exit_code == 1
    assert "No editor configured and no default editor found" in output
    assert "Set CODE_EDITOR or EDITOR to your editor command" in output
    assert "Opening evolution" not in output


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
        "Unchanged valid evolutions",
        "- marker: EVO-010",
        "  description: Keep this id.",
        "  location: tool.py:1",
    ]
    assert source.read_text(encoding="utf-8") == (
        f"# {marker}-010): Keep this id.  # {marker}-020): Add first missing id.  "
        f"# {marker}-030): Add second missing id.\n"
    )


def test_probe_identify_reports_rewritten_conflicts_separately(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(
        f"# {marker}010): Keep the first duplicate.\n"
        f"# {marker}010): Rewrite the conflicting duplicate.\n",
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "identify"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Rewritten conflicting evolutions",
        "- marker: EVO-020",
        "  replaced: EVO-010",
        "  description: Rewrite the conflicting duplicate.",
        "  location: tool.py:2",
        "Unchanged valid evolutions",
        "- marker: EVO-010",
        "  description: Keep the first duplicate.",
        "  location: tool.py:1",
    ]
    assert source.read_text(encoding="utf-8") == (
        f"# {marker}010): Keep the first duplicate.\n"
        f"# {marker}020): Rewrite the conflicting duplicate.\n"
    )


def test_probe_identify_reports_unchanged_valid_markers(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    source = tmp_path / "tool.py"
    source.write_text(f"# {marker}010): Keep this valid marker.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "identify"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "No evolution markers needed identifiers.",
        "Unchanged valid evolutions",
        "- marker: EVO-010",
        "  description: Keep this valid marker.",
        "  location: tool.py:1",
    ]
    assert source.read_text(encoding="utf-8") == f"# {marker}010): Keep this valid marker.\n"


def test_probe_identify_preserves_rewritten_file_newlines_and_permissions(tmp_path: Path, capsys) -> None:
    source = tmp_path / "tool.py"
    source.write_bytes(b"# TODO(EVO): Add first missing id.\r\n# TODO(EVO): Add second missing id.")
    source.chmod(0o754)

    exit_code = main(["--root", str(tmp_path), "identify"])

    assert exit_code == 0
    assert "- marker: EVO-010" in capsys.readouterr().out
    assert source.read_bytes() == (
        b"# TODO" b"(EVO-010): Add first missing id.\r\n# TODO" b"(EVO-020): Add second missing id."
    )
    assert source.stat().st_mode & 0o777 == 0o754


def test_probe_identify_rewrites_symlink_target_without_replacing_symlink(tmp_path: Path, capsys) -> None:
    target = tmp_path / "target"
    source = tmp_path / "tool.py"
    target.write_bytes(b"# TODO(EVO): Rewrite through the symlink.\r\n")
    try:
        source.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    exit_code = main(["--root", str(tmp_path), "identify"])

    assert exit_code == 0
    assert "  location: tool.py:1" in capsys.readouterr().out
    assert source.is_symlink()
    assert target.read_bytes() == b"# TODO" b"(EVO-010): Rewrite through the symlink.\r\n"


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
    (tmp_path / "README.MD").write_text(f"# {marker}010): Markdown is not source.\n", encoding="utf-8")
    (tmp_path / "data.json").write_text(f"# {marker}020): JSON is not source.\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(f"# {marker}030): TOML is not source.\n", encoding="utf-8")
    (tmp_path / "app.config").write_text(f"# {marker}040): Config is not source.\n", encoding="utf-8")
    (tmp_path / "spec.feature").write_text(f"# {marker}050): Feature is not source.\n", encoding="utf-8")
    (tmp_path / "notes.unknownext").write_text(f"# {marker}060): Unknown extension.\n", encoding="utf-8")
    (tmp_path / "tool.py").write_text(f"# {marker}070): A real source marker.\n", encoding="utf-8")

    plan = ProbePlanParser().scan(tmp_path)

    scanned = {evolution.path.name for evolution in plan.evolutions}
    assert scanned == {"tool.py"}


def test_probe_plan_includes_common_source_filename_casing_and_variants(tmp_path: Path) -> None:
    marker = "TODO" + "(EVO-"
    (tmp_path / "tool.PY").write_text(f"# {marker}010): Uppercase suffix.\n", encoding="utf-8")
    (tmp_path / "makefile").write_text(f"# {marker}020): Lowercase makefile.\n", encoding="utf-8")
    (tmp_path / "Dockerfile.prod").write_text(f"# {marker}030): Dockerfile variant.\n", encoding="utf-8")
    (tmp_path / "Makefile.inc").write_text(f"# {marker}040): Makefile variant.\n", encoding="utf-8")

    plan = ProbePlanParser().scan(tmp_path)

    scanned = {evolution.path.name for evolution in plan.evolutions}
    assert scanned == {"tool.PY", "makefile", "Dockerfile.prod", "Makefile.inc"}


def test_probe_plan_strips_uppercase_ocaml_block_comment_suffix(tmp_path: Path) -> None:
    marker = "TODO" + "(EVO-"
    (tmp_path / "target.ML").write_text(f"(* {marker}010): Uppercase OCaml marker. *)\n", encoding="utf-8")

    plan = ProbePlanParser().scan(tmp_path)

    assert [evolution.title for evolution in plan.evolutions] == ["Uppercase OCaml marker."]


def test_probe_plan_collects_docstring_continuation_for_uppercase_python_suffix(tmp_path: Path) -> None:
    marker = "TODO" + "(EVO-"
    (tmp_path / "tool.PY").write_text(
        f'"""\n{marker}010): Uppercase Python docstring.\nKeep the continuation.\n"""\n',
        encoding="utf-8",
    )

    plan = ProbePlanParser().scan(tmp_path)

    assert [evolution.description_lines for evolution in plan.evolutions] == [
        ("Uppercase Python docstring.", "Keep the continuation.")
    ]


def test_probe_plan_excludes_prefixed_doc_config_variants(tmp_path: Path) -> None:
    marker = "TODO" + "(EVO-"
    (tmp_path / "Dockerfile.prod").write_text(f"# {marker}010): Real Docker variant.\n", encoding="utf-8")
    (tmp_path / "Makefile.inc").write_text(f"# {marker}020): Real Make variant.\n", encoding="utf-8")
    (tmp_path / "Dockerfile.md").write_text(f"# {marker}030): Docker docs.\n", encoding="utf-8")
    (tmp_path / "Dockerfile.prod.md").write_text(f"# {marker}040): Docker variant docs.\n", encoding="utf-8")
    (tmp_path / "Makefile.toml").write_text(f"# {marker}050): Make config.\n", encoding="utf-8")
    (tmp_path / "Makefile.inc.json").write_text(f"# {marker}060): Make variant config.\n", encoding="utf-8")

    plan = ProbePlanParser().scan(tmp_path)

    scanned = {evolution.path.name for evolution in plan.evolutions}
    assert scanned == {"Dockerfile.prod", "Makefile.inc"}


def test_probe_list_excludes_prefixed_doc_config_variants(tmp_path: Path, capsys) -> None:
    marker = "TODO" + "(EVO-"
    (tmp_path / "Dockerfile.prod").write_text(f"# {marker}010): Real Docker variant.\n", encoding="utf-8")
    (tmp_path / "Dockerfile.prod.md").write_text(f"# {marker}020): Docker variant docs.\n", encoding="utf-8")
    (tmp_path / "Makefile.inc.json").write_text(f"# {marker}030): Make variant config.\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "list"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Pending evolutions",
        "Dockerfile.prod",
        "  next EVO-010 line 1 Real Docker variant.",
    ]


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
