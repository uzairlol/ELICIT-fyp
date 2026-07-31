#!/usr/bin/env python3
"""
Prompt 4: reputation / reconstructed-gossip event study, reasoning scan,
and per-agent strategy profiles for 20260731.

Run from repo root:
  python "docs/raw documentation/20260731/scripts/analyze_20260731_reputation_gossip.py"
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "docs" / "raw documentation" / "20260731"
TABLES = OUT / "tables"
PLOTS = OUT / "plots"
EVIDENCE = OUT / "evidence"
SOURCE_REL = (
    "results/To_Use/"
    "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json"
)
RUN = "20260731_013853"
GOSSIP_TRIGGER = 7.0
MAX_GOSSIP = 5
NEUTRAL_REP = 5.0
BAD_REP_THRESHOLD = 4.0  # strictly below neutral; documented as analyst threshold grounded in default=5
DROP_THRESHOLD = -1.0


MOTIF_PATTERNS = {
    "reputation_management": re.compile(r"reputat|image|trust score|peer trust", re.I),
    "shame_or_repair": re.compile(r"\b(shame|repair|restore|make up|regain)\b", re.I),
    "retaliation": re.compile(r"retaliat|punish(ing|ment)? (them|him|her|agent)|get back", re.I),
    "reciprocity": re.compile(r"reciproc|return (the )?favor|tit[- ]for[- ]tat", re.I),
    "conformity": re.compile(r"conform|follow(ing)? (the )?group|average contribution|peers? are", re.I),
    "fairness": re.compile(r"\bfair(ness)?\b|equit|unfair", re.I),
    "conditional_cooperation": re.compile(r"conditional|if others|as long as|provided that", re.I),
    "punishment_avoidance": re.compile(r"avoid.*punish|fear of punish|sanction", re.I),
    "future_rounds": re.compile(r"future|next round|long[- ]term|later rounds", re.I),
    "named_agents": re.compile(r"Agent\s+\d+", re.I),
    "gossip_reference": re.compile(r"gossip|bulletin|rumour|rumor|heard that", re.I),
    "opportunistic": re.compile(r"opportuni|free[- ]rid|self[- ]interest|maximi[sz]e (my|own)", re.I),
    "resistance": re.compile(r"ignore|dismiss|unreliable gossip|don't care|do not care", re.I),
}


def load_raw():
    with (REPO / SOURCE_REL).open(encoding="utf-8") as f:
        return json.load(f)


def reconstruct_gossip(rounds: list[dict]) -> pd.DataFrame:
    """Rebuild bulletin using compile_gossip logic on saved outgoing tom_scores.

    Limitation: original audit list order followed concurrent future completion;
    here audits are ordered by source agent_id then target id. Tie order among
    equal scores may differ from the live run.
    """
    rows = []
    for rd in rounds:
        rn = int(rd["round_number"])
        audits = []
        for src in sorted(rd["agents"].keys(), key=lambda x: int(x)):
            scores = rd["agents"][src].get("tom_scores") or {}
            for tgt, sc in sorted(scores.items(), key=lambda kv: int(kv[0])):
                audits.append(
                    {
                        "source": int(src),
                        "target": int(tgt),
                        "score": float(sc),
                    }
                )
        negative = [a for a in audits if a["score"] <= GOSSIP_TRIGGER]
        negative.sort(key=lambda a: (a["score"], a["source"], a["target"]))
        bulletin = negative[:MAX_GOSSIP]
        for rank, item in enumerate(bulletin):
            rows.append(
                {
                    "run": RUN,
                    "round_number": rn,
                    "bulletin_rank": rank,
                    "source": item["source"],
                    "target": item["target"],
                    "score": item["score"],
                    "reconstruction_note": "from saved tom_scores; tie-order approx",
                }
            )
    return pd.DataFrame(rows)


def build_panel(rounds: list[dict], gossip_df: pd.DataFrame) -> pd.DataFrame:
    contrib = pd.read_csv(TABLES / "contributions.csv")
    rep = pd.read_csv(TABLES / "reputation_events.csv")
    panel = contrib.merge(
        rep[
            [
                "round_number",
                "agent_id",
                "reputation",
                "reputation_delta",
                "tom_scores_count",
            ]
        ],
        on=["round_number", "agent_id"],
        how="left",
    )
    # gossip targets this round (end-of-round bulletin)
    targets = (
        gossip_df.groupby("round_number")["target"]
        .apply(lambda s: set(s.tolist()))
        .to_dict()
    )
    panel["in_gossip_bulletin"] = panel.apply(
        lambda r: int(r["agent_id"] in targets.get(r["round_number"], set())),
        axis=1,
    )
    # reputation events (end of round)
    panel["bad_rep"] = (panel["reputation"] < BAD_REP_THRESHOLD).astype(int)
    panel["rep_drop"] = (
        panel["reputation_delta"].notna() & (panel["reputation_delta"] <= DROP_THRESHOLD)
    ).astype(int)
    # events that affect NEXT round decisions
    panel = panel.sort_values(["agent_id", "round_number"])
    panel["bad_rep_prev"] = panel.groupby("agent_id")["bad_rep"].shift(1).fillna(0).astype(int)
    panel["rep_drop_prev"] = panel.groupby("agent_id")["rep_drop"].shift(1).fillna(0).astype(int)
    panel["gossip_prev"] = (
        panel.groupby("agent_id")["in_gossip_bulletin"].shift(1).fillna(0).astype(int)
    )
    panel["prop"] = panel["prop_of_wealth"].astype(float)
    panel["contribution"] = panel["contribution"].astype(float)
    return panel


def event_study(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """For each negative event at end of round t, compare contrib at t vs t+1..t+3."""
    event_rows = []
    for agent_id, g in panel.groupby("agent_id"):
        g = g.sort_values("round_number").set_index("round_number")
        for rn, row in g.iterrows():
            flags = []
            if row["bad_rep"]:
                flags.append("bad_rep")
            if row["rep_drop"]:
                flags.append("rep_drop")
            if row["in_gossip_bulletin"]:
                flags.append("gossip_target")
            if not flags:
                continue
            pre = float(row["prop"])
            pre_c = float(row["contribution"])
            for horizon, rounds_ahead in [("imm", [1]), ("short", [1, 2]), ("med", [1, 2, 3])]:
                props = []
                contribs = []
                for k in rounds_ahead:
                    if rn + k in g.index:
                        props.append(float(g.loc[rn + k, "prop"]))
                        contribs.append(float(g.loc[rn + k, "contribution"]))
                if not props:
                    continue
                event_rows.append(
                    {
                        "agent_id": agent_id,
                        "institution_choice": row["institution_choice"],
                        "agent_group": row["agent_group"],
                        "event_round": rn,
                        "event_types": "|".join(flags),
                        "reputation": row["reputation"],
                        "reputation_delta": row["reputation_delta"],
                        "horizon": horizon,
                        "prop_at_event": pre,
                        "prop_after_mean": float(np.mean(props)),
                        "delta_prop": float(np.mean(props) - pre),
                        "contrib_at_event": pre_c,
                        "contrib_after_mean": float(np.mean(contribs)),
                        "delta_contrib": float(np.mean(contribs) - pre_c),
                        "n_post_rounds": len(props),
                    }
                )
    events = pd.DataFrame(event_rows)
    events.to_csv(TABLES / "reputation_gossip_events.csv", index=False)

    # summary by type / institution / horizon
    summ = []
    for (etype_filter, label) in [
        ("bad_rep", "bad_rep"),
        ("rep_drop", "rep_drop"),
        ("gossip_target", "gossip_target"),
    ]:
        sub = events[events["event_types"].str.contains(etype_filter)]
        for (inst, horizon), gg in sub.groupby(["institution_choice", "horizon"]):
            # first-time vs repeat: for imm horizon only count unique event_rounds per agent
            summ.append(
                {
                    "event_family": label,
                    "institution_choice": inst,
                    "horizon": horizon,
                    "n_events": len(gg),
                    "n_agents": gg["agent_id"].nunique(),
                    "mean_delta_prop": gg["delta_prop"].mean(),
                    "median_delta_prop": gg["delta_prop"].median(),
                    "frac_delta_prop_positive": (gg["delta_prop"] > 0).mean(),
                    "mean_prop_at_event": gg["prop_at_event"].mean(),
                    "mean_prop_after": gg["prop_after_mean"].mean(),
                }
            )
    summary = pd.DataFrame(summ)
    summary.to_csv(TABLES / "reputation_gossip_event_summary.csv", index=False)

    # unaffected controls: same rounds, agents without event
    ctrl_rows = []
    for rn in sorted(panel["round_number"].unique()):
        if rn >= 30:
            continue
        day = panel[panel["round_number"] == rn]
        nxt = panel[panel["round_number"] == rn + 1][["agent_id", "prop"]].rename(
            columns={"prop": "prop_next"}
        )
        m = day.merge(nxt, on="agent_id")
        for flag, col in [
            ("bad_rep", "bad_rep"),
            ("gossip_target", "in_gossip_bulletin"),
            ("rep_drop", "rep_drop"),
        ]:
            affected = m[m[col] == 1]
            control = m[m[col] == 0]
            if affected.empty or control.empty:
                continue
            ctrl_rows.append(
                {
                    "round_number": rn,
                    "event_family": flag,
                    "n_affected": len(affected),
                    "n_control": len(control),
                    "affected_mean_delta": (affected["prop_next"] - affected["prop"]).mean(),
                    "control_mean_delta": (control["prop_next"] - control["prop"]).mean(),
                    "diff_in_diff": (affected["prop_next"] - affected["prop"]).mean()
                    - (control["prop_next"] - control["prop"]).mean(),
                }
            )
    ctrls = pd.DataFrame(ctrl_rows)
    ctrls.to_csv(TABLES / "reputation_gossip_controls.csv", index=False)

    # first vs repeat gossip appearances
    first_rep = []
    for agent_id, g in events[events["horizon"] == "imm"].groupby("agent_id"):
        g = g.sort_values("event_round")
        for et in ("gossip_target", "bad_rep", "rep_drop"):
            sub = g[g["event_types"].str.contains(et)]
            if sub.empty:
                continue
            first = sub.iloc[0]
            reps = sub.iloc[1:]
            first_rep.append(
                {
                    "agent_id": agent_id,
                    "institution_choice": first["institution_choice"],
                    "event_family": et,
                    "first_delta_prop": first["delta_prop"],
                    "repeat_mean_delta_prop": reps["delta_prop"].mean() if len(reps) else np.nan,
                    "n_repeat": len(reps),
                }
            )
    fr = pd.DataFrame(first_rep)
    fr.to_csv(TABLES / "reputation_first_vs_repeat.csv", index=False)
    return events, summary


def scan_reasoning(panel: pd.DataFrame) -> pd.DataFrame:
    rb = pd.read_csv(TABLES / "reasoning_blocks.csv")
    # focus contribution + belief around event-next rounds
    focus = rb[rb["kind"].isin(["contribution", "belief_strategy", "belief_observations", "punishment"])]
    rows = []
    # map agent-round event exposure (prev-round events)
    exp = panel[
        ["round_number", "agent_id", "bad_rep_prev", "rep_drop_prev", "gossip_prev", "prop", "contribution"]
    ]
    merged = focus.merge(exp, on=["round_number", "agent_id"], how="left")
    for _, r in merged.iterrows():
        text = str(r.get("text") or "")
        if not text:
            continue
        motifs = [name for name, pat in MOTIF_PATTERNS.items() if pat.search(text)]
        if not (r.get("bad_rep_prev") or r.get("rep_drop_prev") or r.get("gossip_prev") or motifs):
            # still keep a thin sample? skip non-event non-motif to reduce noise
            continue
        if not (r.get("bad_rep_prev") or r.get("rep_drop_prev") or r.get("gossip_prev")):
            # optional global motif census separately
            pass
        rows.append(
            {
                "evidence_id": r["evidence_id"],
                "round_number": r["round_number"],
                "agent_id": r["agent_id"],
                "institution_choice": r.get("institution_choice", ""),
                "kind": r["kind"],
                "bad_rep_prev": int(r.get("bad_rep_prev") or 0),
                "rep_drop_prev": int(r.get("rep_drop_prev") or 0),
                "gossip_prev": int(r.get("gossip_prev") or 0),
                "contribution": r.get("contribution"),
                "prop": r.get("prop"),
                "motifs": "|".join(motifs) if motifs else "",
                "text_excerpt": text[:400].replace("\n", " "),
                "source_path": r.get("source_path", ""),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "reputation_reasoning_motifs.csv", index=False)

    # motif rates among post-event contribution reasoning only
    post = out[(out["kind"] == "contribution") & ((out["bad_rep_prev"] == 1) | (out["gossip_prev"] == 1))]
    counts = Counter()
    for m in post["motifs"]:
        if not m:
            continue
        for part in str(m).split("|"):
            counts[part] += 1
    pd.DataFrame(
        [{"motif": k, "count_in_post_event_contribution_reasoning": v} for k, v in counts.most_common()]
    ).to_csv(TABLES / "reputation_motif_counts.csv", index=False)
    return out


def strategy_profiles(panel: pd.DataFrame, events: pd.DataFrame, motifs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for aid, g in panel.groupby("agent_id"):
        g = g.sort_values("round_number")
        inst = g["institution_choice"].iloc[0]
        group = g["agent_group"].iloc[0]
        ev = events[(events["agent_id"] == aid) & (events["horizon"] == "imm")]
        m = motifs[motifs["agent_id"] == aid]
        # baseline = rounds 1-4 mean prop
        base = g[g["round_number"] <= 4]["prop"].mean()
        late = g[g["round_number"] >= 20]["prop"].mean()
        # response to gossip
        g_ev = ev[ev["event_types"].str.contains("gossip_target")]
        b_ev = ev[ev["event_types"].str.contains("bad_rep")]
        # shock response from existing deltas if available
        try:
            shock = pd.read_csv(TABLES / "shock_agent_deltas.csv")
            sh = shock[shock["agent_id"] == aid]
            shock_note = "; ".join(
                f"R{int(r.shock_round)} Δ={r.delta_post_minus_pre:.3f}" for _, r in sh.iterrows()
            )
        except Exception:
            shock_note = ""
        # reasoning-action consistency: when contribution>0 is reasoning empty? already 0 globally
        # flag high prop variance
        rows.append(
            {
                "agent_id": aid,
                "agent_group": group,
                "institution_choice": inst,
                "mean_prop": g["prop"].mean(),
                "median_prop": g["prop"].median(),
                "std_prop": g["prop"].std(ddof=1),
                "zero_share": (g["contribution"] <= 0).mean(),
                "baseline_prop_r1_4": base,
                "late_prop_r20_30": late,
                "mean_reputation": g["reputation"].mean(),
                "min_reputation": g["reputation"].min(),
                "n_bad_rep_rounds": int(g["bad_rep"].sum()),
                "n_gossip_target_rounds": int(g["in_gossip_bulletin"].sum()),
                "mean_delta_prop_after_gossip": g_ev["delta_prop"].mean() if len(g_ev) else np.nan,
                "mean_delta_prop_after_bad_rep": b_ev["delta_prop"].mean() if len(b_ev) else np.nan,
                "top_motifs": "|".join(
                    [k for k, _ in Counter("|".join(m["motifs"].dropna()).split("|")).most_common(5) if k]
                ),
                "shock_deltas": shock_note,
                "adaptation_flag": int(abs((late or 0) - (base or 0)) > 0.15),
            }
        )
    profiles = pd.DataFrame(rows).sort_values("agent_id")
    profiles.to_csv(TABLES / "agent_strategy_profiles.csv", index=False)
    return profiles


def consistency_table(panel: pd.DataFrame, motifs: pd.DataFrame) -> pd.DataFrame:
    rb = pd.read_csv(TABLES / "reasoning_blocks.csv")
    contrib_r = rb[rb["kind"] == "contribution"][
        ["round_number", "agent_id", "text", "evidence_id"]
    ].rename(columns={"text": "contribution_reasoning"})
    m = panel.merge(contrib_r, on=["round_number", "agent_id"], how="left")
    rows = []
    for _, r in m.iterrows():
        text = str(r.get("contribution_reasoning") or "").strip()
        c = float(r["contribution"])
        flags = []
        if c > 0 and not text:
            flags.append("action_without_reasoning")
        if c == 0 and re.search(r"cooperat|contribute|support the", text, re.I):
            flags.append("cooperative_language_zero_contrib")
        if c > 0 and re.search(r"free[- ]rid|not contribute|zero", text, re.I):
            flags.append("free_ride_language_positive_contrib")
        # reputation language after gossip without prop increase
        if r.get("gossip_prev") == 1 and re.search(r"reputat|trust", text, re.I):
            flags.append("mentions_reputation_after_gossip")
        if not flags:
            continue
        rows.append(
            {
                "round_number": r["round_number"],
                "agent_id": r["agent_id"],
                "institution_choice": r["institution_choice"],
                "contribution": c,
                "prop": r["prop"],
                "gossip_prev": r.get("gossip_prev"),
                "bad_rep_prev": r.get("bad_rep_prev"),
                "flags": "|".join(flags),
                "evidence_id": r.get("evidence_id", ""),
                "excerpt": text[:300],
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "reasoning_action_flags.csv", index=False)
    return out


def plots(panel: pd.DataFrame, events: pd.DataFrame, gossip_df: pd.DataFrame):
    PLOTS.mkdir(parents=True, exist_ok=True)
    # reputation trajectories
    fig, ax = plt.subplots(figsize=(10, 5))
    for inst, color in [("SI", "#5B4B8A"), ("SFI", "#C47B2C")]:
        sub = panel[panel["institution_choice"] == inst]
        mean = sub.groupby("round_number")["reputation"].mean()
        ax.plot(mean.index, mean.values, label=inst, color=color, lw=2)
    ax.axhline(NEUTRAL_REP, color="#888", ls=":", label="neutral default 5")
    ax.axhline(BAD_REP_THRESHOLD, color="#AA2222", ls="--", label=f"bad threshold {BAD_REP_THRESHOLD}")
    ax.set_xlabel("Round")
    ax.set_ylabel("Mean reputation")
    ax.set_title("Mean reputation by institution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "reputation_mean_trajectories.png", dpi=150)
    plt.close(fig)

    # gossip target frequency
    freq = gossip_df.groupby(["round_number", "target"]).size().reset_index(name="n")
    top_targets = gossip_df["target"].value_counts().head(10)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([str(i) for i in top_targets.index], top_targets.values, color="#666")
    ax.set_xlabel("Agent id")
    ax.set_ylabel("Bulletin appearances (reconstructed)")
    ax.set_title("Most frequent reconstructed gossip targets")
    fig.tight_layout()
    fig.savefig(PLOTS / "gossip_target_frequency.png", dpi=150)
    plt.close(fig)

    # event deltas
    imm = events[events["horizon"] == "imm"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ax, fam in zip(axes, ["bad_rep", "rep_drop", "gossip_target"]):
        sub = imm[imm["event_types"].str.contains(fam)]
        data = [
            sub.loc[sub["institution_choice"] == "SI", "delta_prop"].dropna(),
            sub.loc[sub["institution_choice"] == "SFI", "delta_prop"].dropna(),
        ]
        ax.boxplot(data, tick_labels=["SI", "SFI"])
        ax.axhline(0, color="#888", lw=1)
        ax.set_title(fam)
        ax.set_ylabel("Δ prop (t+1 − t)")
    fig.suptitle("Immediate prop change after negative social events")
    fig.tight_layout()
    fig.savefig(PLOTS / "reputation_event_deltas.png", dpi=150)
    plt.close(fig)


def write_evidence_excerpts(motifs: pd.DataFrame):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    # select post-event contribution excerpts with motifs
    sub = motifs[
        (motifs["kind"] == "contribution")
        & ((motifs["bad_rep_prev"] == 1) | (motifs["gossip_prev"] == 1))
    ].head(40)
    lines = [
        "# Reputation / Gossip Reasoning Excerpts",
        "",
        "Verbatim excerpts from contribution reasoning in rounds after a bad-reputation",
        "or reconstructed-gossip-target event (previous round).",
        "",
        f"Event definitions: bad_rep = reputation < {BAD_REP_THRESHOLD}; "
        f"gossip_target = appeared in reconstructed top-{MAX_GOSSIP} bulletin "
        f"(ToM score ≤ {GOSSIP_TRIGGER}).",
        "",
    ]
    for _, r in sub.iterrows():
        lines.append(f"### {r['evidence_id']}")
        lines.append("")
        lines.append(
            f"[Evidence: {SOURCE_REL} | run={RUN} | round={int(r['round_number'])} | "
            f"agent={int(r['agent_id'])} | record={r['source_path']}]"
        )
        lines.append("")
        lines.append(
            f"- institution: `{r['institution_choice']}` | contribution: `{r['contribution']}` | "
            f"prop: `{r['prop']}` | bad_rep_prev={r['bad_rep_prev']} gossip_prev={r['gossip_prev']}"
        )
        lines.append(f"- motifs: `{r['motifs']}`")
        lines.append("")
        lines.append(f"> {r['text_excerpt']}")
        lines.append("")
    (EVIDENCE / "reputation_gossip_reasoning_excerpts.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> int:
    rounds = load_raw()
    gossip_df = reconstruct_gossip(rounds)
    gossip_df.to_csv(TABLES / "gossip_bulletins_reconstructed.csv", index=False)
    panel = build_panel(rounds, gossip_df)
    panel.to_csv(TABLES / "reputation_gossip_panel.csv", index=False)
    events, summary = event_study(panel)
    motifs = scan_reasoning(panel)
    profiles = strategy_profiles(panel, events, motifs)
    flags = consistency_table(panel, motifs)
    plots(panel, events, gossip_df)
    write_evidence_excerpts(motifs)

    numeric = {
        "bad_rep_threshold": BAD_REP_THRESHOLD,
        "drop_threshold": DROP_THRESHOLD,
        "gossip_trigger": GOSSIP_TRIGGER,
        "max_gossip_items": MAX_GOSSIP,
        "n_gossip_rows": len(gossip_df),
        "n_bad_rep_agent_rounds": int(panel["bad_rep"].sum()),
        "n_gossip_target_agent_rounds": int(panel["in_gossip_bulletin"].sum()),
        "event_summary_head": summary.to_dict(orient="records"),
        "n_reasoning_action_flags": len(flags),
        "n_profiles": len(profiles),
    }
    with open(TABLES / "prompt4_numeric_summary.json", "w", encoding="utf-8") as f:
        json.dump(numeric, f, indent=2)
    print("Prompt 4 done")
    print("bad_rep rounds", numeric["n_bad_rep_agent_rounds"])
    print("gossip target rounds", numeric["n_gossip_target_agent_rounds"])
    print(summary[summary.horizon == "imm"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
