import importlib.util
from pathlib import Path

from neurofusion_qa.provenance import canonical_json_sha256


PATH = Path(__file__).resolve().parents[1] / "scripts/s01_provenance_tutorial.py"
SPEC = importlib.util.spec_from_file_location("s01_provenance_tutorial", PATH)
tutorial = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tutorial)


def test_signal_to_summary_tutorial_and_replay():
    summary = tutorial.run_signal_tutorial()
    assert summary["eeg_shape"] == [24, 33]
    assert summary["fmri_shape"] == [24, 1440]
    assert summary["training_records"] == 16 and summary["held_out_records"] == 8
    assert summary["qc_rejected_modality_receives_zero_weight"]
    assert not summary["separate_integrity_failure"]["passed"]
    assert not summary["qc_failure_with_intact_features"]["passed"]
    assert summary["profiles_are_demonstration_only_not_benchmark"]
    assert canonical_json_sha256(summary) == canonical_json_sha256(tutorial.run_signal_tutorial())


def test_provenance_failure_demonstrations(tmp_path):
    failures = tutorial.provenance_failures(tmp_path)
    assert len(failures) == 11
    assert len({row["case"] for row in failures}) == 11
