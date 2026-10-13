# API reference

This reference describes the submission working tree. The historical `v0.1.0` tag is not an identifier for this tree. Inputs are NumPy-compatible arrays unless stated otherwise. Feature extraction expects preprocessed signals; the package does not perform acquisition, artifact removal, registration or parcellation. Fit learned transformations on training data only.

## Fusion and utility

### `equal_fusion(p_eeg, p_fmri)`

Return the arithmetic mean as a float array. Both arrays must be nonempty, finite, in [0, 1], and have exactly the same shape. Invalid inputs raise `ValueError`; broadcasting is not supported.

### `soft_fusion(p_eeg, p_fmri, w_fmri)`

Return `(1 - w_fmri) * p_eeg + w_fmri * p_fmri`. All three arrays obey the probability contract above and must have the same shape. The weight is a contribution, not a calibrated probability of correctness.

### `label_free_quality_weight(eeg_quality, fmri_quality, epsilon=1e-12)`

Return fMRI mass divided by total mass. Matched arrays must be nonempty, finite and nonnegative. Each total must exceed finite, nonnegative `epsilon`. Very large masses are halved together before summation to avoid overflow. Invalid inputs raise `ValueError`. A zero mass excludes one modality; two zero masses reject the observation. Fusion still requires a valid probability placeholder for an unavailable modality.

### `continuous_utility(y_true, p_eeg, p_fmri)`

Return `abs(y_true - p_eeg) - abs(y_true - p_fmri)`. Positive values favor fMRI. Arrays must match and obey the probability contract. For binary interpretation, callers must supply labels in {0, 1}; the helper itself also accepts fractional targets in [0, 1]. Compute this diagnostic on held-out predictions, never as an input to the label-free gate.

### `binary_utility(y_true, p_eeg, p_fmri)`

Return integer indicators that continuous utility is positive. Ties return zero. Validation is delegated to `continuous_utility`.

```pycon
>>> import numpy as np
>>> from neurofusion_qa import equal_fusion, soft_fusion, label_free_quality_weight
>>> weight = label_free_quality_weight([1., 3.], [3., 1.])
>>> np.allclose(weight, [0.75, 0.25])
True
>>> np.allclose(soft_fusion([0.2, 0.8], [0.6, 0.4], weight), [0.5, 0.7])
True
>>> np.allclose(equal_fusion([0.2], [0.6]), [0.4])
True
```

## Quality transformation

### `RobustQualityScaler`

Frozen dataclass with `median`, `p10`, `p90`, `clip=5.0` and `epsilon=1e-12`. Use `RobustQualityScaler.fit(training_quality, clip=5.0)` to estimate column percentiles from a two-dimensional record-by-variable matrix with at least two rows and one column. NaNs represent missingness; infinities and wholly missing columns raise `ValueError`.

`transform(quality)` requires a two-dimensional matrix with the fitted column count. It replaces all nonfinite values, including infinities, with fitted medians, scales by `(p90 - p10 + epsilon)`, and clips to `[-clip, clip]`. The constructor does not comprehensively validate manually supplied fields or enforce positive `clip`; callers should use the fitted defaults. Output columns are dimensionless. The scaler does not manage train/test partitions.

### `reliability_score(scaled_quality, directions, availability=None)`

Return availability times `sigmoid(mean(scaled_quality * directions, axis=1))`. Quality must be finite and two-dimensional; `directions` contains one -1 or +1 per variable. Availability defaults to one and otherwise must be a binary vector of record length. Invalid inputs raise `ValueError`. Supply at least one quality variable. Despite the historical function name, the result is a quality mass, not validated predictive reliability.

```pycon
>>> from neurofusion_qa import RobustQualityScaler, reliability_score
>>> scaler = RobustQualityScaler.fit([[1., 2.], [3., 4.], [5., 6.]])
>>> np.allclose(scaler.transform([[np.nan, 4.]]), [[0., 0.]])
True
>>> np.allclose(reliability_score([[0., 0.]], [1, -1]), [0.5])
True
```

## Integrity and scientific QC

### `validate_compact_features(features, expected_shape)`

Return an `IntegrityReport` containing `passed`, `expected_shape`, `observed_shape`, `all_finite` and `positive_variance`; `to_dict()` serializes it. Passing requires exact shape, finite entries, more than one value and positive variance across the whole array. This does not check that every column varies, that an atlas is correct, or that scientific QC passes. Shape/finite/constant failures return a failed report; conversion failures can raise exceptions.

