from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


# Shared marker-candidate regex. A candidate is any line that structurally
# looks like ``TODO(EVO...):`` regardless of the surrounding comment syntax.
# Captures the token (e.g. ``EVO-010``, ``EVO-10``, ``EVO``) and the trailing
# description text so that both ``probedev list`` and ``probedev identify``
# agree on the shape of every candidate. Public so that ``identify``'s
# rewrite step can reuse the same pattern when substituting new ids.
CANDIDATE_RE = re.compile(
    r"TODO\((?P<token>EVO(?:-[^)]+)?)\):\s*"
    r"(?P<description>.*?)"
    r"(?=\s*(?:(?:#|//|/\*|\*)\s*|\*\)\s*\(\*\s*)?"
    r"TODO\(EVO(?:-[^)]+)?\):|$)"
)
IGNORE_PRAGMA_RE = re.compile(r"\bprobedev:\s*(?P<pragma>ignore-(?:file|line|next-line|start|end))\b")
IGNORE_PRAGMA_COMMENT_PREFIXES = ("#", "//", "/*", "*", "<!--")

SKIPPED_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "dist", "build"}
# Allowlist of programming-language source extensions. Language-agnostic
# marker parsing does not mean scanning every text file: non-source files
# such as ``.feature`` specs, ``.json``/``.toml`` configs, and lockfiles
# must not appear in the plan even when they happen to contain a
# ``TODO(EVO-...)``-shaped line.
SOURCE_SUFFIXES = {
    ".py", ".pyi",
    ".go",
    ".rs",
    ".c", ".h", ".cc", ".cpp", ".hh", ".hpp",
    ".java", ".kt", ".kts",
    ".rb",
    ".php",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".sh", ".bash", ".zsh",
    ".swift",
    ".cs",
    ".scala",
    ".clj", ".cljs",
    ".hs",
    ".ex", ".exs", ".erl",
    ".lua",
    ".pl", ".pm",
    ".nim",
    ".cr",
    ".ml", ".mli",
    ".fs", ".fsx",
    ".dart",
}
# Recognized extensionless source filenames common in build/infra trees.
SOURCE_FILENAMES = {"Makefile", "Dockerfile", "Rakefile", "Gemfile", "Jenkinsfile", "Evolutions.txt"}
# Dotted variants that remain source-like in build/infra trees.
SOURCE_FILENAME_PREFIXES = {"Makefile", "Dockerfile"}
# Docs/configs stay excluded even when their base name looks like source.
NON_SOURCE_SUFFIXES = {
    ".cfg", ".conf", ".config",
    ".feature",
    ".ini",
    ".json",
    ".lock",
    ".md", ".markdown",
    ".rst",
    ".toml",
    ".txt",
    ".xml",
    ".yaml", ".yml",
}
_SOURCE_SUFFIXES = {suffix.casefold() for suffix in SOURCE_SUFFIXES}
_NON_SOURCE_SUFFIXES = {suffix.casefold() for suffix in NON_SOURCE_SUFFIXES}
_SOURCE_FILENAMES = {name.casefold() for name in SOURCE_FILENAMES}
_SOURCE_FILENAME_PREFIXES = {name.casefold() for name in SOURCE_FILENAME_PREFIXES}


def is_source_file(path: Path) -> bool:
    """Return True when a path matches the scanner's source-file allowlist.

    Shared between the scanner and the ``add`` command so the set of files
    the scanner reads stays identical to the set of files the ``add`` command
    is allowed to write markers into. Diverging the two would let ``add``
    write a marker into a file the scanner will never see, breaking id
    allocation.

    :param Path path: Filesystem path to classify.
    """
    name = path.name.casefold()
    if name in _SOURCE_FILENAMES:
        return True

    suffix = path.suffix.casefold()
    if suffix in _SOURCE_SUFFIXES:
        return True
    if suffix in _NON_SOURCE_SUFFIXES:
        return False

    return any(name.startswith(f"{prefix}.") for prefix in _SOURCE_FILENAME_PREFIXES)


@dataclass(frozen=True)
class MarkerCandidate:
    """One ``TODO(EVO-...)``-shaped line discovered in a source file."""

    path: Path
    line: int
    text: str
    token: str
    description: str


