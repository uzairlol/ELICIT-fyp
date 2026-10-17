"""Generate the pre-configured Kaggle notebooks, one per (arm x model x chunk).

Each notebook is a single session's worth of work with everything hardcoded, so
the user never edits a file. Ordering is embedded in the filenames (01-, 02-, ...)
which is also the run order.

Regenerate with:

    python scripts/make_kaggle_notebooks.py

Substitution note: cells contain real Python f-strings, so they are parameterised
with `__TOKEN__` markers and a plain str.replace. Using str.format() here would
require doubling every brace in every f-string in the file, which is how the
first version of this generator emitted literal `{{ARM}}` into the run cell.

Session sizing. Kaggle caps a GPU session at 12 h, and "Save & Run All" starts a
*completely clean* session, so a notebook cannot resume from a previous run -
whatever it wrote is gone. Each workload is therefore split into as many
notebooks as it takes for every one of them to finish inside a single session,
and the per-cell cost figures below are what decide where the splits fall.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

NOTEBOOK_DIR = Path("src/kaggle")

# (order, arm, model, grid manifest, runtime budget hours, title, why)
# ------------------------------------------------------------------
# Session plan
# ------------------------------------------------------------------
# Kaggle facts this is built around:
#   * a GPU session is capped at 12 h wall-clock;
#   * "Save & Run All" starts a COMPLETELY CLEAN session, so a notebook cannot
#     resume from a previous run - whatever it wrote is gone.
# Therefore every notebook must finish inside one session, and the unit of work
# is (arm, model, chunk-of-cells) rather than (arm, model).
#
# Per-cell wall-clock estimates, keyed by (agents, ToM on/off). The strategy doc's
# 5.5 h/run is a ToM-ON measurement taken with the democracy loops serial. These
# grids are ToM-off with democracy parallelised (democracy_module.py:247,421),
# which the doc prices at ~1.0-1.2 h/run at n=26; n=14 halves the quadratic term.
# Deliberately rounded up: over-estimating costs a little slack, under-estimating
# costs a truncated session that Kaggle will not let us resume.
PER_CELL_HOURS = {
    (26, False): 1.3,
    (14, False): 0.7,
    (26, True): 4.0,  # the ToM control, deliberately scheduled last
}
SETUP_HOURS = 0.6  # pip install vllm, weight download, engine load
SAFETY_HOURS = 1.5  # the per-cell figure is an estimate; leave real slack
SESSION_CAP = 12.0

# (arm, model, grid manifest, title, why-it-matters)
WORKLOADS = [
    (
        "A",
        "qwen2.5-14b",
        "configs/grid_arm_a.yaml",
        "Arm A (prompt robustness) - Qwen2.5-14B",
        "**Start here.** Arm A is the paper: the same simulation run under three "
        "prompt wordings on one model, to see whether the answer survives being "
        "reworded. Run every Arm A notebook before anything else - one model "
        "cannot tell you whether a result is about the institution or the model.",
    ),
    (
        "A",
        "llama-3.1-8b",
        "configs/grid_arm_a.yaml",
        "Arm A (prompt robustness) - Llama-3.1-8B",
        "Same three wordings on a second model family. Llama and Qwen behave very "
        "differently on this prompt, and that difference is the point.",
    ),
    (
        "A",
        "mistral-7b",
        "configs/grid_arm_a.yaml",
        "Arm A (prompt robustness) - Mistral-7B",
        "Third model, third training lineage. With all three done you can say how "
        "much of your result is the model rather than the institution.",
    ),
    (
        "D",
        "qwen2.5-14b",
        "configs/grid_arm_d.yaml",
        "Arm D (governance) - Qwen2.5-14B",
        "The part that makes this repository's name true: the agents choose the "
        "Loss and Damage Fund payout rule themselves. Arm A is its baseline, so "
        "do not skip it.",
    ),
    (
        "D",
        "llama-3.1-8b",
        "configs/grid_arm_d.yaml",
        "Arm D (governance) - Llama-3.1-8B",
        "The same governance levels on a second family, to check whether the "
        "elected rule is model-dependent.",
    ),
    (
        "D",
        "mistral-7b",
        "configs/grid_arm_d.yaml",
        "Arm D (governance) - Mistral-7B",
        "Third family for the governance arm.",
    ),
    (
        "B",
        "qwen2.5-14b",
        "configs/grid_arm_ab.yaml",
        "Arm B (controls) - Qwen2.5-14B",
        "The control arm: the same model with the fund off, the shocks off, and "
        "enforcement off. This is what turns 'we observed X' into 'X happens "
        "because of the fund'. Largest credibility gain in the plan.",
    ),
    (
        "B",
        "llama-3.1-8b",
        "configs/grid_arm_ab.yaml",
        "Arm B (controls) - Llama-3.1-8B",
        "The same four controls on the second family.",
    ),
    (
        "C",
        "qwen2.5-14b",
        "configs/grid_arm_c.yaml",
        "Arm C (payoff sweep) - Qwen2.5-14B",
        "Sweeps the payoff multiplier so the return to contributing crosses 1.0 - "
        "where cooperation stops being irrational. Tests whether the agents "
        "respond to payoffs at all.",
    ),
    (
        "C",
        "llama-3.1-8b",
        "configs/grid_arm_c.yaml",
        "Arm C (payoff sweep) - Llama-3.1-8B",
        "The same sweep on the second family, so the threshold is checked twice.",
    ),
    (
        "E",
        "qwen2.5-14b",
        "configs/grid_full.yaml",
        "Arm E (Theory-of-Mind control) - Qwen2.5-14B",
        "Optional and last. Turns the social-information layer back on so you can "
        "say the audit's conclusions hold without it. First thing to cut if you "
        "run short of quota.",
    ),
]

MD_INTRO = """\
# {title}

