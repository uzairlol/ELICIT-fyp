"""Prompt variants, chat templates and the analysis modules they feed.

The audit's validity rests on three claims that are only as good as their tests:

* P0 is byte-identical to the historical prompt, so it is a usable reference arm;
* P1 and P2 change *framing* without changing payoff information; and
* the chat template is rendered once, so the prompt is the same string across
  model families.

Plus the two analysis modules that turn the grid into claims: the Stage-1
best-response solver and the variance decomposition.
"""

from __future__ import annotations

import pytest

from core import parameters
from prompts.prompt_variants import (
    P1_SUBSTITUTIONS,
    P2_PERSONA_BLOCK,
    P2_SUBSTITUTIONS,
    PROMPT_VARIANTS,
    UnknownPromptVariant,
    active_variant,
    get_variant,
    variant_hash,
)

P0_PROMPT = """You are Agent 3. Round 7. Task: choose contribution amount. Institution: SI.

**Decision Snapshot:**
- Currency: million USD
- Current wealth: 412000.00 million USD

**Behavioral Persona (LLM-DEFAULT):**
- Act in whatever way maximizes your own cumulative payoff over the game.
- Cooperation, free-riding, punishment, or defection are all valid if they serve your interests.
- Do not assume you have any obligation to the group — treat other agents as strategic variables.
- Use past rounds to identify patterns you can exploit or respond to.
- Keep choices valid under all game rules and cite the concrete facts driving your decision.

**Decision Card — Stage 1 / Contribution**
- Institution: SI
- Contribution budget: 412000 million USD
- Group size: 12
- MCPR (marginal return to you per unit contributed): 0.1333 (group multiplier 1.6 split among 12 members)

Decide how much to contribute using the Stage 1 decision card above.
"""

P2_STEER_SENTENCES = (
    "maximizes your own cumulative payoff",
    "Treat other agents as strategic variables",
)


class TestCanonicalVariant:
    def test_p0_is_the_active_default(self):
        assert active_variant().name == "P0_canonical"

    def test_p0_transform_is_the_identity_function(self):
        assert get_variant("P0_canonical").apply(P0_PROMPT) == P0_PROMPT

    def test_p0_preserves_length_exactly(self):
        variant = get_variant("P0_canonical")
        assert len(variant.apply(P0_PROMPT)) == len(P0_PROMPT)


class TestLexicalVariant:
    def test_p1_changes_the_wording(self):
        rendered = get_variant("P1_lexical").apply(P0_PROMPT)
        assert rendered != P0_PROMPT

    def test_p1_replaces_the_persona_instructions(self):
        rendered = get_variant("P1_lexical").apply(P0_PROMPT)
        assert "Act in whatever way maximizes your own cumulative payoff" not in rendered
        assert "Choose whichever course raises your own total payoff" in rendered

    def test_p1_preserves_every_payoff_value(self):
        """Payoff information must be identical across P0 and P1.

        This is the whole claim of a lexical perturbation. If a rule ever rewrote a
        number, a budget or a formula, the arm would no longer be a
        wording test.
        """
        rendered = get_variant("P1_lexical").apply(P0_PROMPT)
        for token in (
            "412000.00 million USD",
            "Contribution budget: 412000 million USD",
            "Group size: 12",
            "0.1333",
            "group multiplier 1.6 split among 12 members",
        ):
            assert token in rendered, token

    def test_p1_rules_carry_no_payoff_numbers(self):
        """Structural guarantee: no lexical rule can perturb a numeric value.

        Digits are permitted only where they are part of a stage name ("Stage 1"),
        never as a value. What must not appear is a decimal or a ratio.
        """
        import re

        for old, new in P1_SUBSTITUTIONS:
            assert not re.search(r"\d+\.\d+", old), old
            assert not re.search(r"\d+\.\d+", new), new
            assert "%" not in old and "%" not in new
            assert "million" not in old and "million" not in new

    def test_p1_rules_are_not_no_ops(self):
        for old, new in P1_SUBSTITUTIONS:
            assert old != new, old

    def test_unmatched_variant_is_a_no_op(self):
        """A variant that matches nothing returns the text unchanged, not reflowed."""
        assert get_variant("P1_lexical").apply("nothing here to paraphrase") == (
            "nothing here to paraphrase"
        )


