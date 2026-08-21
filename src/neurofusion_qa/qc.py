"""Frozen fMRI scientific-QC decision, kept separate from integrity checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FmriQcMeasurements:
    censored_fraction: float
    registration_dice: float
    centroid_distance_mm: float
    parcels_present: int
    parcels_with_10_voxels: int
    finite_connectome: bool
    minimum_filtered_regional_sd: float


@dataclass(frozen=True)
class FmriQcReport:
    passed: bool
    criteria: dict[str, bool]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_fmri_qc(measurements: FmriQcMeasurements) -> FmriQcReport:
    """Apply the seven prespecified conjunction criteria from manuscript Table 2."""
    criteria = {
        "censored_fraction": measurements.censored_fraction <= 0.20,
        "registration_dice": measurements.registration_dice >= 0.70,
        "centroid_distance_mm": measurements.centroid_distance_mm <= 8.0,
        "parcels_present": measurements.parcels_present >= 357,
        "parcels_with_10_voxels": measurements.parcels_with_10_voxels >= 358,
        "finite_connectome": bool(measurements.finite_connectome),
        "minimum_filtered_regional_sd": measurements.minimum_filtered_regional_sd > 0.0,
    }
    return FmriQcReport(passed=all(criteria.values()), criteria=criteria)