**Run this notebook as-is. Do not edit anything.**

{why}

## What to do

1. Open it in Kaggle with the **GPU** toggle on, then **Run All**.
2. Wait for the last cell. It ends with a line reading `ALL CELLS COMPLETE`.
   That is the only signal that matters - if the notebook stopped early, read the
   message it printed and re-run it, but see the note below.
3. The last cell leaves one file, `elicit_results_{slug}.tar.gz`. Click it to
   download, and keep it.
4. Run notebook **{next_label}** next.

## About the time budget

This notebook is sized for **one Kaggle session** ({cells} runs, about
{run_hours:.1f} h of simulation, plus ~{setup_hours:.1f} h of setup).

Kaggle stops a GPU session at 12 hours, and **Save & Run All always starts from
a clean session** - it cannot pick up where a previous run stopped. So each
notebook is deliberately sized to finish in one go rather than relying on
resuming. If a run is slower than estimated and the notebook stops early,
re-running it repeats the cells it already finished; that is wasted quota, not
data corruption, and the notebooks are split conservatively to make it unlikely.
"""

CONFIG = """\
# ============================================================================
# Configuration - already set. Running this notebook as-is is the whole procedure.
# ============================================================================
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SERVED_MODEL = "__MODEL__"
ARM = "__ARM__"
GRID = "__GRID__"
CELLS = __CELLS__
CHUNK_START = __CHUNK_START__
PER_CELL_HOURS = __PER_CELL__
RUNTIME_BUDGET_S = int(__BUDGET__ * 3600)
SETUP_ALLOWANCE_S = int(__SETUP__ * 3600)

REPO = "https://github.com/uzairlol/ELICIT-fyp.git"
REPO_DIR = Path("/kaggle/working/elicit")

