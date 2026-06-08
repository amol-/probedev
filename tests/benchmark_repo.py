#!/usr/bin/env python3
"""Benchmark repository generator.

This module provides functions to generate a reproducible test repository
for benchmarking probedev performance.
"""
from __future__ import annotations

import random
import shutil
from pathlib import Path


# Configuration for the test repository structure
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


def create_test_repo(output_dir: Path, config: dict = REPO_CONFIG) -> Path:
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
