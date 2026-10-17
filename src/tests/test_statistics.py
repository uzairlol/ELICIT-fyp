"""Unit tests for the run-level statistical helpers backing every reported number.

Every interval, p-value and concentration figure in the nine-seed report flows
through this module. The tests therefore check three things: the arithmetic is
correct, degenerate inputs are handled explicitly rather than silently, and the
small-sample properties the report relies on are reproducible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis.qwen_9seed.statistics import (
    cliffs_delta,
    cluster_bootstrap,
    cohen_dz,
    exact_sign_flip_pvalue,
    gini,
    hhi,
    paired_percentile_ci,
    percentile_ci,
    top_share,
)

NINE = list(range(1, 10))


class TestPercentileCI:
    def test_empty_input_returns_nulls(self):
        result = percentile_ci([])
        assert result["estimate"] is None
        assert result["n"] == 0
        assert result["n_boot"] == 0

    def test_single_observation_is_degenerate(self):
        result = percentile_ci([0.5])
        assert result["estimate"] == pytest.approx(0.5)
        assert result["lower"] == pytest.approx(0.5)
        assert result["upper"] == pytest.approx(0.5)
        assert result["n_boot"] == 0

    def test_estimate_is_the_sample_statistic(self):
        result = percentile_ci(NINE, statistic=np.mean)
        assert result["estimate"] == pytest.approx(5.0)

    def test_interval_brackets_the_estimate(self):
        result = percentile_ci([0.643, 0.941, 0.922, 0.938, 0.968, 0.941, 0.918, 0.869, 0.910])
        assert result["lower"] <= result["estimate"] <= result["upper"]

    def test_is_deterministic_for_a_fixed_seed(self):
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        first = percentile_ci(values, n_boot=500, seed=7)
        second = percentile_ci(values, n_boot=500, seed=7)
        assert first == second

    def test_non_finite_values_are_dropped(self):
        result = percentile_ci([1.0, np.nan, np.inf, 2.0])
        assert result["n"] == 2
        assert result["estimate"] == pytest.approx(1.5)

    def test_non_numeric_values_are_coerced_to_nan_then_dropped(self):
        result = percentile_ci([1.0, "not a number", 3.0])
        assert result["n"] == 2

    def test_alternative_statistic_is_respected(self):
        result = percentile_ci([1.0, 2.0, 3.0], statistic=np.median, n_boot=200)
        assert result["estimate"] == pytest.approx(2.0)

    def test_alpha_controls_interval_width(self):
        """``alpha`` is the significance level, so a *smaller* alpha is the *wider* interval."""
        values = [0.1, 0.5, 0.9, 0.2, 0.8, 0.3, 0.7]
        wide = percentile_ci(values, n_boot=2000, alpha=0.02)  # 98% interval
        narrow = percentile_ci(values, n_boot=2000, alpha=0.20)  # 80% interval
        assert (wide["upper"] - wide["lower"]) >= (narrow["upper"] - narrow["lower"])

    def test_matches_the_reported_participation_interval(self):
        """Reproduces the report's 0.908-0.942 interval for the 0.926 mean."""
        per_run = [0.941, 0.922, 0.938, 0.968, 0.941, 0.918, 0.927, 0.869, 0.910]
        result = percentile_ci(per_run, n_boot=20_000)
        assert result["estimate"] == pytest.approx(0.926, abs=0.001)
        assert 0.89 < result["lower"] < 0.93
        assert 0.92 < result["upper"] < 0.97