print(f"arm           : {ARM}")
print(f"served model  : {SERVED_MODEL}")
print(f"grid manifest : {GRID}")
print(f"this notebook : {CELLS} runs of arm {ARM} on {SERVED_MODEL}")
print(f"estimate      : ~{CELLS * PER_CELL_HOURS:.1f} h of simulation")
print(f"hard stop     : {RUNTIME_BUDGET_S / 3600:.1f} h (Kaggle's cap is 12 h)")
print(f"session start : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
"""

CLONE = """\
# ============================================================================
# Clone the repo and install its Python dependencies
# ============================================================================
if not REPO_DIR.exists():
    !git clone -q {REPO} {REPO_DIR}
else:
    !git -C {REPO_DIR} pull --ff-only

os.chdir(REPO_DIR)
sys.path.insert(0, str(REPO_DIR / "src"))

print("environment:")
!python --version
!free -h | head -2
!df -h /kaggle | tail -1
!nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

!pip install -qq -r requirements.txt
!pip install -qq -e . --no-deps
print("dependencies installed.")
"""

VLLM = """\
# ============================================================================
# Install vLLM into an isolated venv
# ============================================================================
# Kaggle's base image ships RAPIDS and protobuf 6.x, and a plain `pip install vllm`
# walks into broken dependency resolution there. An isolated venv keeps vLLM's
# resolver clean and leaves the base environment (which the simulation imports
# from) untouched; the two only talk to each other over HTTP.
VENV = "/kaggle/working/vllm-env"

!apt-get update -y -qq > /dev/null && apt-get install -y -qq pciutils zstd > /dev/null

if not Path(VENV).exists():
    !python -m pip install -q --upgrade pip virtualenv
    !python -m virtualenv {VENV}

!env -u PYTHONPATH -u PYTHONHOME {VENV}/bin/pip install -q --upgrade pip
print("installing vLLM (large CUDA torch wheel, several minutes) ...")
!env -u PYTHONPATH -u PYTHONHOME {VENV}/bin/pip install -q vllm huggingface_hub

!env -u PYTHONPATH -u PYTHONHOME {VENV}/bin/python -c "import vllm, torch; print('  vllm', vllm.__version__, '| cuda', torch.cuda.is_available(), '| gpus', torch.cuda.device_count())"
"""

SERVE = """\
# ============================================================================
# Start the vLLM server for this session's model
# ============================================================================
# The flags are held identical across all three families (tensor-parallel 2,
# max-model-len 8192, max-num-seqs 32). Only the checkpoint differs between
# notebooks. If the serving configuration differed between families, "which
# model produced this result" would be unanswerable.
VLLM_LOG = "/kaggle/working/vllm.log"
os.environ["HF_HOME"] = "/kaggle/working/hf_cache"
os.makedirs(os.environ["HF_HOME"], exist_ok=True)

serve_cmd = ["bash", "scripts/serve_arm_model.sh", SERVED_MODEL]
print("starting:", " ".join(serve_cmd), flush=True)

with open(VLLM_LOG, "w", encoding="utf-8") as handle:
    process = subprocess.Popen(
        serve_cmd,
        stdout=handle,
        stderr=subprocess.STDOUT,
        env={**os.environ, "VLLM_BIN": f"{VENV}/bin/vllm"},
    )
print(f"server pid {process.pid}; log -> {VLLM_LOG}")
print("downloading weights and loading the engine, up to ~30 min ...", flush=True)

deadline = time.time() + 45 * 60
ready = False
while time.time() < deadline:
    if process.poll() is not None:
        print("server exited early; log tail:")
        !tail -40 {VLLM_LOG}
        raise SystemExit("vLLM failed to start")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=5) as response:
            names = [m.get("id") for m in json.loads(response.read()).get("data", [])]
        if SERVED_MODEL in names:
            ready = True
            break
    except Exception:
        pass
    time.sleep(10)

if not ready:
    !tail -60 {VLLM_LOG}
    raise SystemExit(f"server did not come up as {SERVED_MODEL}")
print("server ready.")
!tail -4 {VLLM_LOG}
"""

SMOKE = """\
# ============================================================================
# Smoke test - one real request before spending quota
# ============================================================================
# Cheap insurance. If the endpoint or the chat path is broken, find out in
# seconds rather than after the first hour-long run.
body = json.dumps(
    {
        "model": SERVED_MODEL,
        "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
        "max_tokens": 8,
        "temperature": 0.0,
    }
).encode("utf-8")
request = urllib.request.Request(
    "http://127.0.0.1:8000/v1/chat/completions",
    data=body,
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=120) as response:
    reply = json.loads(response.read())
