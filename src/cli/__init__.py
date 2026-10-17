"""``elicit`` — the grid execution layer.

Command surface:

===================================  ==========================================
``elicit run --config <file>``        Execute one cell from a YAML config
``elicit run --preset <name>``        Execute a named preset, optionally with
                                      ``--set PARAM=value`` overrides
``elicit preset list|show|diff``      Audit the grid by diffing presets
``elicit sweep beta=... --n ...``     Arm C's beta sweep
``elicit grid run --grid <file>``     Run a manifest of cells, resumable
``elicit doctor``                     Preflight before every session
``elicit ls --arm A --model llama``   Tabulate completed cells
``elicit show <run-id>``              Headline metrics for one run
``elicit params``                     Every parameter, and whether anything reads it
``elicit export --grid <file>``       Emit Kaggle-ready per-cell bundles
===================================  ==========================================
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

from cli.config import (
    KNOWN_MODELS,
    SERVER_REQUIREMENTS,
    ConfigError,
    check_grid_parity,
    condition_key,
    expand_preset,
    load_config_file,
    preset,
    preset_names,
    validate_config,
)
from cli.runner import ResolutionError, run_one
from core.parameter_schema import ParameterError

SEED_BASE = 1000


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _apply_set_overrides(cell: dict[str, Any], assignments: list[str]) -> dict[str, Any]:
    """Apply ``--set PARAM=value`` pairs onto a cell's overrides."""
    from core.parameter_schema import coerce, get_spec

    overrides = dict(cell.get("overrides") or {})
    for assignment in assignments or []:
        if "=" not in assignment:
            raise ConfigError(f"--set expects KEY=VALUE, got {assignment!r}")
        key, raw = assignment.split("=", 1)
        key = get_spec(key.strip()).name  # validates, and gives a did-you-mean
        overrides[key] = coerce(key, raw.strip())
        # A sweep changes beta, so it is a theory cell, not a parity comparison.
        if key == "PUBLIC_GOOD_MULTIPLIER":
            cell["description"] = (
                f"{cell.get('description', '')} (beta overridden to {overrides[key]})"
            ).strip()
    cell["overrides"] = overrides
    return cell


def _cell_from_preset(name: str, assignments: list[str], seed_index: int, seeds: int):
    cells = expand_preset(name, seeds=seeds)
    cell = cells[seed_index - 1]
    return _apply_set_overrides(cell, assignments)


def _cell_to_config(cell: dict[str, Any]) -> dict[str, Any]:
    """Normalise an expanded cell into the validated-config shape."""
    payload = {
        "name": cell["name"],
        "arm": cell.get("arm", ""),
        "condition": cell.get("condition", ""),
        "description": cell.get("description", ""),
        "notes": cell.get("notes", ""),
        "model": None,
        "overrides": cell.get("overrides", {}),
    }
    overrides = dict(payload["overrides"])
    # Model, prompt variant and group counts live at the top of a cell; the rest
    # are raw parameter names.
    if cell.get("model"):
        overrides["LLM_MODEL"] = cell["model"]
    if cell.get("prompt_variant"):
        overrides["PROMPT_VARIANT"] = cell["prompt_variant"]
    if cell.get("checkpoint"):
        overrides["_checkpoint"] = cell["checkpoint"]
    payload["overrides"] = overrides
    if cell.get("group_counts"):
        payload["group_counts"] = cell["group_counts"]
    config = validate_config(payload)
    config["seed_vector"] = cell.get("seed_vector")
    if cell.get("seed") is not None:
        config.setdefault("parameters", {})["SEED"] = int(cell["seed"])
    config["preset"] = cell.get("preset")
    config["seed_index"] = cell.get("seed_index")
    return config


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    if args.config:
        raw = load_config_file(args.config)
        raw["overrides"] = {
            **dict(raw.get("overrides") or {}),
            **((args.set and _parse_set(args.set)) or {}),
        }
        config = validate_config(raw)
        config["seed_vector"] = config.get("seed_vector") or raw.get("seed_vector")
        cells = [config]
    elif args.preset:
        expanded = expand_preset(args.preset)
        index = int(args.seed_index)
        if not 1 <= index <= len(expanded):
            raise ConfigError(
                f"preset {args.preset!r} has {len(expanded)} seeds; --seed-index {index} "
                f"is out of range"
            )
        cells = [_cell_to_config(_apply_set_overrides(expanded[index - 1], args.set))]
    else:
        raise ConfigError("`elicit run` needs either --config or --preset")

    for config in cells:
        result = run_one(config, strict=not args.lenient, dry_run=args.dry_run)
        _print(result)
    return 0


