"""Check that notebook content and escaped artifact strings remain audited."""

import importlib.util
import json
from pathlib import Path

import pytest


validator_path = Path(__file__).resolve().parents[1] / "scripts" / "validate_release.py"
spec = importlib.util.spec_from_file_location("validate_release", validator_path)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


@pytest.mark.parametrize("suffix,payload", [
    (".ipynb", {"cells": [{"source": ["sub", "-123"], "outputs": []}]}),
    (".ipynb", {"cells": [{"source": [], "outputs": [{"text": ["sub" + "-123"]}]}]}),
    (".json", {"location": "C:\\Users\\synthetic\\private"}),
])
def test_decoded_notebook_sources_and_outputs_are_scanned(tmp_path, monkeypatch, suffix, payload):
    results = tmp_path / "results"
    results.mkdir()
    (results / "frozen_summary.json").write_text(
        json.dumps({"scope": "development_only", "protected_access_count": 0}), encoding="utf-8")
    (tmp_path / ("fixture" + suffix)).write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="Release validation failed"):
        validator.main()
