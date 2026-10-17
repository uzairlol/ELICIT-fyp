# Kaggle run order

25 notebooks, each one preconfigured. Upload a notebook, turn the **GPU** toggle
on, press **Run All**, download the `.tar.gz` it leaves at the bottom, move to the
next one. Nothing to edit.

Regenerate the notebooks with `python scripts/make_kaggle_notebooks.py` (the
generator reads the grid manifests, so the table below cannot drift from the
grids without the notebooks being wrong in the same commit).

## The order

| # | Notebook | Arm | Model | Runs | ~Hours |
|---|----------|-----|-------|-----:|-------:|
| 01 | `01-arm-a-qwen2.5-14b-part1.ipynb` | A | Qwen2.5-14B | 6 | 8.4 |
| 02 | `02-arm-a-qwen2.5-14b-part2.ipynb` | A | Qwen2.5-14B | 6 | 8.4 |
| 03 | `03-arm-a-llama-3.1-8b-part1.ipynb` | A | Llama-3.1-8B | 6 | 8.4 |
| 04 | `04-arm-a-llama-3.1-8b-part2.ipynb` | A | Llama-3.1-8B | 6 | 8.4 |
| 05 | `05-arm-a-mistral-7b-part1.ipynb` | A | Mistral-7B | 6 | 8.4 |
| 06 | `06-arm-a-mistral-7b-part2.ipynb` | A | Mistral-7B | 6 | 8.4 |
| 07 | `07-arm-d-qwen2.5-14b-part1.ipynb` | D | Qwen2.5-14B | 6 | 8.4 |
| 08 | `08-arm-d-qwen2.5-14b-part2.ipynb` | D | Qwen2.5-14B | 6 | 8.4 |
| 09 | `09-arm-d-llama-3.1-8b-part1.ipynb` | D | Llama-3.1-8B | 5 | 7.1 |
| 10 | `10-arm-d-llama-3.1-8b-part2.ipynb` | D | Llama-3.1-8B | 4 | 5.8 |
| 11 | `11-arm-d-mistral-7b-part1.ipynb` | D | Mistral-7B | 5 | 7.1 |
| 12 | `12-arm-d-mistral-7b-part2.ipynb` | D | Mistral-7B | 4 | 5.8 |
| 13 | `13-arm-b-qwen2.5-14b-part1.ipynb` | B | Qwen2.5-14B | 6 | 8.4 |
| 14 | `14-arm-b-qwen2.5-14b-part2.ipynb` | B | Qwen2.5-14B | 5 | 7.1 |
| 15 | `15-arm-b-qwen2.5-14b-part3.ipynb` | B | Qwen2.5-14B | 5 | 7.1 |
| 16 | `16-arm-b-llama-3.1-8b-part1.ipynb` | B | Llama-3.1-8B | 6 | 8.4 |
| 17 | `17-arm-b-llama-3.1-8b-part2.ipynb` | B | Llama-3.1-8B | 5 | 7.1 |
| 18 | `18-arm-b-llama-3.1-8b-part3.ipynb` | B | Llama-3.1-8B | 5 | 7.1 |
| 19 | `19-arm-c-qwen2.5-14b-part1.ipynb` | C | Qwen2.5-14B | 11 | 8.3 |
| 20 | `20-arm-c-qwen2.5-14b-part2.ipynb` | C | Qwen2.5-14B | 11 | 8.3 |
| 21 | `21-arm-c-qwen2.5-14b-part3.ipynb` | C | Qwen2.5-14B | 10 | 7.6 |
| 22 | `22-arm-c-llama-3.1-8b-part1.ipynb` | C | Llama-3.1-8B | 11 | 8.3 |
| 23 | `23-arm-c-llama-3.1-8b-part2.ipynb` | C | Llama-3.1-8B | 11 | 8.3 |
| 24 | `24-arm-c-llama-3.1-8b-part3.ipynb` | C | Llama-3.1-8B | 10 | 7.6 |
| 25 | `25-arm-e-qwen2.5-14b.ipynb` | E | Qwen2.5-14B | 2 | 8.6 |

164 runs, ~180 h of simulation, ~15 h of that setup overhead.

## Why it is split this way

Kaggle caps a GPU session at 12 hours, and **Save & Run All always begins from a
completely clean session** — it cannot resume a previous run, so nothing a
notebook wrote survives into the next attempt. Every notebook therefore has to
finish in one go. The splits fall where they do because of the per-cell cost:

| Shape | Cost per run | Notes |
|-------|-------------:|-------|
| n=26, ToM off | ~1.3 h | Arms A, B, D |
| n=14, ToM off | ~0.7 h | Arm C; the quadratic term halves |
| n=26, ToM on | ~4.0 h | Arm E, scheduled last |

Those figures are wall-clock per run with the democracy loops already
parallelised (`src/modules/democracy_module.py:247`). The strategy document's
5.5 h/run is a ToM-*on* measurement taken before that optimisation. The estimates
are rounded up on purpose: over-estimating costs a little slack, under-estimating
costs a session that Kaggle kills mid-run and cannot be resumed.

## When it goes wrong

The notebooks are honest about failure rather than silently continuing:

- **Preflight fails** on something other than `llm_reachable` → the notebook
  stops before spending quota. Arm D is expected to run at G1/G2/G3/G3c, so the
  governance check is arm-aware and does not fire there.
- **A run fails** → it is recorded and reported; the remaining runs continue, and
  the summary at the end says how many succeeded.
- **The session times out anyway** → re-running repeats the finished runs. That
  wastes quota but cannot corrupt anything; each run is independent and writes its
  own result file.

## If you run short of quota

Stop after notebook 06. That is Arm A complete across all three models, which is
the publishable core: 36 runs, ~86 GPU-h. Everything from 07 onward is stretch.