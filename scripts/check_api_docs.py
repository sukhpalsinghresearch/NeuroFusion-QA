"""Check public API coverage and execute the reference's pycon examples."""

from __future__ import annotations

import doctest
import json
import re
from pathlib import Path

import neurofusion_qa


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    document = root / "docs/API_REFERENCE.md"
    content = document.read_text(encoding="utf-8")
    missing = [name for name in neurofusion_qa.__all__
               if not re.search(r"^### `" + re.escape(name) + r"(?:`|\()", content, re.M)]
    if missing:
        raise SystemExit(f"Undocumented root exports: {missing}")
    examples = "\n\n".join(re.findall(r"```pycon\n(.*?)\n```", content, re.S))
    if not examples:
        raise SystemExit("API reference contains no executable examples")
    suite = doctest.DocTestParser().get_doctest(examples, {}, "API_REFERENCE", str(document), 0)
    runner = doctest.DocTestRunner()
    runner.run(suite)
    result = runner.summarize()
    report = {"root_exports_documented": len(neurofusion_qa.__all__),
              "examples_attempted": result.attempted, "examples_failed": result.failed,
              "scope": "documentation_examples_not_full_API_validation"}
    output = root / "outputs/api_documentation_check.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    if result.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
