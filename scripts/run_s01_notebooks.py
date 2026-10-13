"""Execute the S01 notebooks in order and verify every saved code cell."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager

from neurofusion_qa.provenance import sha256_file


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", default="python3")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    kernel = KernelSpecManager().get_kernel_spec(args.kernel)
    paths = sorted((ROOT / "notebooks").glob("[0-4][0-9]_S01_*.ipynb"))
    if not paths:
        raise SystemExit("No numbered S01 notebooks found")
    report = {"kernel": args.kernel, "notebooks": []}
    for path in paths:
        print(f"Executing {path.name}", flush=True)
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        notebook.metadata.kernelspec = {
            "name": args.kernel, "display_name": kernel.display_name, "language": "python",
        }
        for cell in notebook.cells:
            if cell.cell_type == "code":
                cell.execution_count = None
                cell.outputs = []
            cell.metadata.pop("execution", None)
        NotebookClient(
            notebook, timeout=args.timeout, kernel_name=args.kernel,
            resources={"metadata": {"path": str(ROOT)}},
        ).execute()
        cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        assert all(cell.execution_count is not None for cell in cells)
        assert not any(output.output_type == "error" for cell in cells for output in cell.outputs)
        nbformat.write(notebook, path)
        report["notebooks"].append({
            "path": path.relative_to(ROOT).as_posix(), "code_cells": len(cells),
            "error_outputs": 0, "sha256": sha256_file(path),
        })
        print(f"Passed: {len(cells)} code cells, zero error outputs", flush=True)
    output = ROOT / "outputs" / "s01_notebook_execution.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
