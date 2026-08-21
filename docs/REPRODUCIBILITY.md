# Reproducibility record

The public package separates reproducibility from participant disclosure.

## Preserved evidence

- frozen aggregate cohort and QC counts;
- complete model-level development metrics;
- paired gate-minus-equal bootstrap intervals;
- direct gate-validity estimates and intervals;
- reusable equations and unit tests;
- a direct manuscript-to-code map;
- an example frozen-protocol configuration.

## Deliberately excluded

- raw EEG or fMRI;
- participant identifiers;
- subject-level features or predictions;
- protected-cohort manifests;
- machine-specific DGX paths;
- tokens, credentials, or private storage locations.

Reproduction from raw data requires the source dataset, the documented scientific preprocessing stack, and the exact frozen protocol used by the study. The compact public implementation reproduces the evaluation logic and aggregate figures; it does not claim bitwise reproduction of AFNI or MNE outputs on another platform.

Run `python scripts/validate_release.py` before every public tag. A passing validation establishes only the repository boundary; it is not evidence that an imaging record passed scientific QC.