def _parse_set(assignments: list[str]) -> dict[str, Any]:
    """Turn ``--set PARAM=value`` pairs into a typed override dict."""
    from core.parameter_schema import coerce, get_spec

    out: dict[str, Any] = {}
    for assignment in assignments or []:
        if "=" not in assignment:
            raise ConfigError(f"--set expects KEY=VALUE, got {assignment!r}")
        key, raw = assignment.split("=", 1)
        out[get_spec(key.strip()).name] = coerce(key.strip(), raw.strip())
    return out


# ---------------------------------------------------------------------------
# preset
# ---------------------------------------------------------------------------


def cmd_preset(args: argparse.Namespace) -> int:
    if args.preset_command == "list":
        for name in preset_names():
            spec = preset(name) or {}
            _print(
                {
                    "preset": name,
                    "arm": spec.get("arm"),
                    "model": spec.get("model"),
                    "prompt_variant": spec.get("prompt_variant"),
                    "seeds": spec.get("seeds"),
                    "description": spec.get("description"),
                }
            )
        return 0

    if args.preset_command == "show":
        shown = preset(args.name)
        if shown is None:
            raise ConfigError(f"Unknown preset {args.name!r}")
        cells = expand_preset(args.name)
        _print({"preset": args.name, "spec": shown, "cells": len(cells), "example": cells[0]})
        return 0

    if args.preset_command == "diff":
        left, right = preset(args.name), preset(args.b)
        if left is None or right is None:
            raise ConfigError("Both presets must exist to diff")
        keys = sorted(set(left.get("overrides", {})) | set(right.get("overrides", {})))
        delta = {
            key: {"a": left["overrides"].get(key), "b": right["overrides"].get(key)}
            for key in keys
            if left["overrides"].get(key) != right["overrides"].get(key)
        }
        # The factors that are not overrides still differ between two cells, and
        # for the audit arm the prompt variant is the whole treatment.
        condition = {
            field: {"a": left.get(field), "b": right.get(field)}
            for field in ("model", "prompt_variant", "seeds")
            if left.get(field) != right.get(field)
        }
        _print(
            {
                "a": args.name,
                "b": args.b,
                "different_condition_factors": condition,
                "different_parameters": delta,
                "identical_parameters": [
                    key for key in keys if left["overrides"].get(key) == right["overrides"].get(key)
                ],
                "parity_clean": not delta,
            }
        )
        return 0

    raise ConfigError(f"Unknown preset subcommand {args.preset_command!r}")


# ---------------------------------------------------------------------------
# sweep
# ---------------------------------------------------------------------------


def cmd_sweep(args: argparse.Namespace) -> int:
    """Build (and with ``--run``, execute) a one-parameter sweep."""
    if len(args.assignments) != 1:
        raise ConfigError("`elicit sweep` takes exactly one PARAM=v1,v2,v3 assignment")
    key, values = args.assignments[0].split("=", 1)
    from core.parameter_schema import get_spec

    get_spec(key)  # validates the name and gives a did-you-mean hint

    cells: list[dict[str, Any]] = []
    for value in values.split(","):
        cell = _cell_from_preset(args.preset, [], args.seed_index, 1)
        cell["name"] = (
            f"{args.preset}_{key.lower()}{value.strip().replace('.', 'p')}_s{args.seed_index}"
        )
        cell = _apply_set_overrides(cell, [f"{key}={value.strip()}"])
        cells.append(cell)

    configs = [_cell_to_config(cell) for cell in cells]
    if args.run:
        for config in configs:
            _print(run_one(config, dry_run=args.dry_run))
    else:
        _print({"sweep": key, "values": values.split(","), "cells": configs})
    return 0


# ---------------------------------------------------------------------------
# grid
# ---------------------------------------------------------------------------