class TestMinimalControlVariant:
    def test_p2_strips_the_payoff_maximisation_directive(self):
        rendered = get_variant("P2_minimal_control").apply(P0_PROMPT)
        assert "Act in whatever way maximizes your own cumulative payoff" not in rendered

    def test_p2_replaces_the_persona_block_outright(self):
        rendered = get_variant("P2_minimal_control").apply(P0_PROMPT)
        assert "Treat other agents as strategic variables" not in rendered
        assert "no additional objective is supplied" in P2_PERSONA_BLOCK

    def test_p2_keeps_every_payoff_value(self):
        """Stripping the steer must not strip the environment."""
        rendered = get_variant("P2_minimal_control").apply(P0_PROMPT)
        for token in (
            "412000.00 million USD",
            "Contribution budget: 412000 million USD",
            "Group size: 12",
            "0.1333",
        ):
            assert token in rendered, token

    def test_p2_removes_evaluative_peer_labels(self):
        stage2 = (
            "- Agent 4, group=developing [FREE-RIDER — contributed BELOW average]: "
            "contrib=0, and agents below this are free-riding\n"
            "Focus punishments on free-riders: agents who contributed below the group "
            "average or whose stated intent does not match their action."
        )
        rendered = get_variant("P2_minimal_control").apply(stage2)
        assert "FREE-RIDER" not in rendered
        assert "are free-riding" not in rendered
        assert "Focus punishments on free-riders" not in rendered
        assert "below average contribution" in rendered

    def test_p2_removes_climate_role_steering(self):
        climate = """
**Climate Role Guidance (Developed Country):**
- You typically have higher fiscal capacity and historically higher emissions.
- Treat long-run climate stability and institutional credibility as strategically important.
- You may choose either self-interested or cooperative actions, but explain trade-offs clearly.
"""
        rendered = get_variant("P2_minimal_control").apply(climate)
        assert "Treat long-run climate stability" not in rendered
        assert "self-interested or cooperative" not in rendered
        # The factual, attributional part of the context survives.
        assert "fiscal capacity" in rendered
        assert "emissions" in rendered

    def test_p2_rules_contain_no_placeholder_tokens(self):
        """A rule holding an unrendered ``{placeholder}`` can never match."""
        for old, new in P2_SUBSTITUTIONS:
            assert "{" not in old, old
            assert "{" not in new, new

    def test_p2_is_marked_as_steering_removal(self):
        assert get_variant("P2_minimal_control").removes_steering is True
        assert get_variant("P0_canonical").removes_steering is False


class TestVariantRegistry:
    def test_unknown_variant_raises_with_the_menu(self):
        with pytest.raises(UnknownPromptVariant, match="P0_canonical"):
            get_variant("P3_imaginary")

    def test_hashes_are_distinct_and_stable(self):
        first = {name: variant_hash(name) for name in PROMPT_VARIANTS}
        second = {name: variant_hash(name) for name in PROMPT_VARIANTS}
        assert first == second
        assert len(set(first.values())) == len(PROMPT_VARIANTS)

    def test_active_variant_follows_the_parameter(self, monkeypatch):
        monkeypatch.setattr(parameters, "PROMPT_VARIANT", "P2_minimal_control", raising=False)
        assert active_variant().name == "P2_minimal_control"

    def test_every_variant_has_a_pinned_hash(self):
        """Changing a rule changes the hash, which is what the manifest records."""
        pinned = {
            "P0_canonical": "bf7daee099a0ac4884ff20445bf790418dd85a662e4f0a9713f21fc25661c7d7",
        }
        for name, expected in pinned.items():
            assert variant_hash(name) == expected