@dataclass(frozen=True)
class FileCandidates:
    """All marker candidates found in one file, alongside its raw lines.

    The full ``lines`` tuple is kept so that consumers that need surrounding
    context (for example continuation-line collection) can work from the same
    in-memory snapshot the scanner already parsed.
    """

    path: Path
    lines: tuple[str, ...]
    candidates: tuple[MarkerCandidate, ...]


@dataclass(frozen=True)
class CandidateScan:
    """Result of one workspace candidate scan."""

    files: tuple[FileCandidates, ...]
    unreadable_paths: tuple[Path, ...]


def scan_candidates(root: Path) -> CandidateScan:
    """Walk a workspace and collect every marker-candidate line.

    This is the single entry point consumed by both ``probedev list`` and
    ``probedev identify``; they agree on candidate shape because they read
    from the same scanner. Directories or files that fail to open are
    reported through :attr:`CandidateScan.unreadable_paths`; undecodable
    files are silently skipped because they cannot contain text markers.

    :param Path root: Workspace root to scan.
    """
    files: list[FileCandidates] = []
    unreadable_paths: list[Path] = []
    for path in _iter_scannable_files(root, unreadable_paths):
        try:
            lines = tuple(path.read_text(encoding="utf-8").splitlines())
        except OSError:
            unreadable_paths.append(path)
            continue
        except UnicodeDecodeError:
            continue
        candidates = tuple(_candidates_in_lines(path, lines))
        files.append(FileCandidates(path, lines, candidates))
    return CandidateScan(tuple(files), tuple(sorted(unreadable_paths)))


def has_ignore_pragma(line: str) -> bool:
    """Return True when a comment line contains any ``probedev: ignore-*`` pragma."""
    return bool(_ignore_pragmas(line))


def _candidates_in_lines(path: Path, lines: tuple[str, ...]):
    if any("ignore-file" in _ignore_pragmas(line) for line in lines):
        return

    ignore_block = False
    ignore_next_line = False
    for line_number, line in enumerate(lines, start=1):
        pragmas = _ignore_pragmas(line)
        ignore_current = ignore_next_line or ignore_block or bool(
            pragmas & {"ignore-line", "ignore-next-line", "ignore-start", "ignore-end"}
        )
        ignore_next_line = False

        if "ignore-end" in pragmas:
            ignore_block = False
        if "ignore-start" in pragmas:
            ignore_block = True
        if "ignore-next-line" in pragmas:
            ignore_next_line = True
        if ignore_current:
            continue

        # Quick pre-check: only run regex if line might contain a marker
        if "TODO(EVO" in line:
            for match in CANDIDATE_RE.finditer(line):
                yield MarkerCandidate(
                    path=path,
                    line=line_number,
                    text=line,
                    token=match.group("token"),
                    description=_candidate_description(path, match.group("description")),
                )


def _candidate_description(path: Path, description: str) -> str:
    description = description.strip()
    if path.suffix.casefold() in {".ml", ".mli"} and description.endswith("*)"):
        return description[:-2].rstrip()
    return description


def _ignore_pragmas(line: str) -> set[str]:
    stripped = line.lstrip()
    if not stripped.startswith(IGNORE_PRAGMA_COMMENT_PREFIXES):
        return set()
    return {match.group("pragma") for match in IGNORE_PRAGMA_RE.finditer(line)}


def _iter_scannable_files(root: Path, unreadable_paths: list[Path]):
    def record_unreadable(error: OSError) -> None:
        if error.filename:
            unreadable_paths.append(Path(error.filename))

    # Use os.scandir() for better performance
    try:
        with os.scandir(root) as it:
            for entry in it:
                try:
                    is_dir = entry.is_dir(follow_symlinks=True)
                except OSError:
                    is_dir = False
                
                if is_dir:
                    if entry.name in SKIPPED_DIRS:
                        continue
                    # Recursively scan subdirectory
                    yield from _iter_scannable_files(entry.path, unreadable_paths)
                else:
                    # Treat as file (including symlinks to files)
                    path = Path(entry.path)
                    try:
                        if not path.is_file():
                            continue
                        if not is_source_file(path):
                            continue
                        yield path
                    except OSError:
                        unreadable_paths.append(path)
    except OSError as error:
        record_unreadable(error)