def _load_grid(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Grid file not found: {path}")
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError("Grid file must be a mapping")
    return data


def _grid_cells(grid: dict[str, Any], *, arms: set[str] | None = None) -> list[dict[str, Any]]:
    """Expand a grid manifest into cells, in manifest order."""
    include = grid.get("include")
    if include is None:
        include = [
            {"arm": "A"},
            {"arm": "B"},
            {"arm": "D"},
            {"arm": "C"},
            {"arm": "E"},
        ]
    cells: list[dict[str, Any]] = []
    for entry in include:
        arm = str(entry.get("arm", "")).upper()
        if arms and arm not in arms:
            continue
        if entry.get("preset"):
            for seed_index in range(1, int(entry.get("seeds", 1)) + 1):
                cells.append(
                    _cell_from_preset(entry["preset"], [], seed_index, int(entry.get("seeds", 1)))
                )
            continue
        for preset_name in entry.get("presets", []):
            for cell in expand_preset(preset_name):
                cells.append(cell)
    return cells


def _completed_keys(results_dir: Path) -> set[str]:
    """Cell names already present in the results directory."""
    done: set[str] = set()
    if not results_dir.exists():
        return done
    for path in results_dir.glob("simulation_*.json"):
        parts = path.stem.split("_")
        # simulation_{model}_{cell_name}_seed{n}_{a}agents_{r}rounds_{stamp}
        if len(parts) >= 6 and parts[-4].startswith("seed"):
            done.add("_".join(parts[2:-4]))
    return done


def cmd_grid(args: argparse.Namespace) -> int:
    grid = _load_grid(args.grid)
    cells = _grid_cells(grid, arms={a.upper() for a in args.arm} if args.arm else None)
    configs = [_cell_to_config(cell) for cell in cells]

    # Parity is a property of the comparison set, so it is checked here and not
    # per cell. If this fires, "model effect" in the variance decomposition is
    # really a composite of several factors and the paper's claim is unfalsifiable.
    parity = check_grid_parity(configs)

    planned = sum(float(c.get("budget_gpu_hours") or 0.0) for c in configs)
    report = {
        "grid": str(args.grid),
        "arms": sorted({str(c.get("arm") or "") for c in configs if c.get("arm")}),
        "condition_groups": len({condition_key(c) for c in configs}),
        "cells": len(configs),
        "planned_gpu_hours": planned,
        "models": sorted({c["parameters"].get("LLM_MODEL", "") for c in configs}),
        "parity_violations": parity,
        "parity_ok": not parity,
    }
    if parity and args.run and not args.allow_parity_violations:
        report["status"] = "refused: fix parity violations before spending GPU-hours"
        _print(report)
        return 3

    if not args.run:
        report["cells_preview"] = [
            {
                "name": c["name"],
                "arm": c["arm"],
                "condition": c["condition"],
                "model": c["parameters"].get("LLM_MODEL"),
                "prompt_variant": c["parameters"].get("PROMPT_VARIANT"),
                "governance": c["parameters"].get("LDF_GOVERNANCE_MODE"),
                "beta": c["parameters"].get("PUBLIC_GOOD_MULTIPLIER"),
                # Cost drivers. A scheduler that has to guess these gets the
                # session budget wrong in one direction or the other.
                "agents": c["parameters"].get("NUM_AGENTS"),
                "rounds": c["parameters"].get("NUM_ROUNDS"),
                "tom": c["parameters"].get("TOM_ENABLED"),
                # The runnable coordinates. A cell's *name* is not its preset:
                # "arm_a_p0_qwen_s1" is preset "a_qwen_p0", seed 1, and the name
                # cannot be split back into that reliably.
                "preset": c.get("preset"),
                "seed_index": c.get("seed_index"),
            }
            for c in configs
        ]
        _print(report)
        return 0

    results_dir = Path(grid.get("results_dir", "results"))
    done = _completed_keys(results_dir) if args.resume else set()
    executed, skipped, failed = 0, 0, []
    for config in configs:
        if config["name"] in done:
            skipped += 1
            continue
        try:
            result = run_one(config, strict=not args.lenient, dry_run=args.dry_run)
            executed += 1
            _print(result)
        except (ConfigError, ResolutionError) as exc:
            failed.append({"name": config["name"], "error": str(exc)})
            _print(failed[-1])
        if args.max_runs and executed >= args.max_runs:
            break
    report.update({"executed": executed, "skipped_completed": skipped, "failed": failed})
    _print(report)
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> int:
    """Preflight: the check to run before every compute session.

    With --preset/--config the named cell is applied to ``parameters`` first, so
    the checks describe the cell that is about to run. Without one they describe
    the module defaults, which is only meaningful for a no-override cell: a grid
    cell's seed vector and chat template live in its config, not in the defaults.
    """
    from core import parameters
    from core.governance import GovernanceMode
    from core.seeding import validate_seed_vector
    from prompts.prompt_variants import active_variant, variant_hash

    findings: list[dict[str, Any]] = []
    cell: dict[str, Any] | None = None
    declared_governance = ""

    if args.preset or args.config:
        if args.preset:
            expanded = expand_preset(args.preset)
            index = int(args.seed_index)
            if not 1 <= index <= len(expanded):
                raise ConfigError(
                    f"preset {args.preset!r} has {len(expanded)} seeds; "
                    f"--seed-index {index} is out of range"
                )
            raw_cell = expanded[index - 1]
            # Read the intent off the raw cell: validate_config() restructures
            # `overrides`, so the declared mode is not readable afterwards.
            declared_governance = str(
                (raw_cell.get("overrides") or {}).get("LDF_GOVERNANCE_MODE") or ""
            ).lower()
            cell = _cell_to_config(_apply_set_overrides(raw_cell, args.set))
        else:
            raw = load_config_file(args.config)
            raw["overrides"] = {
                **dict(raw.get("overrides") or {}),
                **((args.set and _parse_set(args.set)) or {}),
            }
            declared_governance = str(raw["overrides"].get("LDF_GOVERNANCE_MODE") or "").lower()
            cell = validate_config(raw)
            cell["seed_vector"] = cell.get("seed_vector") or raw.get("seed_vector")
        # Apply without running: this is a preflight, not a simulation.
        from cli.runner import prepare_run

        prepare_run(cell, strict=not args.lenient)

    def check(name: str, ok: bool, detail: str = "") -> None:
        findings.append({"check": name, "ok": bool(ok), "detail": detail})

    # 1. Governance matches what the cell intends. The dangerous failure is
    #    governance silently ON for a cell that should have had it off, so with
    #    no cell loaded this stays the "defaults are G0" check. With a cell
    #    loaded, Arm D cells are *supposed* to run at G1/G2/G3/G3c, and the
    #    check becomes "the live level is the one this cell declares".
    live_level = GovernanceMode().level
    if cell is None:
        check(
            "governance_default_off",
            live_level == "G0",
            f"LDF_GOVERNANCE_MODE={parameters.LDF_GOVERNANCE_MODE} -> {live_level}",
        )
    else:
        expected_arm = str(cell.get("arm") or "").upper()
        if expected_arm == "D" or declared_governance not in ("", "fixed", "g0"):
            check(
                "governance_matches_cell",
                declared_governance == str(parameters.LDF_GOVERNANCE_MODE).lower(),
                f"cell declares LDF_GOVERNANCE_MODE={declared_governance!r}, "
                f"live is {parameters.LDF_GOVERNANCE_MODE!r} -> {live_level}",
            )
        else:
            check(
                "governance_off_for_non_governance_arm",
                live_level == "G0",
                f"arm {expected_arm} should be G0, live is {live_level}",
            )

    # 2. Prompt variant resolves and hashes.
    variant = active_variant()
    check("prompt_variant_resolves", True, f"{variant.name} sha256={variant_hash(variant)[:12]}")

    # 3. Chat template parity for cross-model work.
    check(
        "chat_template_fixed_for_parity",
        str(parameters.CHAT_TEMPLATE_MODE).lower() == "fixed",
        f"CHAT_TEMPLATE_MODE={parameters.CHAT_TEMPLATE_MODE}; cross-model cells require 'fixed'",
    )

    # 4. Seed vector complete.
    problems = validate_seed_vector(parameters.SEED_VECTOR)
    check("seed_vector_complete", not problems, "; ".join(problems))

    # 5. Sampling pinned and in range.
    check(
        "sampling_in_range",
        0.0 <= parameters.LLM_TEMPERATURE <= 2.0 and 0.0 < parameters.LLM_TOP_P <= 1.0,
        f"temperature={parameters.LLM_TEMPERATURE} top_p={parameters.LLM_TOP_P}",
    )

    # 6. Shock schedule is decoupled from the constitutional interval.
    shock_rounds = [int(r) for r, _ in parameters.CLIMATE_SHOCK_SCHEDULE]
    interval = int(parameters.DEMOCRACY_INTERVAL)
    check(
        "shocks_decoupled_from_democracy",
        all(r % interval != 0 for r in shock_rounds),
        f"shock rounds {shock_rounds}, DEMOCRACY_INTERVAL={interval}",
    )

    # 7. MCPR vs group size — Arm C must actually cross the threshold.
    group_counts = parameters.LDF_AGENT_GROUP_COUNTS or {}
    n = int(group_counts.get("developed", 0)) + int(group_counts.get("developing", 0)) or int(
        parameters.NUM_AGENTS
    )
    mcpr = parameters.PUBLIC_GOOD_MULTIPLIER / max(1, n)
    check(
        "mcpr_reported",
        True,
        f"beta={parameters.PUBLIC_GOOD_MULTIPLIER} n={n} MCPR={mcpr:.4f}"
        + (
            " (>= 1: above the theoretical threshold)"
            if mcpr >= 1
            else " (< 1: zero is a best response)"
        ),
    )

    # 8. LLM reachability and served-name agreement.
    reachable, served = _probe_llm()
    check("llm_reachable", reachable, served or "no endpoint configured")
    if args.model and parameters.LLM_MODEL and args.model != parameters.LLM_MODEL:
        check(
            "served_model_name_matches",
            False,
            f"cell declares {parameters.LLM_MODEL}, server was asked for {args.model}",
        )
    elif parameters.LLM_MODEL:
        check("served_model_name_matches", True, parameters.LLM_MODEL)

    ok = all(f["ok"] for f in findings)
    _print(
        {
            "ok": ok,
            "cell": cell.get("name") if cell else None,
            "findings": findings,
        }
    )
    return 0 if ok else 1


def _probe_llm() -> tuple[bool, str]:
    from core import parameters

    base = str(parameters.LLM_BASE_URL).rstrip("/")
    try:
        import urllib.request

        with urllib.request.urlopen(f"{base}/models", timeout=5) as response:
            import json as _json

            payload = _json.loads(response.read())
            names = [m.get("id") for m in payload.get("data", [])]
            return True, f"served: {names}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# ls / show
# ---------------------------------------------------------------------------


def cmd_ls(args: argparse.Namespace) -> int:
    results_dir = Path(args.results_dir)
    rows: list[dict[str, Any]] = []
    if results_dir.exists():
        for path in sorted(results_dir.glob("simulation_*.json")):
            name = path.stem
            cell = "_".join(name.split("_")[2:-4]) if len(name.split("_")) >= 6 else name
            rows.append(
                {
                    "cell": cell,
                    "file": path.name,
                    "bytes": path.stat().st_size,
                    "arm": _infer_arm(cell),
                    "model": name.split("_")[1] if "_" in name else "",
                }
            )
    if args.arm:
        rows = [r for r in rows if r["arm"].upper() == args.arm.upper()]
    if args.model:
        rows = [r for r in rows if args.model.lower() in r["model"].lower()]
    _print({"results_dir": str(results_dir), "count": len(rows), "cells": rows})
    return 0


def _infer_arm(cell: str) -> str:
    for arm in ("arm_a", "arm_b", "arm_c", "arm_d", "arm_e"):
        if cell.startswith(arm):
            return arm[-1].upper()
    return "?"


def cmd_show(args: argparse.Namespace) -> int:
    from analysis.qwen_9seed.io import as_rounds, load_json

    path = Path(args.results_dir) / f"simulation_{args.run_id}.json"
    if not path.exists():
        matches = sorted(Path(args.results_dir).glob(f"*{args.run_id}*"))
        if not matches:
            raise ConfigError(f"No run matching {args.run_id!r} under {args.results_dir}")
        path = matches[0]

    payload = load_json(path)
    rounds = as_rounds(payload)
    if not rounds:
        raise ConfigError(f"{path.name} contains no rounds")

    def mean(key: str) -> float:
        values = [r.get(key, 0.0) or 0.0 for r in rounds if isinstance(r.get(key), (int, float))]
        return sum(values) / len(values) if values else float("nan")

    provenance = payload.get("provenance") if isinstance(payload, dict) else {}
    last = rounds[-1]
    agents = last.get("agents", {})
    groups: dict[str, list[float]] = {}
    for data in agents.values():
        groups.setdefault(str(data.get("agent_group", "?")), []).append(
            float(data.get("wealth", 0.0) or 0.0)
        )
    group_means = {group: sum(wealth) / len(wealth) for group, wealth in groups.items() if wealth}
    ratio = (
        group_means.get("developed", 0.0) / group_means["developing"]
        if group_means.get("developing")
        else float("nan")
    )

    _print(
        {
            "file": path.name,
            "rounds": len(rounds),
            "prompt_variant": (provenance or {}).get("prompt_variant", {}).get("name"),
            "prompt_variant_hash": (provenance or {}).get("prompt_variant", {}).get("hash"),
            "governance_mode": (provenance or {}).get("governance", {}).get("mode"),
            "seed_fingerprint": (payload or {}).get("seed_fingerprint")
            if isinstance(payload, dict)
            else None,
            "mean_cooperation_rate": mean("cooperation_rate"),
            "mean_contribution_intensity": mean("contribution_intensity"),
            "final_gini": last.get("gini_wealth"),
            "total_ldf_deposits": sum(r.get("ldf_contributions_total", 0.0) or 0.0 for r in rounds),
            "total_ldf_payouts": sum(r.get("ldf_payouts_total", 0.0) or 0.0 for r in rounds),
            "shock_rounds": [r.get("round_number") for r in rounds if r.get("shock_occurred")],
            "terminal_developed_over_developing_wealth": ratio,
        }
    )
    return 0


# ---------------------------------------------------------------------------
# params
# ---------------------------------------------------------------------------


def cmd_params(args: argparse.Namespace) -> int:
    from core import parameters
    from core.parameter_schema import collect_parameter_reads, iter_specs

    reads = collect_parameter_reads()
    rows = []
    for spec in iter_specs():
        if args.category and spec.category != args.category:
            continue
        readers = sorted(reads.get(spec.name, set()))
        if args.unread_only and readers:
            continue
        rows.append(
            {
                "name": spec.name,
                "category": spec.category,
                "type": spec.type_name,
                "current": getattr(parameters, spec.name, "<absent>"),
                "default": spec.default,
                "min": spec.minimum,
                "max": spec.maximum,
                "read_by": readers,
                "read": bool(readers),
                "description": spec.description,
            }
        )
    if args.json:
        _print(rows)
    else:
        width = max((len(r["name"]) for r in rows), default=8)
        print(f"{'PARAMETER':<{width}}  {'TYPE':<8} {'CURRENT':>14}  READ BY")
        print("-" * (width + 40))
        for row in rows:
            marker = ",".join(Path(f).stem for f in row["read_by"]) or "-- UNREAD --"
            print(f"{row['name']:<{width}}  {row['type']:<8} {row['current']!s:>14}  {marker}")
        unread = [r["name"] for r in rows if not r["read"]]
        print(f"\n{len(rows)} parameters; {len(unread)} unread: {', '.join(unread) or 'none'}")
    return 0


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

#: One cell = one config file plus the server command that loads its model. The
#: notebook clones the repo, installs the venv, starts the server from serve.sh,
#: then executes run_cell.py for each cell whose model matches the served alias.
RUN_CELL_STUB = '''"""Auto-generated by `elicit export`. Execute one grid cell.

Read the config from disk rather than inlining it: a config is a versioned
artefact, and the pre-registration claim only holds if the cell that ran is
recoverable from the cell that is declared here.
"""
import json
import subprocess
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
REPO_SRC = Path("/kaggle/working/elicit/src")
sys.path.insert(0, str(REPO_SRC))

from core import parameters  # noqa: E402
from cli.runner import prepare_run, write_preflight  # noqa: E402

config = json.loads((BUNDLE / "config.json").read_text(encoding="utf-8"))
summary = prepare_run(config)

print("=== resolved cell ===")
print(json.dumps(summary, indent=2, default=str))
print(f"preflight manifest: {write_preflight(config, summary)}")

served = json.loads((BUNDLE / "served_model_name.txt").read_text(encoding="utf-8")).strip()
if parameters.LLM_MODEL != served:
    raise SystemExit(
        f"REFUSING TO RUN: cell declares model {parameters.LLM_MODEL!r} but this session "
        f"served {served!r}. Start the server with this bundle's serve.sh, or run a cell "
        f"whose model matches."
    )

command = [
    sys.executable, str(REPO_SRC / "main.py"),
    "--num-rounds", str(parameters.NUM_ROUNDS),
    "--num-agents", str(parameters.NUM_AGENTS),
    "--model-name", str(parameters.LLM_MODEL),
    "--scenario", str(parameters.SCENARIO),
    "--agent-type", str(parameters.AGENT_TYPE),
]
if parameters.CLIMATE_SHOCK_ENABLED:
    command.append("--enable-climate-shocks")
if parameters.LDF_ENABLED:
    command.append("--enable-ldf")
print("COMMAND:", " ".join(command))
subprocess.run(command, check=True)
print("=== cell complete ===")
'''

SERVE_STUB = """#!/usr/bin/env bash
# Auto-generated by `elicit export` for cell {cell_name}.
#
# Tensor parallelism {tp} and --max-model-len {max_len} are held identical across
# every model family in the grid. If they differ, "model effect" in the variance
# decomposition is really an effect of serving configuration, and the contrast
# cannot be interpreted. --served-model-name must equal the cell's model alias.
set -euo pipefail

VLLM_BIN="${{VLLM_BIN:-/kaggle/working/vllm-env/bin/vllm}}"
exec "$VLLM_BIN" serve "{checkpoint}" \\
  --served-model-name "{alias}" \\
  --tensor-parallel-size {tp} \\
  --max-model-len {max_len} \\
  --max-num-seqs 32 \\
  --dtype {dtype} \\
  --port 8000
"""


def cmd_export(args: argparse.Namespace) -> int:
    """Emit Kaggle-ready cell bundles: config + runner + serve script."""
    import zipfile

    grid = _load_grid(args.grid)
    cells = _grid_cells(grid, arms={a.upper() for a in args.arm} if args.arm else None)
    configs = [_cell_to_config(cell) for cell in cells]
    parity = check_grid_parity(configs)

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    written: list[dict[str, Any]] = []
    for config in configs:
        model = str(config["parameters"].get("LLM_MODEL", ""))
        spec = SERVER_REQUIREMENTS.get(model, {})
        bundle = out_root / config["name"]
        bundle.mkdir(parents=True, exist_ok=True)

        (bundle / "config.json").write_text(
            json.dumps(config, indent=2, default=str), encoding="utf-8"
        )
        (bundle / "run_cell.py").write_text(RUN_CELL_STUB, encoding="utf-8")
        (bundle / "served_model_name.txt").write_text(model, encoding="utf-8")
        (bundle / "serve.sh").write_text(
            SERVE_STUB.format(
                cell_name=config["name"],
                checkpoint=spec.get("checkpoint", ""),
                alias=model,
                tp=spec.get("tensor_parallel", 2),
                max_len=config["parameters"].get("VLLM_MAX_MODEL_LEN", 8192),
                dtype="half",
            ),
            encoding="utf-8",
        )
        written.append(
            {
                "cell": config["name"],
                "arm": config["arm"],
                "model": model,
                "served_alias": model,
                "checkpoint": spec.get("checkpoint"),
                "bundle": str(bundle),
            }
        )

    if args.zip:
        archive = out_root / f"elicit_grid_{args.zip}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in written:
                for file in Path(entry["bundle"]).iterdir():
                    zf.write(file, arcname=f"{entry['cell']}/{file.name}")
        written.append({"archive": str(archive), "cells": len(written) - 1})

    _print(
        {
            "out": str(out_root),
            "bundles": len(written) - (1 if args.zip else 0),
            "parity_violations": parity,
            "next": (
                "Group the bundles by served model: one Kaggle session loads one "
                "model, so a session runs every cell whose model matches the alias "
                "it started. `elicit grid show` lists the cells; run_cell.py refuses "
                "to start if the served alias does not match the cell."
            ),
            "written": written,
        }
    )
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="elicit",
        description="ELICIT grid execution layer: presets, sweeps, grids, preflight.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Execute one cell from a config or a preset.")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", help="Path to a YAML cell.")
    source.add_argument("--preset", help="Preset name.")
    run.add_argument("--seed-index", type=int, default=1, help="Which seed of the preset.")
    run.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="PARAM=VALUE",
        help="Typed, range-checked override. Repeatable.",
    )
    run.add_argument("--dry-run", action="store_true", help="Resolve and preflight only.")
    run.add_argument("--lenient", action="store_true", help="Skip unknown parameter names.")
    run.set_defaults(func=cmd_run)

    preset_parser = sub.add_parser("preset", help="Inspect the preset registry.")
    preset_parser.add_argument("preset_command", choices=["list", "show", "diff"])
    preset_parser.add_argument("name", nargs="?", help="Preset name.")
    preset_parser.add_argument("b", nargs="?", help="Second preset, for diff.")
    preset_parser.set_defaults(func=cmd_preset)

    sweep = sub.add_parser("sweep", help="Build or run a one-parameter sweep.")
    sweep.add_argument("assignments", nargs="+", metavar="PARAM=v1,v2,v3")
    sweep.add_argument("--preset", default="a_p0_qwen", help="Base preset.")
    sweep.add_argument("--seed-index", type=int, default=1)
    sweep.add_argument("--run", action="store_true", help="Execute instead of printing.")
    sweep.add_argument("--dry-run", action="store_true")
    sweep.set_defaults(func=cmd_sweep)

    grid = sub.add_parser("grid", help="Run a manifest of cells.")
    grid.add_argument("grid_command", choices=["run", "show"], help="run executes; show previews.")
    grid.add_argument("--grid", required=True, help="Path to the grid YAML.")
    grid.add_argument("--arm", action="append", help="Restrict to these arms.")
    grid.add_argument("--resume", action="store_true", help="Skip cells already completed.")
    grid.add_argument("--max-runs", type=int, default=0, help="Stop after N cells.")
    grid.add_argument("--dry-run", action="store_true")
    grid.add_argument("--lenient", action="store_true")
    grid.add_argument(
        "--allow-parity-violations",
        action="store_true",
        help="Run anyway despite cross-model parity violations. Not recommended.",
    )
    grid.set_defaults(func=cmd_grid)

    doctor = sub.add_parser("doctor", help="Preflight before a compute session.")
    doctor.add_argument("--model", help="Served model name the session was started with.")
    doctor.add_argument(
        "--preset", help="Validate this preset's cell instead of the module defaults."
    )
    doctor.add_argument("--config", help="Validate this config file's cell.")
    doctor.add_argument(
        "--seed-index", type=int, default=1, help="Seed index within the preset (1-based)."
    )
    doctor.add_argument("--set", action="append", metavar="PARAM=VALUE", help="Extra override.")
    doctor.add_argument("--lenient", action="store_true", help="Do not fail on unread parameters.")
    doctor.set_defaults(func=cmd_doctor)

    ls_parser = sub.add_parser("ls", help="Tabulate completed cells.")
    ls_parser.add_argument("--results-dir", default="results")
    ls_parser.add_argument("--arm")
    ls_parser.add_argument("--model")
    ls_parser.set_defaults(func=cmd_ls)

    show = sub.add_parser("show", help="Headline metrics for one run.")
    show.add_argument("run_id")
    show.add_argument("--results-dir", default="results")
    show.set_defaults(func=cmd_show)

    params = sub.add_parser("params", help="Every parameter, and whether anything reads it.")
    params.add_argument("--category")
    params.add_argument("--unread-only", action="store_true")
    params.add_argument("--json", action="store_true")
    params.set_defaults(func=cmd_params)

    export = sub.add_parser("export", help="Emit Kaggle-ready cell bundles.")
    export.add_argument("--grid", required=True)
    export.add_argument("--out", required=True)
    export.add_argument("--arm", action="append")
    export.add_argument("--zip", help="Also write <name>.zip containing every bundle.")
    export.set_defaults(func=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "grid" and args.grid_command == "show":
        args.run = False
    elif args.command == "grid":
        args.run = True
    try:
        return int(args.func(args) or 0)
    except (ConfigError, ResolutionError, ParameterError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "KNOWN_MODELS",
    "SERVER_REQUIREMENTS",
    "ConfigError",
    "build_parser",
    "difflib",
    "main",
    "preset_names",
]