print("server responds:", repr(reply["choices"][0]["message"]["content"].strip()))
"""

PLAN = '''\
# ============================================================================
# Work out which cells this session is responsible for
# ============================================================================
from cli import main as cli_main


def elicit(*args):
    """Run the CLI in-process and parse its JSON output."""
    buffer = sys.stdout
    captured = io.StringIO()
    sys.stdout = captured
    try:
        code = cli_main(list(args))
    finally:
        sys.stdout = buffer
    text = captured.getvalue()
    try:
        return code, json.loads(text)
    except ValueError:
        return code, {"raw": text}


_code, plan = elicit("grid", "show", "--grid", GRID, "--arm", ARM)

# This notebook owns a chunk of one model's cells for one arm. Cells for the
# other two families belong to their own notebooks, because a Kaggle session only
# ever loads one model, and the cells are chunked so that one notebook fits one
# session (a Kaggle re-run starts clean, so nothing can be resumed).
all_mine = [c for c in plan.get("cells_preview", []) if c.get("model") == SERVED_MODEL]
mine = all_mine[CHUNK_START : CHUNK_START + CELLS]

print(f"arm {ARM} grid: {plan['cells']} cells total, {len(all_mine)} for {SERVED_MODEL}")
print(
    f"this notebook runs chunk {CHUNK_START // CELLS + 1}: "
    f"cells {CHUNK_START}..{CHUNK_START + len(mine) - 1}"
)
print()
for cell in mine:
    print(
        f"  {cell['name']:<30} preset={cell['preset']!s:<18} "
        f"seed={cell['seed_index']} prompt={cell['prompt_variant']!s:<18} "
        f"gov={cell['governance']!s:<10} beta={cell['beta']}"
    )

if len(mine) != CELLS:
    raise SystemExit(
        f"Expected {CELLS} cells in this chunk but the grid returned {len(mine)}. "
        "The grid manifest changed; regenerate the notebooks."
    )
if any(c.get("preset") is None or c.get("seed_index") is None for c in mine):
    raise SystemExit("A cell is missing preset/seed_index, so it cannot be run.")

if plan.get("parity_violations"):
    raise SystemExit(
        "PARITY VIOLATIONS - refusing to spend GPU-hours:\\n"
        + json.dumps(plan["parity_violations"], indent=2)
    )
print("\\nparity check passed.")
'''

DOCTOR = """\
# ============================================================================
# Preflight
# ============================================================================
# Each check corresponds to a way a run can silently become the wrong experiment:
#   governance_matches_cell          the cell runs at a governance level it did not ask for
#   chat_template_fixed_for_parity  the same prompt is a different string per model
#   seed_vector_complete            "four seeds" may actually be one draw
#   shocks_decoupled_from_democracy shock response == rule-change response
#   served_model_name_matches       the whole arm gets relabelled
#
# The cell is passed to `doctor` explicitly. Without it, doctor would describe the
# module defaults, which carry no seed vector and a server-side chat template, and
# would report two failures that say nothing about the run that is about to start.
first = mine[0]
_code, findings = elicit(
    "doctor",
    "--model",
    SERVED_MODEL,
    "--preset",
    str(first["preset"]),
    "--seed-index",
    str(first["seed_index"]),
)
print(json.dumps(findings, indent=2))

if findings.get("ok"):
    print(f"\\npreflight passed for {first['name']}.")
else:
    failed = [f["check"] for f in findings["findings"] if not f["ok"]]
    print(f"\\nfailing checks: {', '.join(failed)}")
    if failed == ["llm_reachable"]:
        print("The server may still be loading. Re-run this cell in a minute or two.")
    else:
        raise SystemExit(
            "Preflight failed on something other than server reachability. "
            "Stop here - running anyway would spend quota on the wrong experiment."
        )
"""

RUN = """\
# ============================================================================
# Run this notebook's cells
# ============================================================================
# `mine` is this notebook's slice of the arm, in grid order. `cell["preset"]` and
# `cell["seed_index"]` are the coordinates `elicit run` needs; the cell *name* is
# not parseable back into them (arm_a_p0_qwen_s1 is preset a_qwen_p0, seed 1).
started = time.time()
completed, failed = [], []

for index, cell in enumerate(mine, start=1):
    elapsed = time.time() - started
    projected = elapsed + (len(mine) - index + 1) * PER_CELL_HOURS * 3600
    print("\\n" + "=" * 72)
    print(
        f"[{index}/{len(mine)}] {cell['name']}  preset={cell['preset']} seed={cell['seed_index']}"
    )
    print(
        f"elapsed {elapsed / 3600:.2f} h | projected finish "
        f"{(projected + SETUP_ALLOWANCE_S) / 3600:.1f} h into the session"
    )
    print("=" * 72, flush=True)

    cell_started = time.time()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli",
            "run",
            "--preset",
            str(cell["preset"]),
            "--seed-index",
            str(cell["seed_index"]),
        ],
        cwd=str(REPO_DIR),
        env={**os.environ, "PYTHONPATH": str(REPO_DIR / "src")},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        failed.append({"cell": cell["name"], "error": result.stderr[-2000:]})
        print(f"FAILED {cell['name']}:\\n{result.stderr[-2000:]}")
        continue

    completed.append(cell["name"])
    took = (time.time() - cell_started) / 3600
    print(f"DONE {cell['name']} in {took:.2f} h")

