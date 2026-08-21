"""Fail closed when the public package crosses its documented release boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".cff", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
FORBIDDEN_SUFFIXES = {".eeg", ".fif", ".nii", ".npy", ".npz", ".vhdr", ".vmrk"}
FORBIDDEN_PATTERNS = {
    "private key": re.compile(r"BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY"),
    "DGX path": re.compile(r"(?<![A-Za-z0-9_])/workspace/"),
    "Windows machine path": re.compile(r"[A-Za-z]:\\Users\\"),
    "participant identifier": re.compile(r"\bsub[-_]?\d{2,}\b", re.IGNORECASE),
}


def main() -> None:
    problems: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {".git", ".pytest_cache", "__pycache__", "outputs"} for part in path.parts):
            continue
        relative = path.relative_to(ROOT)
        if relative.as_posix() == "scripts/validate_release.py":
            continue
        suffixes = {suffix.lower() for suffix in path.suffixes}
        if suffixes & FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden data type: {relative}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
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