### `FmriQcMeasurements`

Frozen dataclass with `censored_fraction`, `registration_dice`, `centroid_distance_mm`, `parcels_present`, `parcels_with_10_voxels`, `finite_connectome`, and `minimum_filtered_regional_sd`. Supply scientifically valid measurements in the stated units. The dataclass does not validate physical ranges or field types.

### `evaluate_fmri_qc(measurements)`

Return an `FmriQcReport` with `passed`, a `criteria` mapping and `to_dict()`. The seven criteria are respectively <=0.20, >=0.70, <=8 mm, >=357, >=358, truthy finite-connectome status, and >0 standard deviation. All must pass. These fixed criteria belong to the originating method; their suitability for another study is not established. The helper does not measure them from images. For example, a physically impossible negative censored fraction is not separately rejected by this conjunction.

## Modelling

### `make_classifier(c=1.0, seed=1201)`

Keyword-only parameters. Return an unfitted scikit-learn pipeline: median imputation, standard scaling, balanced L2 logistic regression (`liblinear`, 5000 maximum iterations). `c` must be one of 0.001, 0.01, 0.1, 1, 10, otherwise `ValueError`. Cross-validation is the caller's responsibility. Preserve feature ordering and fit all steps within training folds.

### `select_balanced_threshold(y_true, probabilities)`

Return the median threshold among near-tied balanced-accuracy maximizers on the 0.05 to 0.95 grid with 0.005 spacing. Decisions use `probability >= threshold`. Labels are cast to integers; shape equality, two unique labels and finite probabilities are checked. Callers must additionally provide one-dimensional {0, 1} labels and probabilities in [0, 1], which this helper does not fully enforce. Use training out-of-fold predictions only.

### `average_repeated_predictions(predictions)`

Return the axis-zero mean of a finite, two-dimensional repeat-by-record probability matrix in [0, 1]. Invalid rank, nonfinite values or out-of-range probabilities raise `ValueError`. Callers must ensure at least one repeat and one record; an empty repeat dimension is not explicitly rejected. Mean probabilities and majority threshold decisions are different summaries.

## Identity and provenance

### `ObservationIdentity(namespace, subject, session, run, modality)`

Frozen dataclass. Every component must match `[A-Za-z0-9][A-Za-z0-9_.-]*`, otherwise `ValueError`. Values are case sensitive. `observation_key` is the four-tuple excluding modality; `to_dict()` retains all five fields. No identity is inferred from filenames.

### `checked_join(left, right, cardinality=...)`

Return `(left_index, right_index)` pairs in left order. Supports keyword-only `one_to_one` and `many_to_one`. Sequences must be nonempty identities, without complete duplicates, and cover exactly the same observation keys. Right keys must be unique; left keys must also be unique for one-to-one. Distinct left modalities can share a key for many-to-one. Missing/extra keys, namespace collisions and cardinality violations raise `ValueError`; records are never silently dropped.

### `canonical_json(payload)`

Return JSON text using sorted object keys, compact separators, ASCII escaping and rejection of NaN/infinity. Array order matters. This is a project serialization convention, not RFC 8785. Standard JSON conversion exceptions propagate.

### `create_execution_manifest(root, derivative_id=..., inputs=..., outputs=..., configuration=..., software=..., environment=..., seed=...)`

All parameters after `root` are keyword only. Return a detached JSON envelope with payload and SHA-256 digest; no files are written. Input/output lists must be nonempty, unique, disjoint, existing root-relative POSIX file paths. Traversal, absolute paths, backslashes and symlink escapes are rejected. Configuration must be a finite JSON mapping. Software requires string fields `name`, `version`, `revision`; environment is a nonempty string mapping supplied by the caller. Seed is a nonnegative integer, not a boolean; derivative ID is an ASCII identity token. Invalid contracts raise `ValueError`. File I/O errors can propagate. Environment values are recorded, not independently discovered.

### `verify_execution_manifest(manifest, root, expected_configuration=..., expected_manifest_sha256=None)`

Keyword-only expectations. Validate exact schema, configuration, envelope and file hashes; return a detached payload. An optional independently trusted digest also binds the envelope. Invalid contracts raise `ValueError`; I/O errors can propagate. Matching hashes establish consistency with a reference, not authorship, biological identity or proof that the recorded process ran.