elapsed_h = (time.time() - started) / 3600
print("\\n" + "=" * 72)
print(
    json.dumps(
        {
            "arm": ARM,
            "served_model": SERVED_MODEL,
            "cells_planned": len(mine),
            "completed": completed,
            "failed": failed,
            "simulated_hours": round(elapsed_h, 2),
            "session_hours_including_setup": round(elapsed_h + SETUP_ALLOWANCE_S / 3600, 2),
            "kaggle_cap_hours": 12.0,
        },
        indent=2,
    )
)

if not failed and len(completed) == len(mine):
    print("\\n" + "=" * 72)
    print(f"ALL {len(mine)} CELLS COMPLETE.")
    print("Download the archive below, then run the next numbered notebook.")
else:
    print("\\n" + "=" * 72)
    print(f"{len(completed)} of {len(mine)} cells succeeded; {len(failed)} failed.")
    print("A Kaggle session cannot be resumed, so re-running repeats finished cells.")
    print("Read the failure above before re-running - a failed cell will fail again.")
"""

ARCHIVE = """\
# ============================================================================
# Package the results - this is the deliverable
# ============================================================================
# Named with the arm, model and part so several sessions' outputs stay
# distinguishable when you extract them all into results/.
slug = (ARM + "_" + SERVED_MODEL + "__PART__").replace(".", "").replace("-", "_")
slug = slug.replace("__part", "part").rstrip("_")
archive = Path("/kaggle/working/elicit_results_" + slug + ".tar.gz")
if archive.exists():
    archive.unlink()

!cd {REPO_DIR} && tar -czf {archive} results/

print("archive:")
!ls -lh {archive}
print("\\nresult files produced:")
!ls -1 {REPO_DIR}/results/simulation_*.json 2>/dev/null | wc -l

from IPython.display import FileLink  # noqa: E402

