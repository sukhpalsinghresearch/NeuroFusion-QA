"""Reusable components for quality-aware multimodal fusion."""

from .gating import (
    binary_utility,
    continuous_utility,
    equal_fusion,
    label_free_quality_weight,
    soft_fusion,
)
from .integrity import validate_compact_features
from .modeling import average_repeated_predictions, make_classifier, select_balanced_threshold
from .qc import FmriQcMeasurements, evaluate_fmri_qc
from .quality import RobustQualityScaler, reliability_score
from .provenance import (
    ObservationIdentity, canonical_json, checked_join,
    create_execution_manifest, verify_execution_manifest,
)

__all__ = [
    "ObservationIdentity", "canonical_json", "checked_join",
    "create_execution_manifest", "verify_execution_manifest",
    "binary_utility",
    "continuous_utility",
    "equal_fusion",
    "label_free_quality_weight",
    "soft_fusion",
    "validate_compact_features",
    "average_repeated_predictions",
    "make_classifier",
    "select_balanced_threshold",
    "FmriQcMeasurements",
    "evaluate_fmri_qc",
    "RobustQualityScaler",
    "reliability_score",
]