```pycon
>>> from neurofusion_qa import ObservationIdentity, checked_join, canonical_json
>>> left = [ObservationIdentity('demo', 'exampleA', 'visitA', 'runA', 'eeg')]
>>> right = [ObservationIdentity('demo', 'exampleA', 'visitA', 'runA', 'fmri')]
>>> checked_join(left, right, cardinality='one_to_one')
[(0, 0)]
>>> canonical_json({'b': 2, 'a': 1})
'{"a":1,"b":2}'
```

## Feature submodule

Import these functions from `neurofusion_qa.features`; they are not root exports.

`eeg_features_33(signal, sampling_rate=250)` expects a finite channel-by-sample matrix with at least two channels and two seconds. It returns 33 float values. Welch estimation uses a Hann window, two-second segments, 50% overlap, constant detrending and median averaging. The five inclusive bands are 1-4, 4-8, 8-13, 13-30 and 30-45 Hz; boundary bins can appear in neighboring bands. The order is:

1. Fifteen band-major values: channel median, interquartile range and population standard deviation of band power for each band.
2. Theta/alpha, beta/alpha and delta/alpha ratios of median powers.
3. Normalized spectral entropy, alpha peak (8-14 Hz), 95% spectral edge (1-45 Hz) and log-log spectral slope.
4. Upper-triangle channel-correlation mean, absolute mean, standard deviation, P10, P50, P90, maximum-eigenvalue fraction and normalized eigenvalue entropy.
5. Median Hjorth activity, mobility and complexity.

Power and activity use input amplitude squared; peak and edge use Hz. Ratios, entropy and slope are dimensionless. Hjorth differences are per sample index, so mobility is not frequency in Hz. Invalid inputs raise `ValueError`; nonfinite output raises `RuntimeError`. Do not interpret synthetic contract tests as physiological validation.

`fisher_connectivity(regional_series)` requires at least two finite, nonconstant regional time series with at least two samples. Return a symmetric Fisher-z Pearson-correlation matrix, clipped before transformation at +/-0.999999, with a zero diagonal. Invalid or constant inputs raise `ValueError`.

`fmri_features_1440(regional_series, sampling_rate=1.25)` requires 360 prefiltered regional rows. Return four consecutive blocks of 360 values: mean Fisher-z connectivity strength (zero diagonal included in the divisor), low-frequency amplitude (ALFF), fractional amplitude (fALFF), and population standard deviation. The periodogram uses constant detrending. ALFF sums square-root PSD bins from 0.01 to 0.10 Hz; the fALFF denominator sums from 0.01 to 0.25 Hz. This discrete amplitude sum is not trapezoidal integration or a claim of equivalence to another toolbox. Connectivity and fALFF are dimensionless; ALFF is a sum of amplitude-density values and SD uses input units. Preserve the regional/atlas order.

## Evaluation submodule

Import from `neurofusion_qa.evaluation`. These helpers retain originating-method conventions and are not substitutes for the frozen notebook-03 evaluator.

`prediction_profile(y_true, probabilities)` returns ROC AUC, average precision, Brier score and log loss. It casts labels to integers and clips probabilities to [1e-6, 1-1e-6] before all four metrics, including Brier. Notebook 03 instead computes Brier on original probabilities. Supply valid matched binary arrays; scikit-learn exceptions can propagate.

`paired_subject_bootstrap(y_true, reference, candidate, metric, n_resamples=5000, seed=20260816)` resamples matched record indices uniformly, skips single-class resamples, and returns candidate-minus-reference difference, percentile bounds and valid resample count. It checks shape equality, not every scientific input assumption. Its sampling is not notebook 03's seed/class-stratified bootstrap. Intervals condition on predictions and do not refit models.

`gate_validity(binary_utility, continuous_utility, fmri_weight, n_resamples=5000, seed=20260816)` returns utility-sign ROC AUC, Spearman correlation and their bootstrap bounds, plus the Spearman p value. It checks matched shapes, two unique integer-cast labels and finite continuous inputs. Callers must supply binary {0, 1} utility, meaningful weights and nonconstant rank inputs. It does not enforce [0, 1] weights. Degenerate bootstrap draws are skipped; no valid draws raises `ValueError`.

The bootstrap parameters after the metric/weight are keyword only. Seeded replay is expected within a fixed environment; bitwise equivalence across arbitrary dependency/platform combinations is not guaranteed.
