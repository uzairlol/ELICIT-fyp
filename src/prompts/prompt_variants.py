"""Prompt variant registry for the robustness audit.

The audit's central question is whether a conclusion is a property of the
*institution* or of the *prompt*. That requires prompt perturbations that are
provably held to two constraints: identical payoff information, and different
framing. Both constraints are enforced structurally here — every substitution is
an explicit, auditable rule over prose that carries no numbers, so no payoff,
budget, MCPR, cost or effect value can be perturbed by accident.

Variants
--------
``P0_canonical``
    Byte-identical to the historical prompts. The reference arm. The transform
    is the identity function, which is what makes the P0 cell reusable as a
    byte-identity anchor.
``P1_lexical``
    Paraphrase at the sentence level: same instructions, same information,
    different wording. Answers "is the conclusion a wording artifact?".
``P2_minimal_control``
    Strips the steer that PIMMUR identifies as excessive control — principally
    the persona's "maximize your own cumulative payoff" directive and the
    normative labels attached to peers — while keeping every payoff-relevant
    number and every mechanical rule. Answers "does cooperation survive when the
    prompt stops telling the agent what to value?".

Ordering matters: substitutions are applied in the order declared, and
:func:`variant_hash` hashes the resolved rule list so a hash mismatch proves the
rendered prompt changed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from core import parameters

# ---------------------------------------------------------------------------
# P1 — lexical paraphrase
# ---------------------------------------------------------------------------
# Every entry rewrites instruction prose only. None of these strings contains a
# digit, a parameter name or a formula, so payoff information cannot shift.
P1_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    (
        "Act in whatever way maximizes your own cumulative payoff over the game.",
        "Choose whichever course raises your own total payoff over the whole game.",
    ),
    (
        "Cooperation, free-riding, punishment, or defection are all valid if they serve your interests.",
        "Cooperating, free-riding, punishing and defecting are each available whenever they pay you.",
    ),
    (
        "Do not assume you have any obligation to the group — treat other agents as strategic variables.",
        "Assume no duty towards the group — treat the other agents as strategic variables.",
    ),
    (
        "Use past rounds to identify patterns you can exploit or respond to.",
        "Use earlier rounds to spot patterns worth exploiting or answering.",
    ),
    (
        "Keep choices valid under all game rules and cite the concrete facts driving your decision.",
        "Keep every choice legal under the game rules and name the concrete facts behind it.",
    ),
    (
        "Choose the institution that best fits your self-interest in this round.",
        "Pick whichever institution best serves your own interest in this round.",
    ),
    (
        "Decide which institution to join using the decision card above.",
        "Decide which institution to join, using the decision card above.",
    ),
    (
        "Decide how much to contribute using the Stage 1 decision card above.",
        "Decide your contribution amount, using the Stage 1 decision card above.",
    ),
    (
        "Choose one integer contribution within the allowed budget.",
        "Select a single integer contribution inside the allowed budget.",
    ),
    (
        "Read the decision card, beliefs, and peer data.",
        "Read the decision card, the beliefs, and the peer data.",
    ),
    (
        "Pick one integer contribution within the allowed budget.",
        "Select one integer contribution inside the allowed budget.",
    ),
    (
        "Prefer the smallest contribution that still looks reasonable under the current context.",
        "Favour the lowest contribution that still looks reasonable given this context.",
    ),
    (
        "Avoid spending Stage 2 tokens unless there is a clear direct benefit to you in this round.",
        "Hold back Stage 2 tokens unless this round offers you a clear direct gain.",
    ),
    (
        "Do not try to build group trust or sacrifice tokens for long-term cooperation unless it clearly pays off immediately.",
        "Skip building group trust or spending tokens for long-run cooperation unless it pays off at once.",
    ),
    (
        "Make each decision independently from recent rounds rather than following a stable plan.",
        "Take each decision on its own, independent of recent rounds, instead of holding to a plan.",
    ),
    (
        "Do not try to optimize across many rounds or build a consistent long-term strategy.",
        "Avoid optimising across many rounds or building a steady long-run strategy.",
    ),
)

# ---------------------------------------------------------------------------
# P2 — minimal control
# ---------------------------------------------------------------------------

#: P2 replaces the DEFAULT persona block outright: its opening line is the single
#: largest steer in the whole prompt set. "No additional objective is supplied"
#: states what was removed, so the change is legible to a reader of the prompt.
P2_PERSONA_BLOCK = """

