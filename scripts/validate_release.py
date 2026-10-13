"""Fail closed when the public package crosses its documented release boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".cff", ".ipynb", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
FORBIDDEN_SUFFIXES = {".eeg", ".fif", ".nii", ".npy", ".npz", ".vhdr", ".vmrk"}
EXCLUDED_DIRECTORIES = {
    ".git",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "outputs",
}
FORBIDDEN_PATTERNS = {
    "private key": re.compile(r"BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY"),
    "DGX path": re.compile(r"(?<![A-Za-z0-9_])/workspace/"),
    "Windows machine path": re.compile(r"[A-Za-z]:\\Users\\"),
    "participant identifier": re.compile(r"\bsub[-_]?\d{2,}\b", re.IGNORECASE),
}


def json_strings(value: object):
    """Yield decoded strings so JSON escaping cannot hide restricted content."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        # Notebook source and outputs can split a sensitive string across lines.
        if all(isinstance(item, str) for item in value):
            yield "".join(value)
        else:
            for item in value:
                yield from json_strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from json_strings(item)


def main() -> None:
    problems: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(
            part in EXCLUDED_DIRECTORIES or part.endswith(".egg-info")
            for part in relative.parts
        ):
            continue
        if relative.as_posix() == "scripts/validate_release.py":
            continue
        suffixes = {suffix.lower() for suffix in path.suffixes}
        if suffixes & FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden data type: {relative}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            if path.suffix.lower() in {".ipynb", ".json"}:
                try:
                    text = "\n".join(json_strings(json.loads(text)))
                except (json.JSONDecodeError, ValueError):
                    problems.append(f"invalid JSON artifact: {relative}")
            for label, pattern in FORBIDDEN_PATTERNS.items():
                if pattern.search(text):
                    problems.append(f"{label}: {relative}")
    summary = json.loads((ROOT / "results" / "frozen_summary.json").read_text(encoding="utf-8"))
    if summary.get("scope") != "development_only" or summary.get("protected_access_count") != 0:
        problems.append("frozen summary violates the development-only boundary")
    if problems:
        raise SystemExit("Release validation failed:\n- " + "\n- ".join(problems))
    print("Release validation passed: aggregate-only, protected access count 0, no prohibited artifacts.")


if __name__ == "__main__":
    main()
