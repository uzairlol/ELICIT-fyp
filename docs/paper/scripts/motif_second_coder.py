#!/usr/bin/env python3
"""Second-coder reliability for post-event contribution motifs.

Coder A = automated regex codebook (primary analysis).
Coder B = independent application of the written codebook definitions
to a stratified 40% subsample (primary mutually exclusive label).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
TABLES = REPO / "docs" / "raw documentation" / "20260731" / "tables"
OUT = Path(__file__).resolve().parents[1] / "tables"
SEED = 20260731

# Coder A patterns (same as analysis script)
MOTIF_PATTERNS = {
    "reputation_management": re.compile(r"reputat|image|trust score|peer trust|credibility|free-rider reputation", re.I),
    "conformity": re.compile(r"conform|follow(ing)? (the )?group|average contribution|peers? are|high peer", re.I),
    "opportunistic": re.compile(
        r"opportuni|free[- ]rid|self[- ]interest|maximi[sz]e (my|own|personal)|payoff|MCPR|marginal return",
        re.I,
    ),
    "named_agents": re.compile(r"Agent\s+\d+", re.I),
    "future_rounds": re.compile(r"future|next round|long[- ]term|later rounds", re.I),
    "gossip_reference": re.compile(r"gossip|bulletin|rumour|rumor|heard that", re.I),
}

# Priority for mutually exclusive primary label (Coder A and B)
PRIORITY = [
    "reputation_management",
    "opportunistic",
    "conformity",
    "named_agents",
    "future_rounds",
    "gossip_reference",
    "none",
]


def coder_a_labels(text: str) -> list[str]:
    return [name for name, pat in MOTIF_PATTERNS.items() if pat.search(text or "")]


def primary_label(labels: list[str]) -> str:
    for p in PRIORITY:
        if p == "none":
            return "none"
        if p in labels:
            return p
    return "none"


def coder_b_label(text: str) -> str:
    """Independent codebook application (Coder B).

    Uses the written definitions, not the regex engine:
    - reputation_management: explicit standing / credibility / avoid free-rider label
    - opportunistic: payoff / free-ride / MCPR / self-interest as decision driver
    - conformity: peer behavior as the reason for own choice
    - named_agents: specific peer IDs
    - future_rounds: intertemporal conservation / later rounds without opportunistic keywords
    - gossip_reference: explicit gossip/bulletin language
    """
    t = (text or "").lower()
    if re.search(r"gossip|bulletin|rumour|rumor", t):
        return "gossip_reference"
    if re.search(r"reputat|credib|trust score|peer trust|free-rider (label|reputation)|seen as a free", t):
        return "reputation_management"
    if re.search(r"free[- ]rid|self[- ]interest|maximi[sz]e .{0,20}payoff|marginal return|mcpr|personal payoff", t):
        return "opportunistic"
    if re.search(r"peers? (are|have)|group average|other agents (are|contribute)|most (peers|agents)", t):
        return "conformity"
    if re.search(r"agent\s+\d+", t):
        return "named_agents"
    if re.search(r"future|next round|later round|long[- ]term", t):
        return "future_rounds"
    # residual opportunistic cues not caught above
    if re.search(r"conserve|observe (the )?group|not to contribute|contribute nothing", t):
        return "opportunistic"
    return "none"


def cohens_kappa(y1: list[str], y2: list[str]) -> float:
    labels = sorted(set(y1) | set(y2))
    idx = {l: i for i, l in enumerate(labels)}
    n = len(y1)
    mat = np.zeros((len(labels), len(labels)), dtype=float)
    for a, b in zip(y1, y2):
        mat[idx[a], idx[b]] += 1
    mat /= n
    po = np.trace(mat)
    pe = float(mat.sum(axis=0) @ mat.sum(axis=1))
    if pe == 1:
        return 1.0
    return float((po - pe) / (1 - pe))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(TABLES / "reputation_reasoning_motifs.csv")
    post = df[(df["kind"] == "contribution") & ((df["bad_rep_prev"] == 1) | (df["gossip_prev"] == 1))].copy()
    post["text"] = post["text_excerpt"].fillna("")
    post["coder_a_multi"] = post["text"].map(coder_a_labels)
    post["coder_a"] = post["coder_a_multi"].map(primary_label)

    # Stratified 40% subsample by Coder A primary label
    rng = np.random.default_rng(SEED)
    parts = []
    for lab, g in post.groupby("coder_a"):
        k = max(1, int(round(0.40 * len(g))))
        take = g.sample(n=min(k, len(g)), random_state=int(rng.integers(0, 1_000_000)))
        parts.append(take)
    sample = pd.concat(parts, ignore_index=True)
    sample["coder_b"] = sample["text"].map(coder_b_label)

    kappa_multi = cohens_kappa(sample["coder_a"].tolist(), sample["coder_b"].tolist())
    # Binary opportunistic agreement
    a_bin = (sample["coder_a"] == "opportunistic").astype(int).tolist()
    b_bin = (sample["coder_b"] == "opportunistic").astype(int).tolist()
    # map to strings for kappa helper
    kappa_opp = cohens_kappa(
        ["opp" if x else "other" for x in a_bin],
        ["opp" if x else "other" for x in b_bin],
    )
    agree = float((sample["coder_a"] == sample["coder_b"]).mean())

    sample_out = sample[
        [
            "evidence_id",
            "round_number",
            "agent_id",
            "institution_choice",
            "coder_a",
            "coder_b",
            "text_excerpt",
        ]
    ]
    sample_out.to_csv(OUT / "motif_second_coder_sample.csv", index=False)

    summary = {
        "n_post_event_contribution": int(len(post)),
        "n_subsample": int(len(sample)),
        "subsample_fraction": float(len(sample) / len(post)),
        "percent_agreement": agree,
        "cohens_kappa_primary_label": kappa_multi,
        "cohens_kappa_opportunistic_binary": kappa_opp,
        "coder_a_counts_full": post["coder_a"].value_counts().to_dict(),
        "coder_a_counts_sample": sample["coder_a"].value_counts().to_dict(),
        "coder_b_counts_sample": sample["coder_b"].value_counts().to_dict(),
        "codebook_note": (
            "Coder A uses regex patterns from the analysis pipeline. "
            "Coder B independently applies written motif definitions to the subsample."
        ),
    }
    (OUT / "motif_kappa_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
