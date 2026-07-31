# 34 — Wealth Gini, Cooperation Rate, and Wealth Gap (20260731)

Dashboard macro dimensions under-used in earlier prompts. Data: `tables/dashboard_macro_series.csv`; plots `gini_wealth_cooperation_rate.png`, `gini_contribution_vs_wealth.png`, `wealth_gap_developed_developing.png`.

---

## Opening claim

Stored `cooperation_rate` and analyst `prop_of_wealth` both show an R2 spike and later volatility, but **wealth inequality does not converge away**: after an early dip, `gini_wealth` rises again, and the developed–developing mean wealth gap **widens by nearly two orders of magnitude**. LDF transfers in this run do not equalise wealth stocks.

---

## Trajectories

| Round | gini_wealth | cooperation_rate | wealth_gap (dev−dvg) | gini(abs contrib) | gini(prop) |
|------:|------------:|-----------------:|---------------------:|------------------:|-----------:|
| 1 | 0.709 | 0.231 | 4.56e6 | 0.857 | 0.861 |
| 2 | 0.601 | 0.445 | 5.78e6 | 0.852 | 0.886 |
| 6 | 0.585 | 0.277 | 8.98e6 | 0.792 | 0.855 |
| 15 | 0.556 | 0.310 | 4.84e7 | 0.585 | 0.472 |
| 30 | 0.653 | 0.258 | 2.15e8 | 0.603 | 0.831 |

[Evidence: `tables/dashboard_macro_series.csv` | run=20260731_013853 | round=1,2,6,15,30 | agent=n/a | record=macro]

**Reasoning why the gap widens:** SI (developed) agents contribute large *absolute* amounts into a public good with multiplier 1.6 and retain large wealth bases; developing/SFI agents have tiny endowments. LDF payouts at shocks are O(10^5) while SI wealth stocks become O(10^8). Even perfect coverage of developing damage cannot close that stock gap.

---

## Contribution Gini vs wealth Gini (RQ 8)

Absolute contribution Gini stays high (~0.6–0.85). Prop Gini is volatile and ends high (0.83). Wealth Gini is U-shaped (0.71→~0.55→0.65). **Effort inequality and wealth inequality move differently** — proportional metric does not deliver equalisation of wealth.

---

## Limits

`cooperation_rate` formula is whatever the simulation stored (not re-derived). Single seed. Confidence high on gap widening as arithmetic fact; medium on welfare interpretation.
