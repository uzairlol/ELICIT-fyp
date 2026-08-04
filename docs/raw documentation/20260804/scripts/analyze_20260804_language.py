#!/usr/bin/env python3
"""
Prompt 6: SI vs SFI language comparison for 20260804 reasoning corpora.

Run from repo root:
  python "docs/raw documentation/20260804/scripts/analyze_20260804_language.py"
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "docs" / "raw documentation" / "20260804"
TABLES = OUT / "tables"
PLOTS = OUT / "plots"
RUN = "20260804_024555"

# Keep economically meaningful terms; remove only function words / boilerplate IDs
STOP = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "to", "of", "in",
    "on", "for", "with", "as", "by", "at", "from", "is", "are", "was", "were",
    "be", "been", "being", "this", "that", "these", "those", "it", "its", "my",
    "me", "i", "we", "our", "you", "your", "they", "their", "them", "he", "she",
    "will", "would", "can", "could", "should", "may", "might", "must", "do",
    "does", "did", "not", "no", "nor", "so", "such", "into", "over", "under",
    "about", "also", "more", "most", "other", "some", "any", "all", "each",
    "both", "few", "own", "same", "too", "very", "just", "only", "because",
    "while", "when", "where", "which", "who", "whom", "what", "how", "there",
    "here", "out", "up", "down", "again", "further", "once", "have", "has",
    "had", "having", "am", "round", "agent", "agents", "based", "using",
    "make", "making", "take", "taking", "get", "got", "one", "two", "three",
}

# Light stem-like normalisation for common variants (manual, reproducible)
LEMMA = {
    "contributions": "contribution",
    "contributing": "contribution",
    "contributed": "contribution",
    "cooperating": "cooperate",
    "cooperation": "cooperate",
    "cooperative": "cooperate",
    "punishments": "punishment",
    "punishing": "punishment",
    "punished": "punishment",
    "rewards": "reward",
    "rewarding": "reward",
    "rewarded": "reward",
    "reputations": "reputation",
    "institutions": "institution",
    "institutional": "institution",
    "fairness": "fair",
    "unfair": "fair",
    "trustworthiness": "trust",
    "trusted": "trust",
    "losses": "loss",
    "damages": "damage",
    "shocks": "shock",
    "rules": "rule",
    "proposals": "proposal",
    "voting": "vote",
    "votes": "vote",
}

CONCEPTS = {
    "fairness": [r"\bfair\b", r"equit", r"unfair", r"inequit"],
    "reciprocity": [r"reciproc", r"return the favor", r"tit[- ]for[- ]tat"],
    "inequity": [r"inequit", r"unequal", r"disparit", r"gap between"],
    "self_interest": [r"self[- ]interest", r"my (own )?wealth", r"maximi[sz]e (my|own)", r"keep more"],
    "group_welfare": [r"collective", r"community", r"common good", r"public good", r"group welfare"],
    "reputation": [r"reputat", r"peer trust", r"trust score", r"image"],
    "punishment": [r"punish", r"sanction", r"tariff"],
    "reward": [r"reward", r"subsidy", r"aid"],
    "conformity": [r"average contribution", r"group average", r"peers? are", r"conform"],
    "trust": [r"\btrust\b", r"trustworthy", r"untrust"],
    "strategic_adaptation": [r"adapt", r"adjust", r"strateg", r"next round", r"future"],
    "institutional_choice": [r"\bSI\b", r"\bSFI\b", r"institution", r"treaty", r"agreement"],
    "future_interaction": [r"future", r"long[- ]term", r"later rounds", r"upcoming"],
    "shocks": [r"shock", r"disaster", r"climate damage", r"damage"],
    "redistribution": [r"redistribut", r"LDF", r"payout", r"loss and damage", r"equity weight"],
    "uncertainty": [r"uncertain", r"risk", r"unpredict", r"might", r"maybe", r"unclear"],
}


def tokenize(text: str) -> list[str]:
    text = str(text or "").lower()
    text = re.sub(r"agent\s*\d+", " ", text)
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    toks = []
    for t in text.split():
        t = t.strip("-")
        if not t or t.isdigit() or len(t) <= 2:
            continue
        if t in STOP:
            continue
        t = LEMMA.get(t, t)
        if t in STOP:
            continue
        toks.append(t)
    return toks


def ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def load_blocks() -> pd.DataFrame:
    df = pd.read_csv(TABLES / "reasoning_blocks.csv")
    # drop proposal_reason with empty institution; assign from profiles if needed
    profiles = pd.read_csv(TABLES / "agent_strategy_profiles.csv")[
        ["agent_id", "institution_choice"]
    ].rename(columns={"institution_choice": "inst_profile"})
    df = df.merge(profiles, on="agent_id", how="left")
    df["institution"] = df["institution_choice"].where(
        df["institution_choice"].isin(["SI", "SFI"]), df["inst_profile"]
    )
    df = df[df["institution"].isin(["SI", "SFI"])].copy()
    df["tokens"] = df["text"].map(tokenize)
    df["n_tokens"] = df["tokens"].map(len)
    return df


def corpus_stats(df: pd.DataFrame, label: str) -> dict:
    return {
        "corpus": label,
        "n_blocks": int(len(df)),
        "n_agents": int(df["agent_id"].nunique()),
        "n_rounds": int(df["round_number"].nunique()),
        "total_tokens": int(df["n_tokens"].sum()),
        "mean_block_chars": float(df["text_length"].mean()) if "text_length" in df else float(df["text"].str.len().mean()),
        "mean_block_tokens": float(df["n_tokens"].mean()),
        "missing_empty_text": int((df["text"].fillna("").str.strip() == "").sum()),
    }


def build_corpora(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    shocks = set(
        pd.read_csv(TABLES / "climatic_shocks.csv")
        .query("shock_occurred == 1")["round_number"]
        .tolist()
    )
    panel = pd.read_csv(TABLES / "reputation_gossip_panel.csv")[
        ["round_number", "agent_id", "bad_rep_prev", "gossip_prev"]
    ]
    m = df.merge(panel, on=["round_number", "agent_id"], how="left")
    m["post_shock"] = m["round_number"].isin({s + 1 for s in shocks}) | m["round_number"].isin(shocks)

    corpora = {
        "SI_all": m[m["institution"] == "SI"],
        "SFI_all": m[m["institution"] == "SFI"],
        "SI_contribution": m[(m["institution"] == "SI") & (m["kind"] == "contribution")],
        "SFI_contribution": m[(m["institution"] == "SFI") & (m["kind"] == "contribution")],
        "SI_proposal_reason": m[(m["institution"] == "SI") & (m["kind"] == "proposal_reason")],
        "SFI_proposal_reason": m[(m["institution"] == "SFI") & (m["kind"] == "proposal_reason")],
        # votes not in reasoning_blocks; skip dedicated vote corpus unless present
        "SI_post_shock": m[(m["institution"] == "SI") & (m["post_shock"] == True) & (m["kind"] == "contribution")],
        "SFI_post_shock": m[(m["institution"] == "SFI") & (m["post_shock"] == True) & (m["kind"] == "contribution")],
        "SI_post_gossip": m[(m["institution"] == "SI") & (m["gossip_prev"] == 1) & (m["kind"] == "contribution")],
        "SFI_post_gossip": m[(m["institution"] == "SFI") & (m["gossip_prev"] == 1) & (m["kind"] == "contribution")],
        "SI_post_badrep": m[(m["institution"] == "SI") & (m["bad_rep_prev"] == 1) & (m["kind"] == "contribution")],
        "SFI_post_badrep": m[(m["institution"] == "SFI") & (m["bad_rep_prev"] == 1) & (m["kind"] == "contribution")],
        # comparable kinds only (exclude SI-only punishment)
        "SI_shared_kinds": m[
            (m["institution"] == "SI")
            & (m["kind"].isin(["contribution", "belief_strategy", "belief_observations", "institution"]))
        ],
        "SFI_shared_kinds": m[
            (m["institution"] == "SFI")
            & (m["kind"].isin(["contribution", "belief_strategy", "belief_observations", "institution"]))
        ],
    }
    return corpora


def count_ngrams(df: pd.DataFrame, n: int) -> Counter:
    c = Counter()
    for toks in df["tokens"]:
        c.update(ngrams(toks, n) if n > 1 else toks)
    return c


def freq_table(counter: Counter, total: int, label: str) -> pd.DataFrame:
    rows = []
    for term, cnt in counter.most_common():
        rows.append(
            {
                "corpus": label,
                "term": term,
                "count": cnt,
                "freq": cnt / total if total else 0.0,
            }
        )
    return pd.DataFrame(rows)


def log_odds_dirichlet(c1: Counter, c2: Counter, alpha: float = 0.01) -> pd.DataFrame:
    """Monroe et al. informative Dirichlet prior log-odds."""
    vocab = set(c1) | set(c2)
    n1 = sum(c1.values())
    n2 = sum(c2.values())
    a0 = alpha * len(vocab)
    rows = []
    for w in vocab:
        y1 = c1.get(w, 0)
        y2 = c2.get(w, 0)
        # prior from pooled
        prior = alpha
        lod = (
            math.log(y1 + prior)
            - math.log(n1 + a0 - y1 - prior)
            - math.log(y2 + prior)
            + math.log(n2 + a0 - y2 - prior)
        )
        var = 1 / (y1 + prior) + 1 / (y2 + prior)
        z = lod / math.sqrt(var) if var > 0 else 0.0
        rows.append(
            {
                "term": w,
                "count_SI": y1,
                "count_SFI": y2,
                "log_odds_SI_minus_SFI": lod,
                "z": z,
            }
        )
    return pd.DataFrame(rows).sort_values("z", ascending=False)


def tfidf_top(df_si: pd.DataFrame, df_sfi: pd.DataFrame, top_k: int = 30) -> pd.DataFrame:
    docs = [
        " ".join(t for toks in df_si["tokens"] for t in toks),
        " ".join(t for toks in df_sfi["tokens"] for t in toks),
    ]
    vec = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b", min_df=1)
    X = vec.fit_transform(docs)
    terms = np.array(vec.get_feature_names_out())
    rows = []
    for i, label in enumerate(["SI", "SFI"]):
        weights = X[i].toarray().ravel()
        idx = weights.argsort()[::-1][:top_k]
        for j in idx:
            rows.append({"corpus": label, "term": terms[j], "tfidf": float(weights[j])})
    return pd.DataFrame(rows)


def concept_freqs(df: pd.DataFrame, label: str) -> dict:
    texts = " \n ".join(df["text"].fillna("").astype(str).tolist())
    out = {"corpus": label, "n_blocks": len(df)}
    for name, pats in CONCEPTS.items():
        hits = 0
        for _, row in df.iterrows():
            t = str(row["text"])
            if any(re.search(p, t, flags=re.I) for p in pats):
                hits += 1
        out[name] = hits
        out[f"{name}_rate"] = hits / len(df) if len(df) else 0.0
    return out


def agent_leave_one_out_keyness(df: pd.DataFrame) -> pd.DataFrame:
    """Check whether SI-SFI unigram keyness is dominated by one agent."""
    base_si = count_ngrams(df[df["institution"] == "SI"], 1)
    base_sfi = count_ngrams(df[df["institution"] == "SFI"], 1)
    base = log_odds_dirichlet(base_si, base_sfi)
    top_si = set(base.head(15)["term"])
    top_sfi = set(base.sort_values("z").head(15)["term"])
    rows = []
    for aid in sorted(df["agent_id"].unique()):
        sub = df[df["agent_id"] != aid]
        lod = log_odds_dirichlet(
            count_ngrams(sub[sub["institution"] == "SI"], 1),
            count_ngrams(sub[sub["institution"] == "SFI"], 1),
        )
        top_si_loo = set(lod.head(15)["term"])
        top_sfi_loo = set(lod.sort_values("z").head(15)["term"])
        rows.append(
            {
                "left_out_agent": aid,
                "jaccard_top15_SI_terms": len(top_si & top_si_loo) / len(top_si | top_si_loo),
                "jaccard_top15_SFI_terms": len(top_sfi & top_sfi_loo) / len(top_sfi | top_sfi_loo),
            }
        )
    return pd.DataFrame(rows)


def wordcloud_plot(counter: Counter, title: str, path: Path, color: str):
    # Simple frequency cloud without wordcloud lib dependency
    top = counter.most_common(40)
    if not top:
        return
    terms, freqs = zip(*top)
    freqs = np.array(freqs, dtype=float)
    sizes = 8 + 28 * (freqs - freqs.min()) / (freqs.max() - freqs.min() + 1e-9)
    rng = np.random.default_rng(abs(hash(title)) % (2**32))
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(title)
    for term, size in zip(terms, sizes):
        ax.text(
            rng.uniform(0.05, 0.95),
            rng.uniform(0.05, 0.95),
            term,
            fontsize=size,
            color=color,
            ha="center",
            va="center",
            alpha=0.85,
        )
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def keyness_bar(lod: pd.DataFrame, path: Path):
    top = pd.concat([lod.head(15), lod.tail(15)])
    fig, ax = plt.subplots(figsize=(9, 7))
    colors = ["#5B4B8A" if z > 0 else "#C47B2C" for z in top["z"]]
    ax.barh(top["term"], top["z"], color=colors)
    ax.axvline(0, color="#333", lw=1)
    ax.set_xlabel("z (log-odds SI âˆ’ SFI)")
    ax.set_title("Keyness: shared-kind reasoning (SI vs SFI)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def concept_bar(concept_df: pd.DataFrame, path: Path):
    # rates for SI_shared vs SFI_shared
    si = concept_df[concept_df["corpus"] == "SI_shared_kinds"].iloc[0]
    sfi = concept_df[concept_df["corpus"] == "SFI_shared_kinds"].iloc[0]
    names = list(CONCEPTS.keys())
    si_r = [si[f"{n}_rate"] for n in names]
    sfi_r = [sfi[f"{n}_rate"] for n in names]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - 0.2, si_r, 0.4, label="SI", color="#5B4B8A")
    ax.bar(x + 0.2, sfi_r, 0.4, label="SFI", color="#C47B2C")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Share of blocks with concept hit")
    ax.set_title("Concept rates in shared-kind corpora")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def example_blocks(df: pd.DataFrame, pattern: str, n: int = 3) -> list[dict]:
    rows = []
    for _, r in df.iterrows():
        if re.search(pattern, str(r["text"]), flags=re.I):
            rows.append(
                {
                    "evidence_id": r["evidence_id"],
                    "agent_id": int(r["agent_id"]),
                    "round": int(r["round_number"]),
                    "institution": r["institution"],
                    "kind": r["kind"],
                    "excerpt": str(r["text"])[:280],
                }
            )
        if len(rows) >= n:
            break
    return rows


def main() -> int:
    df = load_blocks()
    corpora = build_corpora(df)

    stats_rows = [corpus_stats(c, name) for name, c in corpora.items()]
    pd.DataFrame(stats_rows).to_csv(TABLES / "language_corpus_stats.csv", index=False)

    # Primary comparable comparison: shared kinds
    si = corpora["SI_shared_kinds"]
    sfi = corpora["SFI_shared_kinds"]
    c1 = count_ngrams(si, 1)
    c2 = count_ngrams(sfi, 1)
    b1 = count_ngrams(si, 2)
    b2 = count_ngrams(sfi, 2)
    t1 = count_ngrams(si, 3)
    t2 = count_ngrams(sfi, 3)

    freq_si = freq_table(c1, sum(c1.values()), "SI_shared_kinds")
    freq_sfi = freq_table(c2, sum(c2.values()), "SFI_shared_kinds")
    pd.concat([freq_si.head(100), freq_sfi.head(100)]).to_csv(
        TABLES / "language_term_freq_shared.csv", index=False
    )

    lod = log_odds_dirichlet(c1, c2)
    lod.to_csv(TABLES / "language_logodds_shared_unigrams.csv", index=False)
    lod_bi = log_odds_dirichlet(b1, b2)
    lod_bi.to_csv(TABLES / "language_logodds_shared_bigrams.csv", index=False)
    lod_tri = log_odds_dirichlet(t1, t2)
    lod_tri.to_csv(TABLES / "language_logodds_shared_trigrams.csv", index=False)

    tfidf = tfidf_top(si, sfi)
    tfidf.to_csv(TABLES / "language_tfidf_shared.csv", index=False)

    # contribution-only comparison
    lod_c = log_odds_dirichlet(
        count_ngrams(corpora["SI_contribution"], 1),
        count_ngrams(corpora["SFI_contribution"], 1),
    )
    lod_c.to_csv(TABLES / "language_logodds_contribution_unigrams.csv", index=False)

    concept_rows = [
        concept_freqs(corpora["SI_shared_kinds"], "SI_shared_kinds"),
        concept_freqs(corpora["SFI_shared_kinds"], "SFI_shared_kinds"),
        concept_freqs(corpora["SI_contribution"], "SI_contribution"),
        concept_freqs(corpora["SFI_contribution"], "SFI_contribution"),
        concept_freqs(corpora["SI_post_shock"], "SI_post_shock"),
        concept_freqs(corpora["SFI_post_shock"], "SFI_post_shock"),
    ]
    concept_df = pd.DataFrame(concept_rows)
    concept_df.to_csv(TABLES / "language_concept_rates.csv", index=False)

    loo = agent_leave_one_out_keyness(
        df[df["kind"].isin(["contribution", "belief_strategy", "belief_observations", "institution"])]
    )
    loo.to_csv(TABLES / "language_keyness_leave_one_out.csv", index=False)

    # wordclouds
    PLOTS.mkdir(parents=True, exist_ok=True)
    wordcloud_plot(c1, "SI shared-kind terms", PLOTS / "wordcloud_SI_shared.png", "#5B4B8A")
    wordcloud_plot(c2, "SFI shared-kind terms", PLOTS / "wordcloud_SFI_shared.png", "#C47B2C")
    wordcloud_plot(
        count_ngrams(corpora["SI_contribution"], 1),
        "SI contribution reasoning",
        PLOTS / "wordcloud_SI_contribution.png",
        "#5B4B8A",
    )
    wordcloud_plot(
        count_ngrams(corpora["SFI_contribution"], 1),
        "SFI contribution reasoning",
        PLOTS / "wordcloud_SFI_contribution.png",
        "#C47B2C",
    )
    keyness_bar(lod, PLOTS / "keyness_shared_unigrams.png")
    concept_bar(concept_df, PLOTS / "concept_rates_shared.png")

    examples = {
        "SI_punishment": example_blocks(df[df["institution"] == "SI"], r"punish", 3),
        "SFI_damage_or_ldf": example_blocks(df[df["institution"] == "SFI"], r"LDF|damage|payout|shock", 3),
        "SI_fair": example_blocks(df[df["institution"] == "SI"], r"fair", 3),
        "SFI_fair": example_blocks(df[df["institution"] == "SFI"], r"fair", 3),
        "SI_cooperate": example_blocks(corpora["SI_contribution"], r"cooperat", 3),
        "SFI_cooperate": example_blocks(corpora["SFI_contribution"], r"cooperat", 3),
    }

    summary = {
        "run": RUN,
        "primary_comparison": "SI_shared_kinds vs SFI_shared_kinds (excludes SI-only punishment blocks)",
        "corpus_stats": stats_rows,
        "top_SI_key_terms": lod.head(12)[["term", "z", "count_SI", "count_SFI"]].to_dict(orient="records"),
        "top_SFI_key_terms": lod.sort_values("z").head(12)[
            ["term", "z", "count_SI", "count_SFI"]
        ].to_dict(orient="records"),
        "top_SI_bigrams": lod_bi.head(10)[["term", "z"]].to_dict(orient="records"),
        "top_SFI_bigrams": lod_bi.sort_values("z").head(10)[["term", "z"]].to_dict(orient="records"),
        "loo_jaccard_SI_mean": float(loo["jaccard_top15_SI_terms"].mean()),
        "loo_jaccard_SFI_mean": float(loo["jaccard_top15_SFI_terms"].mean()),
        "loo_jaccard_SI_min": float(loo["jaccard_top15_SI_terms"].min()),
        "examples": examples,
    }
    with open(TABLES / "prompt6_numeric_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("Prompt 6 done")
    print("SI key", summary["top_SI_key_terms"][:5])
    print("SFI key", summary["top_SFI_key_terms"][:5])
    print("LOO jaccard", summary["loo_jaccard_SI_mean"], summary["loo_jaccard_SFI_mean"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