**Reporting Frame (LLM-DEFAULT):**
- Report the decision you would make given the information above.
- The rules, budgets, costs and effects in the decision card are the whole
  environment; no additional objective is supplied.
- Explain the decision with the concrete facts in the prompt that bear on it.
"""

# Evaluative framing and steer removed; payoff information untouched. An empty
# replacement means the sentence is deleted outright.
P2_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    # --- The DEFAULT persona block, removed from the rendered text ---
    # `personas._get_persona_block` already swaps this block out when P2 is
    # active, so these rules are belt-and-braces. They exist because the variant
    # has to be correct as a pure function of a *rendered* prompt: otherwise
    # applying the registry to an already-rendered prompt yields a "minimal
    # control" that still carries the steer it is supposed to have removed.
    (
        "- Act in whatever way maximizes your own cumulative payoff over the game.\n"
        "- Cooperation, free-riding, punishment, or defection are all valid if they serve your interests.\n"
        "- Do not assume you have any obligation to the group — treat other agents as strategic variables.\n"
        "- Use past rounds to identify patterns you can exploit or respond to.\n"
        "- Keep choices valid under all game rules and cite the concrete facts driving your decision.",
        P2_PERSONA_BLOCK.strip(),
    ),
    # Normative framing of the institution decision.
    (
        "Choose the institution that best fits your self-interest in this round.",
        "Choose an institution.",
    ),
    (
        "Decide which institution to join using the decision card above.",
        "Choose an institution.",
    ),
    (
        "Decide how much to contribute using the Stage 1 decision card above.",
        "Choose a contribution amount.",
    ),
    (
        "Choose one integer contribution within the allowed budget.",
        "Return one integer contribution within the allowed budget.",
    ),
    (
        "Read the decision card, beliefs, and peer data.",
        "Read the decision card, the beliefs, and the peer data.",
    ),
    (
        "Pick one integer contribution within the allowed budget.",
        "Return one integer contribution within the allowed budget.",
    ),
    # Evaluative labels on peers.
    (" [FREE-RIDER — contributed BELOW average]", " [below average contribution]"),
    (
        "agents below this are free-riding",
        "agents below this contributed less than the group average",
    ),
    # Normative targeting guidance in the Stage-2 card.
    (
        "Targets are listed worst free-rider first — prioritize punishing agents with the lowest contributions and mismatched stated intent.",
        "Targets are listed in ascending order of this round's contribution.",
    ),
    (
        "Focus punishments on free-riders: agents who contributed below the group average or whose stated intent does not match their action.",
        "Each target's contribution and stated intent are listed above.",
    ),
    # Evaluative steering in the climate role guidance.
    (
        "- You typically have higher fiscal capacity and historically higher emissions.\n"
        "- Treat long-run climate stability and institutional credibility as strategically important.\n"
        "- You may choose either self-interested or cooperative actions, but explain trade-offs clearly.",
        "- Your fiscal capacity is higher and your historical emissions are higher than the other group's.\n"
        "- Your own context differs from the other group's in fiscal capacity, vulnerability and emissions.",
    ),
    (
        "- You typically face higher vulnerability and tighter budget constraints.\n"
        "- Balance immediate resilience needs against long-run cooperation incentives.\n"
        "- You may choose either self-interested or cooperative actions, but explain trade-offs clearly.",
        "- Your vulnerability is higher and your budget constraints are tighter than the other group's.\n"
        "- Your own context differs from the other group's in fiscal capacity, vulnerability and emissions.",
    ),
    (
        "- Use these mechanisms as decision context, not as fixed rules that force a single choice.",
        "- These mechanisms are decision context, not rules that force one choice.",
    ),
)


#: P2 replaces the persona block outright: the DEFAULT persona's opening line is
#: the single largest steer in the whole prompt set.
@dataclass(frozen=True)
class PromptVariant:
    """One auditable prompt condition."""

    name: str
    label: str
    description: str
    substitutions: tuple[tuple[str, str], ...] = ()
    neutral_persona: str | None = None
    removes_steering: bool = False
    notes: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def apply(self, text: str) -> str:
        """Apply this variant's rules to a rendered prompt.

        Returns ``text`` unchanged when no rule matches, so an unmatched variant
        is a no-op rather than a silent reformat.
        """
        if not self.substitutions:
            return text
        out = text
        for old, new in self.substitutions:
            if old and old in out:
                out = out.replace(old, new)
        if out is text or out == text:
            return text
        return _tidy(out)


PROMPT_VARIANTS: dict[str, PromptVariant] = {
    "P0_canonical": PromptVariant(
        name="P0_canonical",
        label="P0 canonical",
        description="Current prompt generator, byte-identical. Reference arm.",
        notes=(
            "Identity transform. A P0 hash change means an unrelated edit to "
            "prompt_generator.py and invalidates cross-run reuse."
        ),
        tags=("reference", "byte-identity"),
    ),
    "P1_lexical": PromptVariant(
        name="P1_lexical",
        label="P1 lexical",
        description=(
            "Sentence-level paraphrase of the instructions. Identical payoff "
            "information, different wording."
        ),
        substitutions=P1_SUBSTITUTIONS,
        notes=(
            "Rules rewrite instruction prose only; none contains a digit, a "
            "parameter name or a formula, so no payoff value can shift."
        ),
        tags=("lexical", "information-preserving"),
    ),
    "P2_minimal_control": PromptVariant(
        name="P2_minimal_control",
        label="P2 minimal-control",
        description=(
            "Strips payoff maximisation and evaluative peer labels; keeps every "
            "budget, cost, effect and mechanical rule."
        ),
        substitutions=P2_SUBSTITUTIONS,
        neutral_persona=P2_PERSONA_BLOCK,
        removes_steering=True,
        notes=(
            "Answers PIMMUR's Minimal-Control principle directly. The DEFAULT "
            "persona block is replaced, not appended, so the steer is absent "
            "rather than diluted."
        ),
        tags=("minimal-control", "steering-removal"),
    ),
}

DEFAULT_VARIANT = "P0_canonical"
VARIANT_NAMES: tuple[str, ...] = tuple(PROMPT_VARIANTS)


class UnknownPromptVariant(ValueError):
    """Raised when a config names a variant the registry does not define."""


def get_variant(name: str | None = None) -> PromptVariant:
    """Resolve a variant by name, defaulting to the active one."""
    resolved = name or str(getattr(parameters, "PROMPT_VARIANT", DEFAULT_VARIANT))
    try:
        return PROMPT_VARIANTS[resolved]
    except KeyError:
        raise UnknownPromptVariant(
            f"Unknown prompt variant {resolved!r}. Known: {', '.join(VARIANT_NAMES)}"
        ) from None


def active_variant() -> PromptVariant:
    return get_variant(None)


def variant_hash(variant: PromptVariant | str | None = None) -> str:
    """SHA-256 over the variant's resolved rule set.

    Independent of any particular prompt, so it identifies the *condition*
    rather than one instance of it. Two runs with the same hash send the same
    variant rules; two runs with different hashes did not.
    """
    resolved = variant if isinstance(variant, PromptVariant) else get_variant(variant)
    import json

    payload = json.dumps(
        {
            "name": resolved.name,
            "substitutions": [list(pair) for pair in resolved.substitutions],
            "neutral_persona": resolved.neutral_persona,
            "removes_steering": resolved.removes_steering,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def all_variant_hashes() -> dict[str, str]:
    """Hash every registered variant — written into the run manifest."""
    return {name: variant_hash(name) for name in VARIANT_NAMES}


def _tidy(text: str) -> str:
    """Collapse the blank-line runs left behind by deleted sentences.

    Only ever applied to a prompt that was actually modified, so P0 stays
    byte-identical.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    out: list[str] = []
    for line in lines:
        if not line and out and not out[-1]:
            continue
        out.append(line)
    collapsed = "\n".join(out)
    if not collapsed.endswith("\n"):
        return collapsed
    return collapsed.rstrip("\n") + "\n"