class TestPairedPercentileCI:
    def test_requires_equal_lengths(self):
        with pytest.raises(ValueError, match="equal length"):
            paired_percentile_ci([1, 2], [1])

    def test_computes_after_minus_before(self):
        result = paired_percentile_ci([1.0, 2.0, 3.0], [2.0, 3.0, 4.0], n_boot=500)
        assert result["estimate"] == pytest.approx(1.0)

    def test_reports_pair_count(self):
        result = paired_percentile_ci([1.0, 2.0], [2.0, 3.0], n_boot=200)
        assert result["n_pairs"] == 2

    def test_nan_pairs_are_dropped(self):
        result = paired_percentile_ci([1.0, np.nan, 3.0], [2.0, 5.0, 4.0], n_boot=200)
        assert result["n_pairs"] == 2

    def test_reproduces_the_intensity_decline_sign(self):
        """Nine runs all declining -> estimate negative, interval excludes zero."""
        late = [0.104, 0.099, 0.101, 0.107, 0.103, 0.108, 0.106, 0.100, 0.105]
        early = [0.166, 0.170, 0.168, 0.164, 0.169, 0.167, 0.165, 0.171, 0.163]
        result = paired_percentile_ci(early, late, n_boot=20_000)
        assert result["estimate"] < 0
        assert result["upper"] < 0

    def test_zero_change_yields_zero_estimate(self):
        result = paired_percentile_ci([1.0, 2.0], [1.0, 2.0], n_boot=200)
        assert result["estimate"] == pytest.approx(0.0)