class TestChatTemplateParity:
    """Cross-model prompt parity only works if ELICIT owns the rendering."""

    def test_fixed_mode_is_required_for_cross_model_cells(self):
        from llm.chat_template import fixed_template_mode

        # The default stays "server" so enabling fixed mode is an explicit,
        # recorded choice rather than a silent transport change.
        assert parameters.CHAT_TEMPLATE_MODE == "server"
        assert fixed_template_mode() is False

    def test_every_registered_template_renders_the_prompt_body(self):
        from llm.chat_template import render_chat

        for name in ("chatml", "llama3", "mistral"):
            rendered = render_chat(P0_PROMPT, name)
            assert P0_PROMPT in rendered
            assert rendered.strip()

    def test_render_is_deterministic(self):
        from llm.chat_template import render_chat

        assert render_chat(P0_PROMPT, "chatml") == render_chat(P0_PROMPT, "chatml")

    def test_chatml_open_and_close_tokens_are_present(self):
        from llm.chat_template import render_chat

        rendered = render_chat("Hi", "chatml")
        # Three control tokens (open, close, generation prompt), two pipes each.
        # Counted by codepoint because the literal sequence does not survive
        # copy-paste through every tool.
        assert rendered.count(chr(124)) == 6

    def test_mistral_template_uses_inst_delimiters(self):
        from llm.chat_template import render_chat

        assert render_chat("Hi", "mistral") == "[INST] Hi [/INST]"

    def test_unknown_template_raises(self):
        from llm.chat_template import UnknownTemplate, render_chat

        with pytest.raises(UnknownTemplate):
            render_chat("Hi", "gemma9")

    def test_template_fingerprint_is_stable(self):
        from llm.chat_template import template_fingerprint

        assert template_fingerprint("chatml") == template_fingerprint("chatml")
        assert template_fingerprint("chatml") != template_fingerprint("llama3")