display(FileLink(str(archive)))
print("\\nDownload elicit_results_" + slug + ".tar.gz above, then run the next notebook.")
"""


def substitute(
    text: str,
    *,
    model: str,
    arm: str,
    grid: str,
    cells: int,
    chunk_start: int,
    per_cell: float,
    budget: float,
    part: str,
) -> str:
    """Token substitution that leaves every Python brace untouched."""
    return (
        text.replace("__MODEL__", model)
        .replace("__ARM__", arm)
        .replace("__GRID__", grid)
        .replace("__CELLS__", str(cells))
        .replace("__CHUNK_START__", str(chunk_start))
        .replace("__PER_CELL__", str(per_cell))
        .replace("__BUDGET__", str(budget))
        .replace("__SETUP__", str(SETUP_HOURS))
        .replace("__PART__", part)
    )


def slug_for(arm: str, model: str, part: str) -> str:
    """Archive slug, matching the one the ARCHIVE cell builds at run time."""
    return (
        (f"{arm}_{model}__{part}")
        .replace(".", "")
        .replace("-", "_")
        .replace("__part", "part")
        .rstrip("_")
    )


def split_source(body: str) -> list[str]:
    """nbformat source lines, without a trailing newline on the last one.

    `ruff format` owns .ipynb files in this repo and normalises the final line of
    each cell to have no trailing newline, so emitting one here would make
    `ruff format --check` fail on all 25 notebooks.
    """
    lines = body.splitlines()
    return [line + "\n" for line in lines[:-1]] + lines[-1:]


def markdown(
    title: str, why: str, slug: str, *, cells: int, run_hours: float, next_label: str
) -> dict:
    body = MD_INTRO.format(
        title=title,
        why=why,
        slug=slug,
        cells=cells,
        run_hours=run_hours,
        setup_hours=SETUP_HOURS,
        next_label=next_label,
    )
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": split_source(body),
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": split_source(source),
    }


def build(
    *,
    model: str,
    arm: str,
    grid: str,
    cells: int,
    chunk_start: int,
    per_cell: float,
    budget: float,
    title: str,
    why: str,
    next_label: str,
    part: str,
) -> dict:
    slug = slug_for(arm, model, part)
    tokens = {
        "model": model,
        "arm": arm,
        "grid": grid,
        "cells": cells,
        "chunk_start": chunk_start,
        "per_cell": per_cell,
        "budget": budget,
        "part": part,
    }
    blocks = (CONFIG, CLONE, VLLM, SERVE, SMOKE, PLAN, DOCTOR, RUN, ARCHIVE)
    return {
        "cells": [
            markdown(
                title, why, slug, cells=cells, run_hours=cells * per_cell, next_label=next_label
            ),
            *[code(substitute(block, **tokens)) for block in blocks],
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }


def grid_cells(grid: str, arm: str, model: str) -> list[dict]:
    """Ask the CLI which cells belong to this (arm, model), in grid order."""
    env = {**os.environ, "PYTHONPATH": "src"}
    out = subprocess.run(
        [sys.executable, "-m", "cli", "grid", "show", "--grid", grid, "--arm", arm],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout
    report = json.loads(out[out.index("{") :])
    return [c for c in report["cells_preview"] if c["model"] == model]


def chunk_count(total: int, per_cell: float) -> int:
    """How many notebooks a workload must be split into to fit one session."""
    usable = SESSION_CAP - SETUP_HOURS - SAFETY_HOURS
    per_notebook = int(usable // per_cell)
    if per_notebook < 1:
        raise SystemExit(f"a single cell at {per_cell} h cannot fit a session")
    return max(1, -(-total // per_notebook))


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    for existing in NOTEBOOK_DIR.glob("[0-9][0-9]-arm-*.ipynb"):
        existing.unlink()

    # Plan every chunk first so each notebook can name its successor.
    plan: list[dict] = []
    for arm, model, grid, title, why in WORKLOADS:
        cells = grid_cells(grid, arm, model)
        shape = (int(cells[0]["agents"]), bool(cells[0]["tom"]))
        per_cell = PER_CELL_HOURS[shape]
        chunks = chunk_count(len(cells), per_cell)
        sizes = [len(cells) // chunks] * chunks
        for i in range(len(cells) % chunks):
            sizes[i] += 1
        start = 0
        for size in sizes:
            plan.append(
                {
                    "arm": arm,
                    "model": model,
                    "grid": grid,
                    "title": title,
                    "why": why,
                    "per_cell": per_cell,
                    "cells": size,
                    "chunk_start": start,
                    "total": len(cells),
                }
            )
            start += size

    written = []
    for index, item in enumerate(plan):
        order = f"{index + 1:02d}"
        slug = f"{item['arm'].lower()}-{item['model']}"
        chunk_no = item["chunk_start"] // item["cells"] + 1
        chunks = chunk_count(item["total"], item["per_cell"])
        title = item["title"] if chunks == 1 else f"{item['title']} (part {chunk_no} of {chunks})"
        next_label = (
            "the last one - you are done" if index + 1 == len(plan) else f"{(index + 2):02d}"
        )
        # A chunked workload needs the part in the filename, or part 2 overwrites
        # part 1 on disk.
        suffix = f"-part{chunk_no}" if chunks > 1 else ""
        part = f"part{chunk_no}" if chunks > 1 else "part"
        path = NOTEBOOK_DIR / f"{order}-arm-{slug}{suffix}.ipynb"
        # newline="\n" matters: Path.write_text() translates to CRLF on Windows,
        # and [tool.ruff.format] line-ending = "lf" makes `ruff format --check`
        # reject every notebook otherwise.
        path.write_text(
            json.dumps(
                build(
                    model=item["model"],
                    arm=item["arm"],
                    grid=item["grid"],
                    cells=item["cells"],
                    chunk_start=item["chunk_start"],
                    per_cell=item["per_cell"],
                    budget=SESSION_CAP,
                    title=title,
                    why=item["why"],
                    next_label=next_label,
                    part=part,
                ),
                indent=1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        written.append(
            f"{path.name:<44} arm={item['arm']} {item['model']:<14} "
            f"runs={item['cells']:<3} ~{item['cells'] * item['per_cell']:4.1f} h"
        )

    print("\n".join(written))
    total_h = sum(i["cells"] * i["per_cell"] for i in plan)
    print(
        f"\n{len(written)} notebooks, "
        f"{sum(i['cells'] for i in plan)} runs, ~{total_h:.0f} h of simulation total"
    )


if __name__ == "__main__":
    main()
