"""Direct numerical oracles for the previously unmeasured gate-validity API."""
import numpy as np
import pytest
from scipy.stats import rankdata

from neurofusion_qa.evaluation import gate_validity, paired_subject_bootstrap, prediction_profile


def auc_pairwise(binary, score):
    difference = score[binary == 1, None] - score[None, binary == 0]
    return np.mean((difference > 0) + .5 * (difference == 0))


def rho_from_ranks(first, second):
    return np.corrcoef(rankdata(first), rankdata(second))[0, 1]


def test_gate_validity_matches_pairwise_auc_rank_correlation_and_bootstrap():
    weight = np.linspace(.02, .98, 40)
    utility = np.sin(np.arange(40) * .7) + weight
    binary = (np.arange(40) % 3 == 0).astype(int)
    seed, resamples = 20261011, 64
    result = gate_validity(binary, utility, weight, seed=seed, n_resamples=resamples)
    assert result == gate_validity(binary, utility, weight, seed=seed, n_resamples=resamples)
    assert result['utility_auc'] == pytest.approx(auc_pairwise(binary, weight))
    assert result['spearman_rho'] == pytest.approx(rho_from_ranks(utility, weight))
    rng = np.random.default_rng(seed)
    auc_samples, rho_samples = [], []
    for _ in range(resamples):
        index = rng.integers(0, binary.size, size=binary.size)
        if np.unique(binary[index]).size == 2:
            auc_samples.append(auc_pairwise(binary[index], weight[index]))
        rho = rho_from_ranks(utility[index], weight[index])
        if np.isfinite(rho):
            rho_samples.append(rho)
    np.testing.assert_allclose([result['utility_auc_ci_low'], result['utility_auc_ci_high']],
                               np.quantile(auc_samples, [.025, .975]))
    np.testing.assert_allclose([result['spearman_ci_low'], result['spearman_ci_high']],
                               np.quantile(rho_samples, [.025, .975]))
    assert 0 <= result['spearman_p'] <= 1


def test_legacy_prediction_profile_retains_its_documented_probability_clipping():
    # This public legacy helper clips before all four metrics. The separate
    # frozen S01 comparator uses unmodified probabilities for its Brier metric.
    y = np.array([0, 0, 1, 1])
    probability = np.array([0, .25, .75, 1])
    clipped = np.clip(probability, 1e-6, 1 - 1e-6)
    result = prediction_profile(y, probability)
    assert result['roc_auc'] == 1 and result['average_precision'] == 1
    assert result['brier_score'] == pytest.approx(np.mean((y - clipped) ** 2))
    assert result['log_loss'] == pytest.approx(-np.mean(y * np.log(clipped) + (1 - y) * np.log1p(-clipped)))


@pytest.mark.parametrize('case', ['shape', 'one_class', 'nonfinite_utility', 'nonfinite_weight', 'zero_resamples'])
def test_gate_validity_rejects_invalid_or_unestimable_inputs(case):
    binary = np.array([0, 1] * 10)
    utility = np.linspace(-1, 1, 20)
    weight = np.linspace(.01, .99, 20)
    count = 16
    if case == 'shape':
        weight = weight[:-1]
    elif case == 'one_class':
        binary[:] = 0
    elif case == 'nonfinite_utility':
        utility[0] = np.inf
    elif case == 'nonfinite_weight':
        weight[0] = np.nan
    else:
        count = 0
    with pytest.raises(ValueError):
        gate_validity(binary, utility, weight, n_resamples=count)


def test_paired_bootstrap_rejects_unpaired_shapes():
    with pytest.raises(ValueError, match='same shape'):
        paired_subject_bootstrap([0, 1], [.2], [.3, .8], lambda y, p: float(np.mean(p)), n_resamples=16)