class TestBestResponseSolver:
    """MCPR < 1 makes zero a strict best response; the solver must say so."""

    def test_historical_condition_gives_zero_as_the_best_response(self):
        from analysis.best_response import Stage1Game

        game = Stage1Game(
            beta=1.6, group_size=12, peer_contributions=1_000_000.0, floor=1_000_000.0
        )
        assert game.mcpr == pytest.approx(1.6 / 12)
        assert game.best_response() == 0.0

    def test_below_threshold_contributing_costs_payoff(self):
        from analysis.best_response import Stage1Game

        game = Stage1Game(beta=1.6, group_size=12, peer_contributions=0.0, floor=1_000_000.0)
        assert game.stage1_payoff(1_000.0) < game.stage1_payoff(0.0)

    def test_above_threshold_the_cap_is_the_best_response(self):
        from analysis.best_response import Stage1Game

        game = Stage1Game(beta=20.0, group_size=14, peer_contributions=0.0, floor=1_000.0)
        assert game.mcpr > 1.0
        assert game.best_response() == game.cap == 1_000.0

    def test_at_the_threshold_the_cap_is_still_best(self):
        from analysis.best_response import Stage1Game

        game = Stage1Game(beta=14.0, group_size=14, peer_contributions=0.0, floor=1_000.0)
        assert game.mcpr == pytest.approx(1.0)
        assert game.best_response() == game.cap

    def test_payoff_is_flat_in_the_choice_at_the_threshold(self):
        """MCPR = 1 makes the agent indifferent, which is the canonical threshold.

        The agent's own contribution enters the public good it consumes, so
        ``d pi / d c = MCPR - 1 = 0`` here and every action in ``[0, cap]`` earns
        the same payoff. This is exactly why the sweep brackets MCPR = 1.
        """
        from analysis.best_response import Stage1Game

        game = Stage1Game(beta=14.0, group_size=14, peer_contributions=0.0, floor=1_000.0)
        assert game.stage1_payoff(0.0) == pytest.approx(game.stage1_payoff(1_000.0))

    def test_slope_below_and_above_the_threshold(self):
        from analysis.best_response import Stage1Game

        below = Stage1Game(beta=1.6, group_size=12, peer_contributions=0.0, floor=1_000.0)
        assert below.marginal_return() < 0
        above = Stage1Game(beta=20.0, group_size=14, peer_contributions=0.0, floor=1_000.0)
        assert above.marginal_return() > 0
        assert above.marginal_return() == pytest.approx(above.mcpr - 1.0)

    def test_own_contribution_enters_the_public_good(self):
        """The derivative must be MCPR - 1, not -1.

        Reproducing ``-1`` would make MCPR irrelevant and would quietly rebuild
        the exact error the best-response comparison exists to expose.
        """
        from analysis.best_response import Stage1Game

        game = Stage1Game(beta=20.0, group_size=14, peer_contributions=0.0, floor=1_000.0)
        delta = game.stage1_payoff(100.0) - game.stage1_payoff(0.0)
        assert delta == pytest.approx(100.0 * (game.mcpr - 1.0))

    def test_contribution_cannot_exceed_the_cap(self):
        from analysis.best_response import Stage1Game

        game = Stage1Game(
            beta=40.0, group_size=14, peer_contributions=0.0, capacity=0.1, floor=1_000_000.0
        )
        assert game.stage1_payoff(999_999.0) == pytest.approx(game.stage1_payoff(game.cap))

    def test_iteration_agrees_with_the_closed_form(self):
        from analysis.best_response import Stage1Game, best_response_by_iteration

        for beta, group_size in ((1.6, 12), (20.0, 14), (14.0, 14)):
            game = Stage1Game(
                beta=beta, group_size=group_size, peer_contributions=5_000.0, floor=1_000_000.0
            )
            result = best_response_by_iteration(game)
            assert result["agrees"], (beta, group_size)
            assert result["iterated"] == result["closed_form"]

    def test_capacity_scales_the_cap(self):
        from analysis.best_response import Stage1Game

        game = Stage1Game(
            beta=40.0, group_size=14, peer_contributions=0.0, capacity=0.10, floor=1_000_000.0
        )
        assert game.cap == pytest.approx(100_000.0)