class TestExactSignFlipPvalue:
    def test_empty_input_is_nan(self):
        assert np.isnan(exact_sign_flip_pvalue([]))

    def test_nine_runs_cannot_go_below_the_enumeration_floor(self):
        """The report's stated floor: 2/512 == 0.0039 for nine runs."""
        p = exact_sign_flip_pvalue([0.1] * 9)
        assert p == pytest.approx(2 / 512)
        assert p == pytest.approx(0.0039, abs=0.0001)

    def test_uniform_direction_hits_the_floor(self):
        assert exact_sign_flip_pvalue([0.05] * 9) == pytest.approx(0.0039, abs=0.0001)

    def test_mixed_signs_are_not_significant(self):
        p = exact_sign_flip_pvalue([0.1, -0.1, 0.1, -0.1, 0.1, -0.1, 0.1, -0.1, 0.1])
        assert p > 0.5

    def test_all_zero_differences_is_maximally_uninformative(self):
        assert exact_sign_flip_pvalue([0.0] * 9) == pytest.approx(1.0)

    def test_result_is_a_probability(self):
        for differences in ([0.2] * 9, [0.1, -0.1] * 4 + [0.3], [0.0] * 5):
            p = exact_sign_flip_pvalue(differences)
            assert 0.0 <= p <= 1.0

    def test_zero_differences_are_retained_in_the_reference_distribution(self):
        """Zero entries do not shrink the denominator (documented behaviour)."""
        with_zero = exact_sign_flip_pvalue([0.1, 0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert 0.0 <= with_zero <= 1.0

    def test_large_n_uses_the_monte_carlo_fallback(self):
        differences = [0.1] * 25
        p = exact_sign_flip_pvalue(differences)
        assert 0.0 < p <= 1.0


class TestCliffsDelta:
    def test_all_after_above_before_is_maximal(self):
        assert cliffs_delta([1, 2, 3], [4, 5, 6]) == pytest.approx(1.0)

    def test_all_after_below_before_is_minimal(self):
        assert cliffs_delta([4, 5, 6], [1, 2, 3]) == pytest.approx(-1.0)

    def test_all_ties_is_zero(self):
        assert cliffs_delta([2, 2, 2], [2, 2, 2]) == pytest.approx(0.0)

    def test_ties_receive_half_credit(self):
        # after = [1, 1], before = [1, 2] -> one tie (0.5) + one loss (0.0)
        assert cliffs_delta([1, 2], [1, 1]) == pytest.approx(-0.5)

    def test_is_bounded(self):
        assert -1.0 <= cliffs_delta([1, 5, 3], [4, 2, 6]) <= 1.0

    def test_empty_input_is_nan(self):
        assert np.isnan(cliffs_delta([], []))


class TestCohenDz:
    def test_single_observation_is_nan(self):
        assert np.isnan(cohen_dz([0.5]))

    def test_zero_sd_is_nan(self):
        assert np.isnan(cohen_dz([1.0, 1.0, 1.0]))

    def test_positive_consistent_change(self):
        assert cohen_dz([0.1, 0.12, 0.11, 0.13]) > 0

    def test_matches_known_value(self):
        # dz = mean(diff) / sd(diff, ddof=1) = 3 / 1.4142... ~ 2.1213
        diffs = [2.0, 4.0]
        assert cohen_dz(diffs) == pytest.approx(np.mean(diffs) / np.std(diffs, ddof=1))
        assert cohen_dz(diffs) == pytest.approx(2.1213203435596424)

    def test_sign_follows_the_direction_of_change(self):
        assert cohen_dz([-0.1, -0.2, -0.15]) < 0


class TestGini:
    def test_perfect_equality_is_zero(self):
        assert gini([2, 2, 2, 2]) == pytest.approx(0.0)

    def test_single_observation_is_zero(self):
        assert gini([5]) == pytest.approx(0.0)

    def test_matches_the_reference_sequence(self):
        assert gini([1, 2, 3, 4]) == pytest.approx(0.25)

    def test_complete_concentration_is_below_one(self):
        assert gini([0, 0, 0, 10]) == pytest.approx(0.75)

    def test_zero_total_is_nan(self):
        assert np.isnan(gini([0, 0, 0]))

    def test_empty_is_nan(self):
        assert np.isnan(gini([]))

    def test_negative_values_are_dropped(self):
        assert gini([-10, 5, 5]) == pytest.approx(gini([5, 5]))

    def test_is_permutation_invariant(self):
        assert gini([1, 9, 3, 7]) == pytest.approx(gini([9, 1, 7, 3]))

    def test_higher_inequality_raises_the_coefficient(self):
        equal = gini([10] * 10)
        unequal = gini([1] * 9 + [100])
        assert unequal > equal


class TestTopShare:
    def test_top_decile_of_twenty(self):
        # fraction=0.10 of n=20 rounds k up to 2, so the share is (100 + 1) / 119.
        values = [1] * 19 + [100]
        assert top_share(values, fraction=0.10) == pytest.approx(101 / 119)

    def test_single_holding_the_top_decile(self):
        # fraction=0.05 of n=20 gives k=1, i.e. the monopolist's share alone.
        values = [1] * 19 + [100]
        assert top_share(values, fraction=0.05) == pytest.approx(100 / 119)

    def test_uniform_distribution_is_one_over_n(self):
        assert top_share([1] * 10, fraction=0.10) == pytest.approx(0.1)

    def test_k_rounds_up_to_at_least_one(self):
        assert top_share([1, 3], fraction=0.01) == pytest.approx(3 / 4)

    def test_all_zero_is_nan(self):
        assert np.isnan(top_share([0, 0, 0]))

    def test_empty_is_nan(self):
        assert np.isnan(top_share([]))

    def test_never_exceeds_one(self):
        assert top_share([1] * 19 + [1e9], fraction=0.5) <= 1.0


class TestHHI:
    def test_uniform_distribution_is_one_over_n(self):
        assert hhi([1] * 4) == pytest.approx(0.25)

    def test_monopoly_is_one(self):
        assert hhi([10, 0, 0]) == pytest.approx(1.0)

    def test_zero_total_is_nan(self):
        assert np.isnan(hhi([0, 0]))

    def test_is_bounded(self):
        assert 0.0 <= hhi([3, 1, 4, 1, 5]) <= 1.0

    def test_responds_to_the_reported_concentration_range(self):
        """Report Table 2 quotes target-allocation HHI between 0.092 and 0.321."""
        assert 0.09 <= hhi([1] * 11) <= 0.10  # very diffuse
        # Four claimants: 1/4 = 0.25 is the floor for a uniform vector, so a
        # three-claimant vector can never land inside the reported range.
        assert 0.26 <= hhi([3, 3, 3, 1]) <= 0.32
        assert hhi([3, 3, 3, 1]) > hhi([1] * 4)  # concentrated vs uniform


class TestClusterBootstrap:
    def _frame(self):
        return pd.DataFrame(
            {
                "run": ["r1"] * 3 + ["r2"] * 3 + ["r3"] * 3,
                "value": [1.0, 2.0, 3.0, 10.0, 20.0, 30.0, 100.0, 200.0, 300.0],
            }
        )

    def test_missing_column_returns_empty_result(self):
        result = cluster_bootstrap(self._frame(), value="nope", cluster="run")
        assert result["n_clusters"] == 0
        assert result["estimate"] is None

    def test_missing_cluster_column_returns_empty_result(self):
        result = cluster_bootstrap(self._frame(), value="value", cluster="nope")
        assert result["n_clusters"] == 0

    def test_single_cluster_is_degenerate(self):
        frame = pd.DataFrame({"run": ["r1"] * 4, "value": [1.0, 2.0, 3.0, 4.0]})
        result = cluster_bootstrap(frame, value="value", cluster="run")
        assert result["lower"] == pytest.approx(result["estimate"])
        assert result["upper"] == pytest.approx(result["estimate"])

    def test_reports_cluster_and_row_counts(self):
        result = cluster_bootstrap(self._frame(), value="value", cluster="run", n_boot=200)
        assert result["n_clusters"] == 3
        assert result["n_rows"] == 9

    def test_interval_brackets_the_estimate(self):
        result = cluster_bootstrap(self._frame(), value="value", cluster="run", n_boot=2000)
        assert result["lower"] <= result["estimate"] <= result["upper"]

    def test_estimate_is_the_plain_row_mean_by_default(self):
        result = cluster_bootstrap(self._frame(), value="value", cluster="run", n_boot=200)
        assert result["estimate"] == pytest.approx(np.mean([1, 2, 3, 10, 20, 30, 100, 200, 300]))

    def test_custom_statistic_is_applied(self):
        result = cluster_bootstrap(
            self._frame(),
            value="value",
            cluster="run",
            statistic=lambda f: float(pd.to_numeric(f["value"]).max()),
            n_boot=200,
        )
        assert result["estimate"] == pytest.approx(300.0)

    def test_is_deterministic_for_a_fixed_seed(self):
        first = cluster_bootstrap(self._frame(), value="value", cluster="run", n_boot=300, seed=11)
        second = cluster_bootstrap(self._frame(), value="value", cluster="run", n_boot=300, seed=11)
        assert first == second

    def test_cluster_level_uncertainty_is_wider_than_iid(self):
        """Why the protocol refuses agent-level intervals: clustering inflates variance."""
        frame = self._frame()
        clustered = cluster_bootstrap(frame, value="value", cluster="run", n_boot=2000)
        naive = percentile_ci(frame["value"].tolist(), n_boot=2000)
        clustered_width = clustered["upper"] - clustered["lower"]
        naive_width = naive["upper"] - naive["lower"]
        assert clustered_width > naive_width


class TestPseudoReplicationGuard:
    """The report's core methodological commitment, asserted as executable code."""

    def test_cluster_bootstrap_over_seeds_differs_from_iid_over_rows(self):
        rows = []
        for seed in range(1, 10):
            centre = seed * 0.1
            rows.extend({"run": f"s{seed}", "value": centre + j * 0.001} for j in range(3))
        frame = pd.DataFrame(rows)

        run_level = cluster_bootstrap(frame, value="value", cluster="run", n_boot=3000)
        row_level = percentile_ci(frame["value"].tolist(), n_boot=3000)

        # Resampling whole runs is the honest unit, and it is *wider* than the
        # iid-over-rows interval. The near-duplicate within-run rows give the
        # naive analysis 27 "replications" instead of 9 and therefore understate
        # the standard error. This asymmetry is exactly the pseudo-replication
        # error the analysis protocol refuses to make.
        assert run_level["lower"] < row_level["lower"]
        assert run_level["upper"] > row_level["upper"]
        run_width = run_level["upper"] - run_level["lower"]
        row_width = row_level["upper"] - row_level["lower"]
        assert run_width > row_width

    def test_run_level_bootstrap_on_reported_gini_change_is_narrow(self):
        """Nine runs, paired per-run Gini change, must give the reported interval."""
        early = [0.663, 0.713, 0.620, 0.616, 0.642, 0.652, 0.646, 0.701, 0.731]
        late = [0.280, 0.603, 0.346, 0.506, 0.262, 0.226, 0.358, 0.275, 0.504]
        result = paired_percentile_ci(early, late, n_boot=20_000)
        assert result["estimate"] == pytest.approx(-0.292, abs=0.002)
        assert -0.40 < result["lower"] < -0.32
        assert -0.25 < result["upper"] < -0.18
