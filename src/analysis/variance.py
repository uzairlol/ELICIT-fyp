"""Variance decomposition across model, prompt, condition and seed.

This is the single most persuasive object the paper can produce, because it puts
a number on the reliability question instead of an anecdote. TRAILS argues
robustness must be measured per claim and per model and provides no general
decomposition to borrow; this module is the general decomposition.

    Var(y) = sigma^2_model + sigma^2_prompt + sigma^2_condition + sigma^2_seed + eps^2

Two design facts make it interpretable:

* every non-model input is held identical inside a comparison group, which
  ``cli.config.check_grid_parity`` asserts rather than assumes; and
* inference is at the *run* level. Agent-rounds are not replications, so pooling
  7,020 of them into a variance estimate is the pseudo-replication error the
  existing protocol already refuses elsewhere.

The headline test is stated in advance: **if
``sigma^2_prompt + sigma^2_model > sigma^2_seed``, the result is an artefact of the
instrument rather than a property of the institution** — and that is a
publishable, quantitative, general finding rather than a null.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd


class VarianceDecompositionError(ValueError):
    """Raised when the frame cannot support a decomposition."""


#: Order matters: the report quotes model and prompt first, then condition, then
#: seed as the baseline, then residual.
DEFAULT_FACTORS: tuple[str, ...] = ("model", "prompt_variant", "condition", "seed")


def _cell_means(frame: pd.DataFrame, value: str) -> pd.Series:
    """One value per run, which is the only legitimate replication unit."""
    if value not in frame:
        raise VarianceDecompositionError(f"Value column {value!r} is not in the frame")
    series = pd.to_numeric(frame[value], errors="coerce")
    grouped = series.groupby(frame["run"], dropna=True)
    means = grouped.mean().dropna()
    if means.empty:
        raise VarianceDecompositionError(f"No finite values in {value!r}")
    return means


def variance_decomposition(
    frame: pd.DataFrame,
    value: str,
    factors: Sequence[str] = DEFAULT_FACTORS,
    *,
    run_column: str = "run",
) -> dict[str, Any]:
    """Nested-means variance decomposition of one outcome across run-level cells.

    Uses sequential (Type-I) sums of squares: factors are entered in the order
    given and each contributes the variance its predecessors leave unexplained.
    That is what makes ``sigma^2_seed`` a usable baseline — it is the residual
    spread after model, prompt and condition have already been accounted for,
    i.e. pure sampling noise at fixed everything.
    """
    if frame is None or frame.empty:
        raise VarianceDecompositionError(
            f"No runs to decompose. {value!r} needs at least two runs with provenance."
        )
    missing = [f for f in (run_column, *factors) if f not in frame]
    if missing:
        raise VarianceDecompositionError(f"Frame is missing columns: {missing}")

    work = frame.copy()
    work[run_column] = work[run_column].astype(str)
    means = _cell_means(work, value)
    if len(means) < 2:
        raise VarianceDecompositionError(
            f"At least two runs are needed to decompose {value!r}; got {len(means)}"
        )

    values = means.to_numpy(dtype=float)
    grand_mean = float(values.mean())
    total_ss = float(np.sum((values - grand_mean) ** 2))
    total_df = len(values) - 1
    total_ms = total_ss / total_df if total_df else float("nan")

    # Attach each run's factor levels onto its mean.
    levels = (
        work.drop_duplicates(subset=[run_column])[[run_column, *factors]]
        .set_index(run_column)
        .reindex(means.index)
    )

    contributions: dict[str, dict[str, float]] = {}
    residual = values.astype(float).copy()

    for factor in factors:
        groups = levels[factor].astype(str).to_numpy()
        residual_mean = float(residual.mean())
        between = 0.0
        df_between = 0
        # Within-group means, so the same quantity can be reused for the
        # projection below. Centring on the *current* residual mean (rather than
        # the original grand mean) is what keeps later factors from being
        # annihilated by the projection of the earlier ones.
        group_means = np.zeros(len(values), dtype=float)
        for level in np.unique(groups):
            mask = groups == level
            count = int(mask.sum())
            if count == 0:
                continue
            level_mean = float(np.mean(residual[mask]))
            group_means[mask] = level_mean
            between += count * (level_mean - residual_mean) ** 2
            df_between += count - 1
        contributions[factor] = {
            "ss": max(0.0, between),
            "df": df_between,
            "variance": max(0.0, between) / df_between if df_between else 0.0,
            "share_of_variance": max(0.0, between) / total_ss if total_ss else 0.0,
        }
        residual = residual - (group_means - residual_mean)

    residual_ss = float(np.sum((residual - residual.mean()) ** 2))
    residual_df = max(0, total_df - sum(c["df"] for c in contributions.values()))
    residual_var = residual_ss / residual_df if residual_df else 0.0

    instrument_ss = contributions.get("model", {}).get("ss", 0.0) + contributions.get(
        "prompt_variant", {}
    ).get("ss", 0.0)
    seed_ss = contributions.get("seed", {}).get("ss", 0.0)

    return {
        "value": value,
        "n_runs": len(values),
        "grand_mean": grand_mean,
        "total_ss": total_ss,
        "total_ms": total_ms,
        "factors": contributions,
        "residual": {
            "ss": residual_ss,
            "df": residual_df,
            "variance": residual_var,
            "share_of_variance": residual_ss / total_ss if total_ss else 0.0,
        },
        "variance_shares": {
            **{name: data["share_of_variance"] for name, data in contributions.items()},
            "residual": residual_ss / total_ss if total_ss else 0.0,
        },
        # The pre-committed headline test.
        "instrument_share": instrument_ss / total_ss if total_ss else 0.0,
        "seed_share": seed_ss / total_ss if total_ss else 0.0,
        "artifact_threshold_exceeded": bool(seed_ss > 0.0 and instrument_ss > seed_ss),
        "interpretation": (
            "sigma^2_prompt + sigma^2_model exceeds sigma^2_seed: the outcome is a "
            "property of the instrument (which model, which prompt) rather than of "
            "the institution."
            if seed_ss > 0.0 and instrument_ss > seed_ss
            else "sigma^2_seed dominates: the outcome is a property of sampling "
            "noise at fixed model, prompt and condition."
        ),
    }


def decomposition_table(frame: pd.DataFrame, values: Sequence[str], **kwargs: Any) -> pd.DataFrame:
    """Long-form table of every decomposition, ready for a figure or a claim."""
    rows: list[dict[str, Any]] = []
    for value in values:
        try:
            result = variance_decomposition(frame, value, **kwargs)
        except VarianceDecompositionError as exc:
            rows.append({"value": value, "error": str(exc)})
            continue
        row: dict[str, Any] = {
            "value": value,
            "n_runs": result["n_runs"],
            "grand_mean": result["grand_mean"],
            "instrument_share": result["instrument_share"],
            "seed_share": result["seed_share"],
            "artifact_threshold_exceeded": result["artifact_threshold_exceeded"],
        }
        for name, share in result["variance_shares"].items():
            row[f"share_{name}"] = share
        rows.append(row)
    return pd.DataFrame(rows)


def mcpr_for(beta: float, group_size: int) -> float:
    """Marginal return to the contributor: ``beta / n_G``."""
    return float(beta) / float(group_size) if group_size else float("inf")


def mcpr_response_curve(
    frame: pd.DataFrame,
    value: str = "contribution_intensity",
    *,
    beta_column: str = "beta",
    group_size_column: str = "group_size",
    outcome: str = "participation_rate",
    model_column: str | None = "model",
) -> pd.DataFrame:
    """Participation and intensity against MCPR, the Arm C prediction test.

    The pre-registered prediction is a *discontinuity at MCPR = 1*. The curve is
    the object that either shows it or does not, and either answer is publishable.

    Kept per model family, because the prediction is made across families rather
    than within one: a single family could produce a threshold for reasons that
    have nothing to do with the payoff structure.
    """
    columns = ["mcpr", "beta", "group_size", "n_runs", "participation_rate", "intensity"]
    has_model = bool(model_column and model_column in getattr(frame, "columns", []))
    output_columns = [*([str(model_column)] if has_model else []), *columns]
    if frame is None or frame.empty:
        return pd.DataFrame(columns=[*output_columns, "above_threshold"])

    required = {beta_column, group_size_column, value, outcome}
    if has_model:
        required.add(str(model_column))
    missing = required - set(frame)
    if missing:
        raise VarianceDecompositionError(f"Frame is missing columns: {sorted(missing)}")

    work = frame.dropna(subset=list(required)).copy()
    if work.empty:
        return pd.DataFrame(columns=[*output_columns, "above_threshold"])
    work["mcpr"] = work.apply(lambda r: mcpr_for(r[beta_column], int(r[group_size_column])), axis=1)

    keys = [str(model_column), "mcpr"] if has_model else ["mcpr"]
    rows = []
    for group_key, group in work.groupby(keys):
        entry = dict(
            zip(keys, group_key if isinstance(group_key, tuple) else (group_key,), strict=True)
        )
        rows.append(
            {
                **entry,
                "beta": float(group[beta_column].iloc[0]),
                "group_size": int(group[group_size_column].iloc[0]),
                "n_runs": int(group["run"].nunique()) if "run" in group else len(group),
                "participation_rate": float(pd.to_numeric(group[outcome]).mean()),
                "intensity": float(pd.to_numeric(group[value]).mean()),
                "above_threshold": bool(float(entry["mcpr"]) >= 1.0),  # type: ignore[arg-type]
            }
        )
    return (
        pd.DataFrame(rows)[[*output_columns, "above_threshold"]]
        .sort_values(
            [k for k in keys if k != model_column]
            + ([model_column] if model_column in keys else [])
        )
        .reset_index(drop=True)
    )


def threshold_discontinuity(
    curve: pd.DataFrame,
    outcome: str = "participation_rate",
    *,
    group_column: str | None = None,
) -> dict[str, Any]:
    """Difference in the outcome between the two sides of MCPR = 1.

    Reported as a plain difference with the point estimates, not as a significance
    test: with a handful of cells per side a p-value would overstate what the
    design supports. The comparison is descriptive and pre-specified.

    With ``group_column`` the contrast is computed per model family and pooled,
    because the prediction is made across families.
    """
    if curve.empty or outcome not in curve:
        return {"outcome": outcome, "available": False}

    def _one(subset: pd.DataFrame) -> dict[str, Any]:
        below = subset.loc[subset["mcpr"] < 1.0, outcome]
        above = subset.loc[subset["mcpr"] >= 1.0, outcome]
        result: dict[str, Any] = {
            "n_below": int(below.notna().sum()),
            "n_above": int(above.notna().sum()),
            "mean_below": float(below.mean()) if len(below) else float("nan"),
            "mean_above": float(above.mean()) if len(above) else float("nan"),
        }
        result["difference"] = result["mean_above"] - result["mean_below"]
        # A discontinuity means the jump across the boundary is larger than the
        # typical step between neighbouring points on either side.
        steps = subset[outcome].diff().abs().dropna()
        result["typical_step"] = float(steps.median()) if len(steps) else float("nan")
        result["discontinuity"] = bool(
            result["n_below"] > 0
            and result["n_above"] > 0
            and np.isfinite(result["typical_step"])
            and abs(result["difference"]) > result["typical_step"]
        )
        return result

    overall = _one(curve)
    result: dict[str, Any] = {"outcome": outcome, "available": True, **overall}
    if group_column and group_column in curve.columns:
        result["by_group"] = {
            str(name): _one(subset) for name, subset in curve.groupby(group_column)
        }
    return result


def summarise_decomposition(result: Mapping[str, Any]) -> str:
    """One-sentence reading of a decomposition, for a claim ledger entry."""
    shares = result["variance_shares"]
    ordered = sorted(shares.items(), key=lambda kv: -kv[1])
    parts = ", ".join(f"{name} {share:.1%}" for name, share in ordered if share > 1e-9)
    verdict = "ARTEFACT" if result["artifact_threshold_exceeded"] else "not an artefact"
    return f"{result['value']}: {parts or 'no variance'} -> {verdict}"
