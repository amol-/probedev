"""Benchmark tests for probedev list command performance.

This module creates a reproducible test repository structure and benchmarks
the list command performance using pytest-benchmark.

To run benchmarks:
    pytest tests/benchmark_list.py --benchmark-only

To compare against a previous run:
    pytest tests/benchmark_list.py --benchmark-only --benchmark-compare
"""
from __future__ import annotations

import argparse
import random
import shutil
import tempfile
from io import StringIO
from pathlib import Path

import pytest


# Configuration for the test repository structure
# This defines a reproducible structure without hardcoding all 100,000 files
# Target: ~100,000 files total with:
#   - 10 nesting levels
#   - Mix of source and non-source files
#   - ~5% of source files contain TODO(EVO-...) markers
REPO_CONFIG = {
    "levels": 2,  # Number of nesting levels (root -> level1 -> level2)
    "fanout": 31,  # How many subdirectories per level
    "files_per_dir": 100,  # Files per directory
    # Distribution of file types (percentages)
    "file_distribution": {
        # Source files that will be scanned
        ".py": 40,    # 40% of files are Python
        ".js": 10,    # 10% are JavaScript
        ".go": 5,     # 5% are Go
        ".rs": 5,     # 5% are Rust
        # Non-source files that will be skipped
        ".md": 10,    # 10% are Markdown
        ".json": 10,  # 10% are JSON
        ".txt": 10,   # 10% are text
        ".log": 5,    # 5% are logs
        ".mp4": 5,    # 5% are videos (should be skipped)
    },
    # Percentage of source files that contain TODO(EVO-...) markers
    "marker_percentage": 5,  # 5% of source files have markers
    # Number of markers per file (for files that have them)
    "markers_per_file": 3,
}


def generate_file_name(index: int, extension: str) -> str:
    """Generate a deterministic file name based on index and extension."""
    return f"file_{index:06d}{extension}"


def generate_directory_name(level: int, index: int) -> str:
    """Generate a deterministic directory name."""
    return f"l{level:02d}d{index:03d}"


def generate_file_content(filepath: Path, file_index: int, extension: str, config: dict) -> str:
    """Generate file content, potentially with TODO markers."""
    # Use deterministic randomness based on file index
    rng = random.Random(file_index)
    
    # Determine if this is a source file
    SOURCE_EXTENSIONS = {".py", ".js", ".go", ".rs", ".java", ".ts", ".cc", ".cpp", ".h", ".hpp"}
    is_source = extension in SOURCE_EXTENSIONS
    
    lines = []
    
    if is_source:
        # Add some code-like content
        lines.append(f"# File: {filepath.name}")
        lines.append(f"# Index: {file_index}")
        lines.append("")
        
        # Add some realistic code
        if extension == ".py":
            lines.extend([
                "def example_function():",
                '    """Example docstring."""',
                "    pass",
                "",
            ])
        elif extension == ".js":
            lines.extend([
                "function example() {",
                "    // Example function",
                "}",
                "",
            ])
        elif extension == ".go":
            lines.extend([
                "package main",
                "",
                "func Example() {",
                "}",
                "",
            ])
        elif extension == ".rs":
            lines.extend([
                "fn example() {",
                "}",
                "",
            ])
        
        # Potentially add TODO markers
        if is_source and rng.random() < config["marker_percentage"] / 100:
            for marker_idx in range(config["markers_per_file"]):
                lines.append(f"# TODO(EVO-{file_index:03d}-{marker_idx:02d}): Example marker")
                lines.append(f"#   Description for marker {marker_idx}")
                lines.append("")
    else:
        # Non-source files
        if extension == ".md":
            lines = [
                f"# {filepath.name}",
                "",
                "This is a markdown file.",
                "",
            ]
        elif extension == ".json":
            lines = ['{', '  "name": "' + filepath.name + '",', '  "index": ' + str(file_index), '}']
        elif extension == ".txt":
            lines = [f"Text file: {filepath.name}", f"Index: {file_index}"]
        elif extension == ".log":
            lines = [f"LOG: {filepath.name}", f"Index: {file_index}"]
        elif extension == ".mp4":
            # Binary-like content (but we write as text for the test)
            lines = [f"FAKE_VIDEO_{file_index}"]
    
    return "\n".join(lines)


