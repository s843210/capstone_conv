"""Report writing helpers — uniform text report generation."""

from __future__ import annotations

from pathlib import Path

from .io import ensure_dir


def write_report(path: Path, lines: list[str]) -> Path:
    """Write *lines* to a UTF-8 text report file, creating parent dirs."""
    ensure_dir(path)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def print_and_report(
    path: Path,
    lines: list[str],
    *,
    also_print: bool = True,
) -> Path:
    """Write a report **and** optionally print key lines to stdout."""
    write_report(path, lines)
    if also_print:
        for line in lines[:15]:
            print(line)
        if len(lines) > 15:
            print(f"  ... ({len(lines)} lines total, see {path.name})")
    return path
