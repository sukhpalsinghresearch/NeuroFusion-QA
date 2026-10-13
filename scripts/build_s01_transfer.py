"""Package the explicit public S01 file set for a DGX workspace transfer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    files = [ROOT / name for name in (
        "README.md", "pyproject.toml", "LICENSE", "CITATION.cff", "environment.yml",
        "scripts/validate_release.py", "scripts/s01_core_workflow.py",
        "scripts/s01_provenance_tutorial.py", "scripts/run_s01_notebooks.py",
        "scripts/S01_DGX_RUNBOOK.md", "notebooks/PROVENANCE_TUTORIAL.md",
        "scripts/reproduce_summary_figures.py",
        "results/frozen_summary.json", "config/protocol.example.yaml", "data/README.md",
        "notebooks/README.md", "notebooks/NOTEBOOK_SPECIFICATION.md",
        "notebooks/artifacts/README.md",
    )]
    for directory, pattern in (("src/neurofusion_qa", "*.py"), ("tests", "test_*.py"),
                               ("docs", "*.md"), ("notebooks", "*.ipynb")):
        files.extend(sorted((ROOT / directory).glob(pattern)))
    output = ROOT / "outputs" / "s01_dgx_transfer" / "S01_DGX_Source.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "1.0", "scope": "explicit_public_source_snapshot",
                "includes_environment": False, "includes_participant_level_data": False,
                "files": {}}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            content = path.read_bytes()
            relative = path.relative_to(ROOT).as_posix()
            if path.suffix == ".ipynb":
                notebook = json.loads(content)
                # Remote runs must produce their own outputs and environment records.
                for cell in notebook["cells"]:
                    cell["metadata"].pop("execution", None)
                    if cell["cell_type"] == "code":
                        cell["execution_count"] = None
                        cell["outputs"] = []
                content = (json.dumps(notebook, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
            manifest["files"][relative] = {"bytes": len(content),
                                           "sha256": hashlib.sha256(content).hexdigest()}
            archive.writestr(relative, content)
        archive.writestr("TRANSFER_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"archive": output.relative_to(ROOT).as_posix(),
                      "files": len(files), "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
