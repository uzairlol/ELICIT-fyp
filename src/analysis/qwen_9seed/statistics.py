"""Small, dependency-light statistical helpers for the Qwen analysis.

The experiment has only nine independent run files, so helpers deliberately
make the resampling unit explicit.  In particular, functions that accept
agent-round observations should receive a run-level table or a cluster id;
ordinary iid bootstrap intervals over rows would be too optimistic.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import numpy as np
import pandas as pd


def _clean(values: Iterable[Any]) -> np.ndarray:
    """Return finite numeric values as a one-dimensional float array."""
    arr = pd.to_numeric(pd.Series(list(values)), errors="coerce").to_numpy(dtype=float)
    return arr[np.isfinite(arr)]


def percentile_ci(
    values: Iterable[Any],
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_boot: int = 10_000,
    seed: int = 20260925,
    alpha: float = 0.05,
) -> dict[str, float | int | None]:
    """Bootstrap a statistic over independent observations.

    The caller should pass one value per run (or another prespecified
    independent unit), not one row per agent-round unless that row is truly a
    replicate.  The returned interval is a percentile interval and is intended
    as a transparent descriptive uncertainty summary for this small sample.
    """
    arr = _clean(values)
    n = len(arr)
    if n == 0:
        return {"estimate": None, "lower": None, "upper": None, "n": 0, "n_boot": 0}
    estimate = float(statistic(arr))
    if n == 1:
        return {
            "estimate": estimate,
            "lower": estimate,
            "upper": estimate,
            "n": 1,
            "n_boot": 0,
        }
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n, size=(n_boot, n))
    estimates = np.asarray([statistic(arr[idx]) for idx in draws], dtype=float)
    lo, hi = np.quantile(estimates, [alpha / 2, 1 - alpha / 2])
    return {
        "estimate": estimate,
        "lower": float(lo),
        "upper": float(hi),
        "n": int(n),
        "n_boot": int(n_boot),
    }


def paired_percentile_ci(
    before: Iterable[Any],
    after: Iterable[Any],
    n_boot: int = 10_000,
    seed: int = 20260925,
    alpha: float = 0.05,
) -> dict[str, float | int | None]:
    """Bootstrap the paired mean change ``after - before`` over runs."""
    left = pd.to_numeric(pd.Series(list(before)), errors="coerce").reset_index(drop=True)
    right = pd.to_numeric(pd.Series(list(after)), errors="coerce").reset_index(drop=True)
    if len(left) != len(right):
        raise ValueError("Paired vectors must have equal length")
    valid = left.notna() & right.notna()
    diff = (right[valid] - left[valid]).to_numpy(dtype=float)
    result = percentile_ci(diff, np.mean, n_boot=n_boot, seed=seed, alpha=alpha)
    result["n_pairs"] = int(valid.sum())
    return result


def exact_sign_flip_pvalue(differences: Iterable[Any]) -> float:
    """Two-sided exact sign-flip p-value for a paired mean difference.

    With nine runs there are only 512 sign assignments, making an exact paired
    randomization-style reference distribution feasible.  Zero differences are
    retained in the sign assignment and therefore do not change the reference
    distribution's denominator.  This is a descriptive robustness check, not a
    claim that the temporal comparison is randomized.
    """
    arr = _clean(differences)
    n = len(arr)
    if n == 0:
        return float("nan")
    observed = abs(float(np.mean(arr)))
    signs = np.array(np.meshgrid(*[[-1.0, 1.0]] * n)).T.reshape(-1, n)
    # The meshgrid expression above is memory-safe for the intended n <= 20;
    # fall back to iterative generation if a future design has more runs.
    if n > 20:
        signs = np.random.default_rng(0).choice([-1.0, 1.0], size=(200_000, n))
    null = np.abs((signs * arr).mean(axis=1))
    if n <= 20:
        # Complete enumeration: no pseudo-count is needed.
        return float(np.sum(null >= observed - 1e-15) / len(null))
    # Monte Carlo sensitivity for a future design with more than 20 runs.
    return float((np.sum(null >= observed - 1e-15) + 1) / (len(null) + 1))


def cliffs_delta(a: Iterable[Any], b: Iterable[Any]) -> float:
    """Cliff's delta for a paired or independent comparison, as applicable.

    For paired data, each run's after value is compared with its before value;
    ties receive half credit.  The returned value is in [-1, 1].
    """
    left = pd.to_numeric(pd.Series(list(a)), errors="coerce").reset_index(drop=True)
    right = pd.to_numeric(pd.Series(list(b)), errors="coerce").reset_index(drop=True)
    if len(left) != len(right):
        left, right = _clean(left), _clean(right)
        if len(left) != len(right):
            return float("nan")
        x, y = left, right
    else:
        mask = left.notna() & right.notna()
        x, y = right[mask].to_numpy(), left[mask].to_numpy()
    if len(x) == 0:
        return float("nan")
    delta = sum(1.0 if xv > yv else 0.5 if xv == yv else 0.0 for xv, yv in zip(x, y, strict=True))
    return float((2 * delta / len(x)) - 1)


def cohen_dz(differences: Iterable[Any]) -> float:
    """Standardized mean paired change, with a safe zero-SD fallback."""
    arr = _clean(differences)
    if len(arr) < 2:
        return float("nan")
    sd = float(np.std(arr, ddof=1))
    return float(np.mean(arr) / sd) if sd > 0 else float("nan")


def gini(values: Iterable[Any]) -> float:
    """Compute the nonnegative Gini coefficient, returning NaN when undefined."""
    arr = _clean(values)
    arr = arr[arr >= 0]
    n = len(arr)
    total = float(arr.sum())
    if n == 0 or total == 0:
        return float("nan")
    ordered = np.sort(arr)
    weights = np.arange(1, n + 1, dtype=float)
    return float((2 * np.sum(weights * ordered) / (n * total)) - (n + 1) / n)


def top_share(values: Iterable[Any], fraction: float = 0.10) -> float:
    """Share of a nonnegative total held by the top ``fraction`` of values."""
    arr = _clean(values)
    arr = arr[arr >= 0]
    n = len(arr)
    if n == 0 or arr.sum() == 0:
        return float("nan")
    k = max(1, int(np.ceil(n * fraction)))
    return float(np.sort(arr)[-k:].sum() / arr.sum())


def hhi(values: Iterable[Any]) -> float:
    """Herfindahl-Hirschman concentration index for nonnegative values."""
    arr = _clean(values)
    arr = arr[arr >= 0]
    total = float(arr.sum())
    if total == 0:
        return float("nan")
    return float(np.sum((arr / total) ** 2))


def cluster_bootstrap(
    frame: pd.DataFrame,
    value: str,
    cluster: str,
    statistic: Callable[[pd.DataFrame], float] | None = None,
    n_boot: int = 5_000,
    seed: int = 20260925,
    alpha: float = 0.05,
) -> dict[str, float | int | None]:
    """Bootstrap a statistic after resampling whole clusters (runs)."""
    if statistic is None:

        def statistic(frame: pd.DataFrame) -> float:
            return float(pd.to_numeric(frame[value]).mean())

    if value not in frame or cluster not in frame:
        return {"estimate": None, "lower": None, "upper": None, "n_clusters": 0, "n_rows": 0}
    clusters = frame[cluster].dropna().unique()
    n_clusters = len(clusters)
    if n_clusters == 0:
        return {"estimate": None, "lower": None, "upper": None, "n_clusters": 0, "n_rows": 0}
    estimate = float(statistic(frame))
    if n_clusters == 1:
        return {
            "estimate": estimate,
            "lower": estimate,
            "upper": estimate,
            "n_clusters": 1,
            "n_rows": len(frame),
        }
    rng = np.random.default_rng(seed)
    groups = {key: frame[frame[cluster] == key] for key in clusters}
    estimates = []
    for _ in range(n_boot):
        selected = rng.choice(clusters, size=n_clusters, replace=True)
        sample = pd.concat([groups[key] for key in selected], ignore_index=True)
        value_stat = statistic(sample)
        if np.isfinite(value_stat):
            estimates.append(value_stat)
    if not estimates:
        return {
            "estimate": estimate,
            "lower": float("nan"),
            "upper": float("nan"),
            "n_clusters": n_clusters,
            "n_rows": len(frame),
        }
    lo, hi = np.quantile(estimates, [alpha / 2, 1 - alpha / 2])
    return {
        "estimate": estimate,
        "lower": float(lo),
        "upper": float(hi),
        "n_clusters": int(n_clusters),
        "n_rows": len(frame),
    }