def create_test_repo(output_dir: Path, config: dict) -> Path:
    """Create a test repository with the specified configuration.
    
    Returns the root path of the created repository.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    repo_root = output_dir / "test_repo"
    
    if repo_root.exists():
        # Clean up existing repo
        shutil.rmtree(repo_root)
    
    repo_root.mkdir()
    
    # Track file index
    file_index = 0
    
    def create_level_files(parent: Path, level: int) -> None:
        nonlocal file_index
        
        # Create files in this directory
        for file_num in range(config["files_per_dir"]):
            # Determine file extension based on distribution
            # Use deterministic selection
            ext_idx = file_index % len(config["file_distribution"])
            ext = list(config["file_distribution"].keys())[ext_idx]
            
            filename = generate_file_name(file_index, ext)
            filepath = parent / filename
            
            # Create the file
            content = generate_file_content(filepath, file_index, ext, config)
            filepath.write_text(content, encoding="utf-8")
            
            file_index += 1
        
        # Create subdirectories and recurse if we haven't reached max depth
        if level < config["levels"]:
            for dir_idx in range(config["fanout"]):
                dir_name = generate_directory_name(level, dir_idx)
                dir_path = parent / dir_name
                dir_path.mkdir(exist_ok=True)
                create_level_files(dir_path, level + 1)
    
    # Start from root
    create_level_files(repo_root, 0)
    
    return repo_root


@pytest.fixture(scope="session")
def benchmark_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a test repository for benchmarking.
    
    This fixture creates a session-scoped test repository with ~100,000 files
    across multiple nesting levels. The structure is reproducible.
    
    File distribution:
    - 40% .py files (source)
    - 10% .js files (source)
    - 5% .go files (source)
    - 5% .rs files (source)
    - 40% non-source files (.md, .json, .txt, .log, .mp4)
    - 5% of source files contain TODO(EVO-...) markers
    """
    tmp_path = tmp_path_factory.mktemp("benchmark")
    repo_root = create_test_repo(tmp_path, REPO_CONFIG)
    
    # Verify the structure
    total_files = sum(1 for _ in repo_root.rglob("*") if _.is_file())
    print(f"\nCreated benchmark repo with {total_files:,} files")
    
    # Count source vs non-source
    from collections import Counter
    ext_counts = Counter()
    source_files = 0
    files_with_markers = 0
    
    for f in repo_root.rglob("*"):
        if f.is_file():
            ext_counts[f.suffix] += 1
            if f.suffix in {".py", ".js", ".go", ".rs"}:
                source_files += 1
                content = f.read_text()
                if "TODO(EVO-" in content:
                    files_with_markers += 1
    
    print(f"Source files: {source_files:,}")
    print(f"Files with TODO markers: {files_with_markers:,}")
    
    return repo_root


class TestListBenchmark:
    """Benchmark tests for the list command."""

    @pytest.mark.benchmark
    def test_list_performance(self, benchmark: pytest.BenchmarkFixture, benchmark_repo: Path) -> None:
        """Benchmark the list command on a large repository.
        
        This benchmark measures the total time to scan and list all TODO(EVO-...)
        markers in a repository with ~100,000 files.
        """
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        
        from probedev.cli import Workspace, run_list
        
        # Create mock args
        args = argparse.Namespace(
            short=False,
            color=False,
            root=str(benchmark_repo),
        )
        workspace = Workspace(benchmark_repo)
        out = StringIO()
        
        # Run the list command
        result = benchmark(
            run_list,
            args=args,
            workspace=workspace,
            out=out,
        )
        
        # Verify we got some results
        assert result == 0 or result == 1  # 0 = success, 1 = no evolutions found


if __name__ == "__main__":
    # Allow running this module directly for testing
    import sys
    from pathlib import Path
    
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        tmp_dir = Path(tempfile.mkdtemp())
        print(f"Generating test repo in {tmp_dir}")
        repo = create_test_repo(tmp_dir, REPO_CONFIG)
        print(f"Generated repo at {repo}")
        
        # Count files
        total = sum(1 for _ in repo.rglob("*") if _.is_file())
        print(f"Total files: {total}")
        
        # Count by extension
        from collections import Counter
        ext_counts = Counter()
        for f in repo.rglob("*"):
            if f.is_file():
                ext_counts[f.suffix] += 1
        
        print("\nFiles by extension:")
        for ext, count in sorted(ext_counts.items()):
            print(f"  {ext}: {count}")
