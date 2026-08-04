# 03 — Extraction Pipeline (20260804)

## Command

From repository root:

```bash
python "docs/raw documentation/20260804/scripts/extract_20260804_results.py"
```

Then analysis scripts under `scripts/analyze_20260804_*.py`, then:

```bash
python "docs/raw documentation/20260804/scripts/cross_seed_comparison.py"
```

## Guarantees

- Original JSON is never modified.
- Tables are deterministic given the locked SHA256 `9CE44CE613698436DE86940E8042D0A9EF6BA4030B13E67C02544F9EA00C5A6E`.
- Extraction logged 86 non-fatal issues (see `tables/extraction_issues.csv`) — mostly missing optional fields or reconstruction notes, not schema breaks.

## Outputs

| Destination | Contents |
|-------------|----------|
| `tables/` | CSV + JSON numeric summaries |
| `evidence/` | Traceable excerpts / ID maps |
| `plots/` | Seed2 figures |
| `plots/cross_seed/` | Comparative figures |

[Evidence: `tables/extraction_issues.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=pipeline]
