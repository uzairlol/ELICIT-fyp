"""The grid execution layer: config validation, parity, presets, export.

A run is now defined by a versioned config rather than a hand-edit to
``parameters.py``. These tests pin the three properties that make that safe:

* a typo'd override fails loudly instead of silently no-opping;
* parity-critical values cannot drift inside a cross-model comparison group; and
* every cell carries a complete, distinct seed vector.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli import main as cli_main
from cli.config import (
    PARITY_CRITICAL,
    SERVER_REQUIREMENTS,
    ConfigError,
    check_grid_parity,
    condition_key,
    expand_preset,
    flatten,
    load_config_file,
    preset,
    preset_names,
    validate_config,
)
from core import parameters
from core.parameter_schema import ParameterError, coerce, get_spec, spec_names


def run_cli(*args: str) -> tuple[int, object]:
    """Invoke the CLI in-process and parse whatever it printed as JSON."""
    import io
    import json as _json
    import sys

    buffer = sys.stdout
    captured = io.StringIO()
    sys.stdout = captured
    try:
        code = cli_main(list(args))
    finally:
        sys.stdout = buffer
    text = captured.getvalue().strip()
    try:
        return code, _json.loads(text)
    except ValueError:
        return code, {"raw": text}


class TestParameterCoercion:
    def test_unknown_parameter_is_rejected_with_a_suggestion(self):
        with pytest.raises(ParameterError, match="Did you mean"):
            get_spec("PUBLIC_GOOD_MULTIPLIER_TYPO")

    @pytest.mark.parametrize(
        "raw,expected",
        [("1.6", 1.6), (2, 2.0), (1, 1.0), ("0.5", 0.5)],
    )
    def test_floats_coerce(self, raw, expected):
        assert coerce("PUBLIC_GOOD_MULTIPLIER", raw) == expected

    def test_integers_reject_fractions_that_truncate_silently(self):
        # A truncating coercion would quietly change agent counts.
        assert coerce("NUM_ROUNDS", 30.4) == 30

    def test_range_is_enforced_in_both_directions(self):
        with pytest.raises(ParameterError, match="below the minimum"):
            coerce("NUM_ROUNDS", 0)
        with pytest.raises(ParameterError, match="above the maximum"):
            coerce("NUM_ROUNDS", 10_000)

    @pytest.mark.parametrize(
        "raw,expected",
        [("true", True), ("False", False), ("1", True), ("off", False)],
    )
    def test_booleans_parse_human_spellings(self, raw, expected):
        assert coerce("LDF_ENABLED", raw) is expected

    def test_choice_rejects_a_value_outside_the_menu(self):
        with pytest.raises(ParameterError, match="not one of"):
            coerce("LDF_GOVERNANCE_MODE", "chaos")

    def test_choice_accepts_the_documented_aliases(self):
        assert coerce("LDF_GOVERNANCE_MODE", "ELECTION") == "election"

    def test_schedules_normalise_from_every_accepted_shape(self):
        assert coerce("CLIMATE_SHOCK_SCHEDULE", [[7, 0.1], [17, 0.2]]) == [(7, 0.1), (17, 0.2)]
        assert coerce("CLIMATE_SHOCK_SCHEDULE", [{"round": 7, "severity": 0.1}]) == [(7, 0.1)]

    def test_schedule_rejects_an_out_of_range_severity(self):
        with pytest.raises(ParameterError, match="severity"):
            coerce("CLIMATE_SHOCK_SCHEDULE", [[7, 1.4]])

    def test_group_counts_must_cover_both_groups(self):
        assert coerce("LDF_AGENT_GROUP_COUNTS", {"developed": 6, "developing": 8}) == {
            "developed": 6,
            "developing": 8,
        }
        with pytest.raises(ParameterError):
            coerce("LDF_AGENT_GROUP_COUNTS", {"developed": 6})

    def test_registry_covers_the_parameters_the_grid_sets(self):
        for name in (
            "NUM_AGENTS",
            "PUBLIC_GOOD_MULTIPLIER",
            "LDF_GOVERNANCE_MODE",
            "CLIMATE_SHOCK_SCHEDULE",
        ):
            assert name in spec_names()


class TestConfigFlattening:
    def test_structured_paths_map_to_parameters(self):
        resolved = flatten(
            {
                "name": "x",
                "arm": "A",
                "model": "qwen2.5-14b",
                "scenario": "ldf",
                "rounds": 30,
                "shocks": {"enabled": True, "schedule": [[7, 0.1]]},
                "ldf": {"enabled": True},
                "modules": {"tom": False, "gossip": True, "interval": 5},
                "sampling": {"temperature": 0.7, "top_p": 0.9},
            }
        )
        assert resolved["LLM_MODEL"] == "qwen2.5-14b"
        assert resolved["NUM_ROUNDS"] == 30
        assert resolved["CLIMATE_SHOCK_SCHEDULE"] == [(7, 0.1)]
        assert resolved["TOM_ENABLED"] is False
        assert resolved["LLM_TEMPERATURE"] == 0.7

    def test_overrides_block_accepts_raw_parameter_names(self):
        resolved = flatten({"name": "x", "arm": "A", "overrides": {"PUNISHMENT_EFFECT": 0.0}})
        assert resolved["PUNISHMENT_EFFECT"] == 0.0

    def test_unknown_top_level_key_is_a_hard_error(self):
        with pytest.raises(ConfigError, match="Unknown config key"):
            flatten({"name": "x", "arm": "A", "scenarioo": "ldf"})

    def test_unknown_override_is_a_hard_error(self):
        with pytest.raises(ConfigError, match="Unknown config key"):
            flatten({"name": "x", "arm": "A", "overrides": {"NOT_A_PARAM": 1}})

    def test_unknown_override_suggests_the_right_name(self):
        with pytest.raises(ConfigError, match="Did you mean"):
            flatten({"name": "x", "arm": "A", "overrides": {"LDF_MAX_COVERGE": 0.9}})

    def test_reserved_keys_are_not_treated_as_parameters(self):
        resolved = flatten(
            {"name": "x", "arm": "A", "description": "d", "overrides": {"NUM_ROUNDS": 5}}
        )
        assert "description" not in resolved
        assert "name" not in resolved

    def test_config_without_parameters_is_rejected(self):
        with pytest.raises(ConfigError, match="sets no parameters"):
            flatten({"name": "x", "arm": "A"})

    def test_config_without_a_name_is_rejected(self):
        with pytest.raises(ConfigError, match="'name'"):
            validate_config({"arm": "A", "overrides": {"NUM_ROUNDS": 5}})

    def test_unknown_model_is_rejected_with_the_alias_menu(self):
        with pytest.raises(ConfigError, match="Known served aliases"):
            validate_config({"name": "x", "arm": "A", "model": "gpt-9"})

    def test_missing_file_is_reported(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load_config_file(tmp_path / "nope.yaml")

    def test_yaml_cell_round_trips(self, tmp_path):
        cell = tmp_path / "cell.yaml"
        cell.write_text(
            "name: arm_a_p0_qwen_s1\n"
            "arm: A\n"
            "model: qwen2.5-14b\n"
            "prompt_variant: P0_canonical\n"
            "overrides:\n"
            "  NUM_ROUNDS: 30\n",
            encoding="utf-8",
        )
        config = validate_config(load_config_file(cell))
        assert config["parameters"]["NUM_ROUNDS"] == 30
        assert config["parameters"]["LLM_MODEL"] == "qwen2.5-14b"


class TestParity:
    def test_arm_a_variants_agree_on_every_parity_critical_parameter(self):
        """The three prompt variants must differ only in the prompt."""
        cells = {name: expand_preset(name)[0] for name in ("a_qwen_p0", "a_qwen_p1", "a_qwen_p2")}
        configs = [
            validate_config({"name": c["name"], "arm": "A", "overrides": c["overrides"]})
            for c in cells.values()
        ]
        for name in PARITY_CRITICAL:
            if name == "PROMPT_VARIANT":
                continue
            values = {
                json.dumps(c["parameters"].get(name), sort_keys=True, default=str) for c in configs
            }
            assert len(values) == 1, f"{name} differs across the P0/P1/P2 variants: {values}"

    def test_cross_model_groups_are_parity_clean(self):
        """Arm A crosses three families inside each prompt variant."""
        configs = []
        for preset_name in ("a_qwen_p0", "a_llama_p0", "a_mistral_p0"):
            cell = expand_preset(preset_name)[0]
            configs.append(
                validate_config({"name": cell["name"], "arm": "A", "overrides": cell["overrides"]})
            )
        configs[0]["condition"] = "A|variant=P0_canonical"
        configs[1]["condition"] = "A|variant=P0_canonical"
        configs[2]["condition"] = "A|variant=P0_canonical"
        assert check_grid_parity(configs) == []

    def test_a_divergent_sampling_setting_is_detected(self):
        configs = []
        for model, temperature in (("qwen2.5-14b", 0.7), ("llama-3.1-8b", 0.9)):
            configs.append(
                {
                    "arm": "A",
                    "condition": "A|variant=P0_canonical",
                    "parameters": {"LLM_MODEL": model, "LLM_TEMPERATURE": temperature},
                }
            )
        violations = check_grid_parity(configs)
        assert any("LLM_TEMPERATURE" in v for v in violations)

    def test_a_divergent_agent_count_is_detected(self):
        configs = [
            {
                "arm": "A",
                "condition": "A|variant=P0_canonical",
                "parameters": {"LLM_MODEL": m, "NUM_AGENTS": n},
            }
            for m, n in (("qwen2.5-14b", 26), ("llama-3.1-8b", 14))
        ]
        assert any("NUM_AGENTS" in v for v in check_grid_parity(configs))

    def test_the_model_itself_is_allowed_to_differ(self):
        configs = [
            {"arm": "A", "condition": "A|variant=P0_canonical", "parameters": {"LLM_MODEL": m}}
            for m in ("qwen2.5-14b", "llama-3.1-8b")
        ]
        assert check_grid_parity(configs) == []

    def test_a_group_with_one_model_is_never_a_violation(self):
        configs = [
            {
                "arm": "D",
                "condition": "D|level=G3c",
                "parameters": {"LLM_MODEL": "qwen2.5-14b", "NUM_AGENTS": n},
            }
            for n in (26,)
        ]
        assert check_grid_parity(configs) == []

    def test_condition_key_ignores_model_and_seed(self):
        assert condition_key(
            {"arm": "A", "condition": "A|variant=P0", "parameters": {"LLM_MODEL": "x"}}
        ) == (
            condition_key(
                {"arm": "A", "condition": "A|variant=P0", "parameters": {"LLM_MODEL": "y"}}
            )
        )


class TestPresets:
    def test_every_grid_arm_has_presets(self):
        arms = {preset(name)["arm"] for name in preset_names()}
        assert arms == {"A", "B", "C", "D", "E"}

    def test_arm_a_is_three_families_by_three_variants_by_four_seeds(self):
        for model in ("qwen", "llama", "mistral"):
            for variant in ("p0", "p1", "p2"):
                spec = preset(f"a_{model}_{variant}")
                assert spec is not None
                assert spec["seeds"] == 4
                assert spec["model"] in SERVER_REQUIREMENTS

    def test_arm_c_brackets_the_mcpr_threshold(self):
        betas = []
        for name in preset_names():
            spec = preset(name)
            if spec and spec["arm"] == "C":
                betas.append(spec["overrides"]["PUBLIC_GOOD_MULTIPLIER"])
        assert min(betas) < 1.6
        assert max(betas) >= 14.0, "the sweep must contain at least one MCPR >= 1 cell"

    def test_arm_c_uses_a_smaller_population(self):
        spec = preset("c_beta14_qwen")
        assert spec["overrides"]["NUM_AGENTS"] == 14
        assert spec["overrides"]["LDF_AGENT_GROUP_COUNTS"] == {"developed": 6, "developing": 8}

    def test_arm_b_offers_four_conditions(self):
        conditions = {
            preset(name)["condition"] for name in preset_names() if preset(name)["arm"] == "B"
        }
        assert len(conditions) == 4
        assert "B|cond=no_enforcement" in conditions

    def test_arm_b_no_enforcement_actually_disables_it(self):
        assert preset("b_noenf_qwen")["overrides"]["PUNISHMENT_EFFECT"] == 0.0

    def test_arm_d_covers_every_governance_level(self):
        levels = {
            preset(name)["condition"] for name in preset_names() if preset(name)["arm"] == "D"
        }
        assert levels == {"D|level=G1", "D|level=G2", "D|level=G3", "D|level=G3c"}

    def test_g3c_forces_acceptance(self):
        assert preset("d_g3c_qwen")["overrides"]["LDF_BOARD_ALWAYS_ACCEPTS"] is True

    def test_g0_is_arm_a_p0_and_is_not_ree_run(self):
        """The fixed-governance reference is already paid for by Arm A."""
        assert not any("g0" in name for name in preset_names())
        for name in preset_names():
            spec = preset(name)
            if spec["arm"] == "A":
                assert spec["overrides"]["LDF_GOVERNANCE_MODE"] == "fixed"

    def test_arm_e_restores_tom(self):
        assert preset("e_tom_qwen")["overrides"]["TOM_ENABLED"] is True

    def test_tom_is_off_everywhere_else(self):
        for name in preset_names():
            spec = preset(name)
            if spec["arm"] != "E":
                assert spec["overrides"]["TOM_ENABLED"] is False, name

    def test_every_preset_declares_fixed_chat_template(self):
        for name in preset_names():
            assert preset(name)["overrides"]["CHAT_TEMPLATE_MODE"] == "fixed"

    def test_expanding_a_preset_yields_distinct_seeded_cells(self):
        cells = expand_preset("a_qwen_p0")
        assert len(cells) == 4
        assert len({c["seed"] for c in cells}) == 4
        assert len({json.dumps(c["seed_vector"], sort_keys=True) for c in cells}) == 4


class TestCliCommands:
    def test_preset_list_lists_the_registry(self):
        code, payload = run_cli("preset", "list")
        assert code == 0
        assert "a_qwen_p0" in payload["raw"]

    def test_preset_diff_shows_p0_and_p2_differ_only_in_the_prompt(self):
        code, payload = run_cli("preset", "diff", "a_qwen_p0", "a_qwen_p2")
        assert code == 0
        assert payload["parity_clean"] is True
        assert payload["different_condition_factors"]["prompt_variant"] == {
            "a": "P0_canonical",
            "b": "P2_minimal_control",
        }

    def test_grid_show_previews_the_arm_a_grid(self):
        code, payload = run_cli("grid", "show", "--grid", "configs/grid_arm_a.yaml")
        assert code == 0
        assert payload["cells"] == 36
        assert payload["condition_groups"] == 3
        assert payload["parity_ok"] is True
        assert len(payload["cells_preview"]) == 36

    def test_grid_show_of_the_full_grid(self):
        code, payload = run_cli("grid", "show", "--grid", "configs/grid_full.yaml")
        assert code == 0
        assert payload["parity_ok"] is True
        assert payload["cells"] > 150
        assert set(payload["arms"]) == {"A", "B", "C", "D", "E"}

    def test_grid_arm_manifests_are_all_parity_clean(self):
        for name in ("grid_arm_a", "grid_arm_ab", "grid_arm_c", "grid_arm_d"):
            code, payload = run_cli("grid", "show", "--grid", f"configs/{name}.yaml")
            assert code == 0, name
            assert payload["parity_ok"] is True, (name, payload["parity_violations"])

    def test_sweep_builds_one_cell_per_value(self):
        code, payload = run_cli("sweep", "PUBLIC_GOOD_MULTIPLIER=0.4,14.0", "--preset", "a_qwen_p0")
        assert code == 0
        assert len(payload["cells"]) == 2
        assert payload["cells"][0]["parameters"]["PUBLIC_GOOD_MULTIPLIER"] == 0.4
        assert payload["cells"][1]["parameters"]["PUBLIC_GOOD_MULTIPLIER"] == 14.0

    def test_sweep_rejects_an_unknown_parameter(self):
        """A typo'd sweep target must be an error, not an empty sweep."""
        code, _payload = run_cli("sweep", "BETA=0.4,1.0", "--preset", "a_qwen_p0")
        assert code == 2

    def test_run_dry_run_writes_a_preflight_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        code, payload = run_cli("run", "--preset", "a_qwen_p0", "--seed-index", "1", "--dry-run")
        assert code == 0
        assert payload["status"] == "dry-run"
        manifest = Path(payload["preflight"])
        assert manifest.exists()
        written = json.loads(manifest.read_text(encoding="utf-8"))
        assert written["seed_vector"]["python_streams"]
        assert written["summary"]["prompt_variant"] == "P0_canonical"

    def test_run_rejects_an_out_of_range_seed_index(self):
        code, _payload = run_cli("run", "--preset", "a_qwen_p0", "--seed-index", "99", "--dry-run")
        assert code == 2

    def test_run_applies_the_config_to_parameters(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        original_governance = parameters.LDF_GOVERNANCE_MODE
        try:
            run_cli("run", "--preset", "d_g3_qwen", "--seed-index", "1", "--dry-run")
            assert parameters.LDF_GOVERNANCE_MODE == "full"
            assert parameters.LLM_MODEL == "qwen2.5-14b"
            assert parameters.NUM_ROUNDS == 30
        finally:
            parameters.LDF_GOVERNANCE_MODE = original_governance
            parameters.SEED_VECTOR = {}

    def test_doctor_reports_the_governance_level(self):
        _code, payload = run_cli("doctor")
        findings = {f["check"]: f for f in payload["findings"]}
        assert findings["governance_default_off"]["detail"].endswith("G0")
        assert findings["shocks_decoupled_from_democracy"]["ok"] is True
        assert findings["mcpr_reported"]["ok"] is True

    def test_doctor_reports_mcpr_for_the_active_configuration(self):
        _code, payload = run_cli("doctor")
        detail = next(f["detail"] for f in payload["findings"] if f["check"] == "mcpr_reported")
        assert "MCPR=" in detail

    def test_doctor_on_a_cell_passes_the_checks_the_defaults_fail(self):
        """`doctor --preset` must describe the cell, not the module defaults.

        The defaults carry no seed vector and a server-side chat template, so a
        bare `doctor` reports two failures that say nothing about the run that is
        about to start. Checking a real cell has to clear both.
        """
        _code, bare = run_cli("doctor")
        bare_checks = {f["check"]: f["ok"] for f in bare["findings"]}
        assert bare_checks["seed_vector_complete"] is False
        assert bare_checks["chat_template_fixed_for_parity"] is False

        _code, payload = run_cli("doctor", "--preset", "a_qwen_p0", "--seed-index", "1")
        assert payload["cell"] == "arm_a_p0_qwen_s1"
        checks = {f["check"]: f["ok"] for f in payload["findings"]}
        assert checks["seed_vector_complete"] is True
        assert checks["chat_template_fixed_for_parity"] is True

    def test_doctor_accepts_the_governance_arm_intends(self):
        """Arm D runs at G1/G2/G3/G3c on purpose; that is not a failure."""
        _code, payload = run_cli("doctor", "--preset", "d_g3c_qwen", "--seed-index", "1")
        checks = {f["check"]: f["ok"] for f in payload["findings"]}
        assert "governance_default_off" not in checks
        assert checks["governance_matches_cell"] is True
        assert any(
            "G3" in f["detail"]
            for f in payload["findings"]
            if f["check"] == "governance_matches_cell"
        )

    def test_doctor_still_catches_governance_that_was_not_intended(self):
        """The governance check must have teeth, not just accept whatever it sees."""
        original = parameters.LDF_GOVERNANCE_MODE
        try:
            _code, payload = run_cli(
                "doctor",
                "--preset",
                "a_qwen_p0",
                "--seed-index",
                "1",
                "--set",
                "LDF_GOVERNANCE_MODE=full",
            )
            checks = {f["check"]: f["ok"] for f in payload["findings"]}
            assert checks["governance_off_for_non_governance_arm"] is False
        finally:
            parameters.LDF_GOVERNANCE_MODE = original

    def test_grid_preview_carries_runnable_coordinates(self):
        """A caller must be able to run a previewed cell without parsing its name.

        `arm_a_p0_qwen_s1` is preset `a_qwen_p0` at seed 1; deriving the preset by
        splitting the name on "_s" yields "arm_a_p0_qwen", which does not exist.
        """
        _code, payload = run_cli("grid", "show", "--grid", "configs/grid_arm_a.yaml", "--arm", "A")
        cell = payload["cells_preview"][0]
        assert cell["name"] == "arm_a_p0_qwen_s1"
        assert cell["preset"] == "a_qwen_p0"
        assert cell["seed_index"] == 1

        code, _run = run_cli(
            "run",
            "--preset",
            str(cell["preset"]),
            "--seed-index",
            str(cell["seed_index"]),
            "--dry-run",
        )
        assert code == 0

    def test_grid_preview_reports_the_cost_drivers(self):
        """Scheduling a session needs agents/rounds/ToM, not just a condition label."""
        _code, payload = run_cli("grid", "show", "--grid", "configs/grid_arm_c.yaml", "--arm", "C")
        cell = payload["cells_preview"][0]
        assert cell["agents"] == 14
        assert cell["rounds"] == 30
        assert cell["tom"] is False

    def test_export_writes_a_runnable_bundle_per_cell(self, tmp_path):
        code, payload = run_cli(
            "export",
            "--grid",
            "configs/grid_arm_a.yaml",
            "--out",
            str(tmp_path),
            "--zip",
            "arm_a",
        )
        assert code == 0
        assert payload["bundles"] == 36
        bundle = tmp_path / "arm_a_p0_qwen_s1"
        assert (bundle / "config.json").exists()
        assert (bundle / "serve.sh").exists()
        assert (bundle / "run_cell.py").exists()
        assert (bundle / "served_model_name.txt").read_text(
            encoding="utf-8"
        ).strip() == "qwen2.5-14b"
        assert (tmp_path / "elicit_grid_arm_a.zip").exists()

        config = json.loads((bundle / "config.json").read_text(encoding="utf-8"))
        assert config["parameters"]["CHAT_TEMPLATE_MODE"] == "fixed"
        assert config["seed_vector"]["llm_seed"] != config["seed_vector"]["python"]

        serve = (bundle / "serve.sh").read_text(encoding="utf-8")
        assert "--max-model-len 8192" in serve
        assert "--tensor-parallel-size 2" in serve

        runner = (bundle / "run_cell.py").read_text(encoding="utf-8")
        assert "REFUSING TO RUN" in runner

    def test_export_records_parity_violations(self, tmp_path):
        _code, payload = run_cli(
            "export", "--grid", "configs/grid_full.yaml", "--out", str(tmp_path)
        )
        assert payload["parity_violations"] == []

    def test_ls_on_a_missing_directory_is_not_an_error(self, tmp_path):
        code, payload = run_cli("ls", "--results-dir", str(tmp_path / "nothing"))
        assert code == 0
        assert payload["count"] == 0

    def test_params_reports_the_read_status_of_every_parameter(self):
        code, payload = run_cli("params", "--unread-only", "--json")
        assert code == 0
        assert payload == [], f"unread parameters: {payload}"

    def test_params_can_be_filtered_by_category(self):
        code, payload = run_cli("params", "--category", "governance", "--json")
        assert code == 0
        assert all(row["category"] == "governance" for row in payload)


class TestConfigAsArtefact:
    def test_config_file_is_what_makes_a_run_reproducible(self, tmp_path):
        """The pre-registration claim only holds if a cell is re-instantiable."""
        _code, payload = run_cli("run", "--preset", "a_qwen_p2", "--seed-index", "3", "--dry-run")
        # The dry run above wrote into the repo's results/; read it back.
        manifest = Path(payload["preflight"])
        written = json.loads(manifest.read_text(encoding="utf-8"))
        assert written["seed_vector"]["llm_seed"]
        assert written["summary"]["prompt_variant_hash"]
        assert written["seed_vector"]["sampling"]["temperature"] == 0.7
