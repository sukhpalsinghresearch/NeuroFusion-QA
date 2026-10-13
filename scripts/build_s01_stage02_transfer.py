"""Build a narrow, hash-checked stage-02 update; preserve the original ZIP."""

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/neurofusion_qa/provenance.py", "src/neurofusion_qa/__init__.py",
    "scripts/s01_provenance_tutorial.py", "tests/test_provenance.py", "tests/test_s01_tutorial.py",
    "notebooks/02_S01_Provenance_End_to_End_Tutorial.ipynb", "notebooks/PROVENANCE_TUTORIAL.md",
    "notebooks/README.md", "notebooks/NOTEBOOK_SPECIFICATION.md", "README.md",
]


def main():
    directory = ROOT / "outputs/s01_dgx_transfer"
    with zipfile.ZipFile(directory / "S01_DGX_Source.zip") as original:
        original_manifest = json.loads(original.read("TRANSFER_MANIFEST.json"))
    baseline = {name: original_manifest["files"][name]["sha256"] for name in
                ("src/neurofusion_qa/provenance.py", "src/neurofusion_qa/__init__.py", "README.md")}
    manifest = {"files": {}, "baseline": baseline}
    archive_path = directory / "S01_DGX_Stage02.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            content = (ROOT / name).read_bytes()
            manifest["files"][name] = hashlib.sha256(content).hexdigest()
            archive.writestr(name, content)
        archive.writestr("STAGE02_MANIFEST.json", json.dumps(manifest, indent=2))
    print(json.dumps({"archive": archive_path.relative_to(ROOT).as_posix(),
                      "files": len(FILES), "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
