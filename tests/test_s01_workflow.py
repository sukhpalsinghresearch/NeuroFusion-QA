"""Integration checks for the synthetic notebook evidence path."""

import importlib.util
from pathlib import Path


helper_path = Path(__file__).resolve().parents[1] / "scripts" / "s01_core_workflow.py"
spec = importlib.util.spec_from_file_location("s01_core_workflow", helper_path)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def test_qc_boundary_matrix_and_independent_gates() -> None:
    report = workflow.qc_contracts()
    assert len(report["threshold_cases"]) == 20
    assert len({row["criterion"] for row in report["threshold_cases"]}) == 7
    assert any(row["integrity_pass"] and not row["scientific_qc_pass"]
               for row in report["independent_gates"])


def test_training_only_quality_and_fusion_diagnostics() -> None:
    quality = workflow.quality_contracts()
    assert quality["held_out_transform_preserves_fit"]
    assert quality["availability_scores"] == [0.5, 0.0]
    fusion = workflow.fusion_contracts()
    assert fusion["generated_valid_cases"] == 512
    assert len(fusion["failures"]) == 9


def test_matched_nested_training_and_prediction_coverage() -> None:
    report = workflow.matched_model_contracts(repeats=1)
    assert len(report["folds"]) == 4
    assert report["each_record_held_out_once_per_repeat"]
    for fold in report["folds"]:
        assert fold["training_records"] + fold["held_out_records"] == report["records"]
        assert fold["train_test_disjoint"] and fold["quality_fit_on_training_only"]
        for modality in ("eeg", "fmri"):
            assert fold["tuning"][modality]["threshold_input_records"] == fold["training_records"]
    for prediction in report["predictions"].values():
        assert prediction["repeat_shape"] == [1, 80]
        assert 0 <= prediction["minimum"] <= prediction["maximum"] <= 1