class TestVarianceDecomposition:
    def _frame(self):
        import pandas as pd

        rows = []
        # Deliberate structure: model and prompt dominate, seed barely moves.
        for model, model_effect in (("qwen", 0.60), ("llama", 0.40), ("mistral", 0.20)):
            for prompt, prompt_effect in (("P0", 0.30), ("P2", 0.10)):
                for seed in range(4):
                    rows.append(
                        {
                            "run": f"{model}_{prompt}_{seed}",
                            "model": model,
                            "prompt_variant": prompt,
                            "condition": "full",
                            "seed": f"{model}_{prompt}_{seed}",
                            "y": model_effect + prompt_effect + seed * 0.001,
                        }
                    )
        return pd.DataFrame(rows)

    def test_shares_sum_to_one(self):
        from analysis.variance import variance_decomposition

        result = variance_decomposition(self._frame(), "y")
        assert sum(result["variance_shares"].values()) == pytest.approx(1.0, abs=1e-9)

    def test_model_and_prompt_dominate_the_designed_variance(self):
        from analysis.variance import variance_decomposition

        result = variance_decomposition(self._frame(), "y")
        assert result["variance_shares"]["model"] > result["variance_shares"]["seed"]

    def test_artifact_test_fires_when_the_instrument_dominates(self):
        from analysis.variance import variance_decomposition

        result = variance_decomposition(self._frame(), "y")
        assert result["artifact_threshold_exceeded"] is True
        assert "instrument" in result["interpretation"].lower()

    def test_pure_noise_is_not_an_artifact(self):
        import pandas as pd

        from analysis.variance import variance_decomposition

        rows = [
            {
                "run": f"m{p}_v{v}_s{s}",
                "model": f"m{p}",
                "prompt_variant": f"v{v}",
                "condition": "full",
                "seed": f"m{p}_v{v}_s{s}",
                "y": ((s * 37) % 11) / 100.0,
            }
            for p in range(3)
            for v in range(2)
            for s in range(4)
        ]
        result = variance_decomposition(pd.DataFrame(rows), "y")
        assert result["artifact_threshold_exceeded"] is False

    def test_inference_is_at_the_run_level_not_the_row_level(self):
        """Pooled agent-rounds are not replications; the decomposition must not use them."""
        import pandas as pd

        from analysis.variance import variance_decomposition

        rows = []
        for seed in range(4):
            for _ in range(20):  # twenty agent-rounds per run
                rows.append(
                    {
                        "run": f"s{seed}",
                        "model": "qwen",
                        "prompt_variant": "P0",
                        "condition": "full",
                        "seed": f"s{seed}",
                        "y": 0.5 + seed * 0.01,
                    }
                )
        result = variance_decomposition(pd.DataFrame(rows), "y")
        assert result["n_runs"] == 4

    def test_empty_frame_is_an_error_not_a_zero(self):
        import pandas as pd

        from analysis.variance import VarianceDecompositionError, variance_decomposition

        with pytest.raises(VarianceDecompositionError):
            variance_decomposition(pd.DataFrame(), "y")

    def test_missing_column_is_reported(self):
        import pandas as pd

        from analysis.variance import VarianceDecompositionError, variance_decomposition

        with pytest.raises(VarianceDecompositionError, match="missing columns"):
            variance_decomposition(pd.DataFrame({"run": ["a", "b"], "y": [1.0, 2.0]}), "y")

    def test_mcpr_curve_brackets_the_threshold(self):
        import pandas as pd

        from analysis.variance import mcpr_response_curve

        rows = [
            {
                "run": f"r{i}",
                "beta": beta,
                "group_size": 14,
                "contribution_intensity": 0.0,
                "participation_rate": rate,
            }
            for i, (beta, rate) in enumerate([(0.4, 0.9), (1.6, 0.9), (14.0, 0.2), (20.0, 0.1)])
        ]
        curve = mcpr_response_curve(pd.DataFrame(rows))
        assert len(curve) == 4
        assert curve["above_threshold"].sum() == 2
        assert list(curve["mcpr"]) == sorted(curve["mcpr"])

    def test_threshold_discontinuity_is_detected(self):
        import pandas as pd

        from analysis.variance import mcpr_response_curve, threshold_discontinuity

        rows = [
            {
                "run": f"r{i}",
                "beta": beta,
                "group_size": 14,
                "contribution_intensity": 0.0,
                "participation_rate": rate,
            }
            for i, (beta, rate) in enumerate([(0.4, 0.90), (1.6, 0.90), (14.0, 0.20), (20.0, 0.15)])
        ]
        curve = mcpr_response_curve(pd.DataFrame(rows))
        result = threshold_discontinuity(curve, "participation_rate")
        assert result["n_below"] == 2 and result["n_above"] == 2
        assert result["difference"] < -0.5
        assert result["discontinuity"] is True

    def test_no_discontinuity_when_participation_is_flat(self):
        import pandas as pd

        from analysis.variance import mcpr_response_curve, threshold_discontinuity

        rows = [
            {
                "run": f"r{i}",
                "beta": beta,
                "group_size": 14,
                "contribution_intensity": 0.0,
                "participation_rate": 0.5,
            }
            for i, beta in enumerate([0.4, 1.6, 14.0, 20.0])
        ]
        curve = mcpr_response_curve(pd.DataFrame(rows))
        assert threshold_discontinuity(curve, "participation_rate")["discontinuity"] is False
