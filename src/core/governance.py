"""Endogenous redistribution: elected rule, payout board, peer adjudication.

The LDF's allocation rule was a hardcoded constant. These three mechanisms make
it endogenous at escalating levels, all gated on ``LDF_GOVERNANCE_MODE``:

======  ==========================  =======  ====================================
Level   Mechanism                    Calls    Allocative authority held by agents
======  ==========================  =======  ====================================
G0      today's hardcoded arithmetic 0        none
G1      D4 constitutional election   0        which rule governs
G2      D4 + D5 payout board         12       which rule, and each payout
G3      D4 + D5 + D6 claim filing    52       which rule, each payout, and
                                                     who is eligible at all
G3c     D6 machinery, accept-all     40       eligibility uncontested (control)
======  ==========================  =======  ====================================

Cost control is the point: D4 is free, because it rides the constitutional
session that already runs six times per run. The 30 extra runs cost far more
than the mechanisms do.

G3c exists because of a specific referee objection. Once eligibility becomes
contestable, "the board rejected genuine free-riders" and "the board is biased
against developing agents" are observationally identical. Without an accept-all
control, G3's headline number — the rejection rate — means nothing.
"""

from __future__ import annotations

import logging
import statistics
from typing import Any

from core import parameters
from core.allocation_rules import default_eligibility, resolve_rule
from core.utils import robust_json_loads
from llm.retry import build_failure_retry_prompt, request_with_retries

logger = logging.getLogger(__name__)

#: Adjudicator verdict vocabulary. Reason codes are the diagnostic; the verdict
#: itself is not, because rejection incidence must never be folded into a
#: free-riding rate.
VERDICTS = ("accept", "reject", "abstain")

REASON_CODES = (
    "damage_substantiated",
    "damage_inflated",
    "no_mitigation_attempted",
    "mitigation_documented",
    "insufficient_evidence",
    "duplicate_claim",
    "out_of_scope",
    "other",
)


#: Governance mode -> (level label, elects rule, uses board, adjudicates claims).
GOVERNANCE_LEVELS: dict[str, tuple[str, bool, bool, bool]] = {
    "fixed": ("G0", False, False, False),
    "election": ("G1", True, False, False),
    "election+board": ("G2", True, True, False),
    "full": ("G3", True, True, True),
}


class GovernanceMode:
    """Parsed view of ``LDF_GOVERNANCE_MODE``."""

    __slots__ = ("adjudicates_claims", "elects_rule", "level", "mode", "uses_board")

    def __init__(self, mode: str | None = None) -> None:
        resolved = str(mode or getattr(parameters, "LDF_GOVERNANCE_MODE", "fixed"))
        level, self.elects_rule, self.uses_board, self.adjudicates_claims = GOVERNANCE_LEVELS.get(
            resolved, GOVERNANCE_LEVELS["fixed"]
        )
        self.mode = resolved if resolved in GOVERNANCE_LEVELS else "fixed"
        self.level = level

    @property
    def enabled(self) -> bool:
        return self.mode != "fixed"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"GovernanceMode({self.mode!r} -> {self.level})"


def governance_level() -> str:
    """``G0``/``G1``/``G2``/``G3`` for the active mode."""
    return GovernanceMode().level


def board_uses_discretion() -> bool:
    return GovernanceMode().uses_board and resolve_rule().board_discretion


def _sampling(api_client, temperature: float, top_p: float) -> dict[str, Any]:
    return {
        "model_name": api_client.deployment_name,
        "temperature": temperature,
        "top_p": top_p,
        "response_format": {"type": "json_object"},
        "seed": int(getattr(parameters, "LLM_SEED", parameters.SEED)),
    }


def rotate_board(agents, round_number: int) -> list[Any]:
    """Pick the board for a shock round, rotating the seats deterministically.

    Default composition is 3 developed + 3 developing, which keeps the board from
    being captured by either group and makes a group-skewed verdict visible.
    Rotation is by round, not by a random draw, so the board is a function of the
    run and therefore reproducible from the seed vector.
    """
    developed = [a for a in agents if getattr(a, "agent_group", None) == "developed"]
    developing = [a for a in agents if getattr(a, "agent_group", None) != "developed"]
    dev_seats = int(getattr(parameters, "LDF_BOARD_DEVELOPED_SEATS", 3))
    devg_seats = int(getattr(parameters, "LDF_BOARD_DEVELOPING_SEATS", 3))
    if not developed or not developing or dev_seats + devg_seats <= 0:
        return []

    def rotate(pool: list[Any], seats: int) -> list[Any]:
        if not pool or seats <= 0:
            return []
        offset = (round_number - 1) % len(pool)
        rotated = pool[offset:] + pool[:offset]
        return rotated[: min(seats, len(rotated))]

    return rotate(developed, dev_seats) + rotate(developing, devg_seats)


# ---------------------------------------------------------------------------
# D5 — payout board
# ---------------------------------------------------------------------------


def run_payout_board(api_client, agents, round_number: int, damages, pool_balance: float):
    """Ask each board member for a full allocation vector; keep the elementwise median.

    One structured call per board member, not one call per claimant: the median
    over members is robust to a single outlier and needs no extra tally call.
    With 6 rotating members and 2 shock rounds that is 12 calls per run, 0.5% of
    a ToM-off baseline.

    Returns ``(allocation, record)``; ``allocation`` is ``None`` when the level
    is off or the pool is empty.
    """
    if not api_client or pool_balance <= 0.0:
        return None, None
    if not GovernanceMode().uses_board:
        return None, None

    rule_name = str(getattr(parameters, "LDF_ALLOCATION_RULE", "damage_proportional"))
    claimants = default_eligibility(agents)
    claim_rows = "\n".join(
        f"  Agent {cid}: damage = {max(0.0, float(damages.get(cid, 0.0))):,.0f}, "
        f"group = {getattr(next((a for a in agents if a.agent_id == cid), object), 'agent_group', '?')}"
        for cid in claimants
    )
    coverage = float(getattr(parameters, "LDF_MAX_COVERAGE", 0.9))
    board = rotate_board(agents, round_number)
    if not board:
        return None, None

    members = ", ".join(f"Agent {a.agent_id}" for a in board)
    prompt = f"""You are a member of the Loss & Damage Fund payout board after Round {round_number}.

Pool available: {pool_balance:,.0f}
Current allocation rule in force: {rule_name}
Maximum coverage: an agent can receive at most {coverage:.0%} of the damage it suffered.

Damaged claimants:
{claim_rows}

Board members (you are one of them): {members}

Task: allocate the pool across the damaged claimants. Return the FULL allocation vector,
covering every listed claimant. The amounts must sum to at most the pool. The allocations
are checked against the coverage cap, and the median across board members is what is paid,
so a single extreme proposal will not survive on its own.

Respond ONLY with valid JSON:
{{
  "allocations": {{"Agent 12": <amount>, "Agent 13": <amount>}},
  "justifications": {{"Agent 12": "<one short sentence>", "Agent 13": "<one short sentence>"}}
}}"""

    def parse(raw):
        parsed = robust_json_loads(raw)
        return parsed if isinstance(parsed, dict) else None

    def validate(parsed):
        if parsed is None or "allocations" not in parsed:
            return "response must contain an 'allocations' object"
        allocations = parsed.get("allocations")
        if not isinstance(allocations, dict):
            return "'allocations' must be a JSON object of Agent label -> amount"
        allowed = {f"Agent {cid}" for cid in claimants}
        for key in allocations:
            if str(key) not in allowed:
                return f"unknown claimant label {key!r}; allowed labels are {sorted(allowed)}"
        return ""

    proposals: dict[int, dict[int, float]] = {}
    justifications: dict[int, dict[str, str]] = {}
    for member in board:
        # Mark the member so self-allocation can be stripped before use.
        member.board_member_allocating = True
        try:
            _response, parsed = request_with_retries(
                api_client,
                base_prompt=prompt,
                parse_response=parse,
                validate_result=validate,
                request_kwargs=_sampling(api_client, 0.3, 0.9),
                max_attempts=int(getattr(parameters, "LLM_DECISION_MAX_ATTEMPTS", 2)),
                label=f"Board member {member.agent_id} payout allocation",
                retry_prompt_factory=lambda base, _attempt, error: build_failure_retry_prompt(
                    base,
                    "Payout Board Allocation",
                    error,
                    fix_guidance=(
                        'Return {"allocations": {"Agent <id>": <amount>, ...}, '
                        '"justifications": {"Agent <id>": "<one short sentence>", ...}}.'
                    ),
                ),
                logger=logger,
            )
        finally:
            member.board_member_allocating = False
        proposals[member.agent_id] = _coerce_allocations(parsed.get("allocations"), claimants)
        justifications[member.agent_id] = parsed.get("justifications") or {}

    allocation = _elementwise_median(proposals, claimants)
    record = {
        "round": round_number,
        "rule": rule_name,
        "pool": pool_balance,
        "board": [a.agent_id for a in board],
        "proposals": proposals,
        "justifications": justifications,
        "median_allocation": allocation,
        "mechanism": "elementwise median across board members",
    }
    return allocation, record


def _coerce_allocations(raw, claimants) -> dict[int, float]:
    """Map 'Agent N' labels onto ids and drop anything unrecognised."""
    allowed = {int(cid) for cid in claimants}
    out: dict[int, float] = {}
    for key, value in (raw or {}).items():
        text = str(key).strip()
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            continue
        cid = int(digits)
        if cid not in allowed:
            continue
        try:
            out[cid] = max(0.0, float(value))
        except (TypeError, ValueError):
            continue
    return out


def _elementwise_median(proposals: dict[int, dict[int, float]], claimants) -> dict[int, float]:
    """Median of each claimant's proposed amount across board members."""
    out: dict[int, float] = {}
    for cid in claimants:
        values = [proposals[member].get(cid, 0.0) for member in proposals if member in proposals]
        if values:
            out[cid] = float(statistics.median(values))
    return out


# ---------------------------------------------------------------------------
# D6 — peer-adjudicated claims
# ---------------------------------------------------------------------------


def collect_claims(api_client, agents, round_number: int, damages) -> dict[int, dict[str, Any]]:
    """Each eligible agent files one claim per shock round.

    14 filings x 2 shocks = 28 calls per run. The filing cost is unavoidable
    once eligibility is contestable; the adjudication cost is a design choice.
    """
    claimants = default_eligibility(agents)
    claims: dict[int, dict[str, Any]] = {}
    if not api_client:
        return claims

    agents_by_id = {int(a.agent_id): a for a in agents}
    for claimant_id in claimants:
        agent = agents_by_id.get(claimant_id)
        reported = max(0.0, float(damages.get(claimant_id, 0.0)))
        prompt = f"""You are Agent {claimant_id}, filing a Loss & Damage claim after Round {round_number}.

The shock caused you {reported:,.0f} in damage. Your recorded wealth is
{getattr(agent, "wealth", 0.0):,.0f}.

Task: file your claim. State the damage you sustained and what mitigation you attempted
before or after the shock.

Respond ONLY with valid JSON:
{{
  "damage_claimed": <number>,
  "mitigation_attempted": "<one short sentence>",
  "reason_code": "<one of: {", ".join(REASON_CODES)}>"
}}"""

        def parse(raw):
            parsed = robust_json_loads(raw)
            return parsed if isinstance(parsed, dict) else None

        def validate(parsed):
            if parsed is None or "damage_claimed" not in parsed:
                return "response must contain 'damage_claimed'"
            try:
                float(parsed["damage_claimed"])
            except (TypeError, ValueError):
                return "damage_claimed must be numeric"
            return ""

        try:
            _response, parsed = request_with_retries(
                api_client,
                base_prompt=prompt,
                parse_response=parse,
                validate_result=validate,
                request_kwargs=_sampling(api_client, 0.3, 0.9),
                max_attempts=int(getattr(parameters, "LLM_DECISION_MAX_ATTEMPTS", 2)),
                label=f"Agent {claimant_id} LDF claim",
                retry_prompt_factory=lambda base, _attempt, error: build_failure_retry_prompt(
                    base,
                    "LDF Claim",
                    error,
                    fix_guidance=(
                        'Return {"damage_claimed": <number>, "mitigation_attempted": '
                        '"<one short sentence>", "reason_code": "<one of '
                        f"{', '.join(REASON_CODES)}>" + '"}.'
                    ),
                ),
                logger=logger,
            )
            claims[claimant_id] = {
                "damage_claimed": float(parsed["damage_claimed"]),
                "mitigation_attempted": str(parsed.get("mitigation_attempted", ""))[:200],
                "reason_code": str(parsed.get("reason_code", "other")),
                "mechanically_recorded_damage": reported,
            }
        except Exception as exc:
            logger.warning("Agent %s claim failed: %s", claimant_id, exc)
            claims[claimant_id] = {
                "damage_claimed": reported,
                "mitigation_attempted": "",
                "reason_code": "insufficient_evidence",
                "mechanically_recorded_damage": reported,
                "filing_failed": True,
            }
    return claims


def adjudicate_claims(
    api_client,
    agents,
    round_number: int,
    claims: dict[int, dict[str, Any]],
    damages,
) -> tuple[list[int], dict[str, Any]]:
    """Each adjudicator returns ONE verdict map over all claims, in a single call.

    One call per adjudicator per shock round — 6 calls, 12 per run — rather than
    one call per claim, which would be 84 calls per round. The per-claim design is
    also epistemically worse: an adjudicator judging claims one at a time never
    has to compare them, and comparison is the whole task.

    Returns ``(accepted_ids, record)``.
    """
    claimants = sorted(claims)
    record: dict[str, Any] = {
        "round": round_number,
        "claimants": claimants,
        "claims": claims,
        "verdicts_by_adjudicator": {},
        "acceptance_threshold": float(getattr(parameters, "LDF_CLAIM_ACCEPT_FRACTION", 2 / 3)),
        "forced_accept": bool(getattr(parameters, "LDF_BOARD_ALWAYS_ACCEPTS", False)),
    }
    if not claimants or not api_client:
        return list(claimants), record

    forced = bool(getattr(parameters, "LDF_BOARD_ALWAYS_ACCEPTS", False))
    if forced:
        # G3c control: the machinery runs, the verdicts are pre-determined.
        record["verdicts_by_adjudicator"] = {
            agent.agent_id: dict.fromkeys(claimants, "accept") for agent in agents
        }
        accepted = list(claimants)
        record["accepted"] = accepted
        record["rejection_incidence"] = 0.0
        return accepted, record

    board = rotate_board(agents, round_number)
    if not board:
        board = list(agents)[:6]

    claim_rows = "\n".join(
        f"  Agent {cid}: claimed {claims[cid]['damage_claimed']:,.0f} "
        f"(recorded {claims[cid].get('mechanically_recorded_damage', 0.0):,.0f}); "
        f'mitigation: "{claims[cid].get("mitigation_attempted", "")}"'
        for cid in claimants
    )
    adjudicators = ", ".join(f"Agent {a.agent_id}" for a in board)
    prompt = f"""You are adjudicating Loss & Damage claims after Round {round_number}.

All filed claims (compare them against each other before deciding):
{claim_rows}

Adjudicators: {adjudicators}

Task: rule on EVERY claim listed above in one verdict map. Use "accept", "reject" or
"abstain" per claimant, with a reason code from: {", ".join(REASON_CODES)}.

Respond ONLY with valid JSON:
{{
  "verdicts": {{"Agent 12": {{"verdict": "accept", "reason_code": "damage_substantiated"}}, ...}},
  "summary": "<one sentence>"
}}"""

    def parse(raw):
        parsed = robust_json_loads(raw)
        return parsed if isinstance(parsed, dict) else None

    def validate(parsed):
        if parsed is None or not isinstance(parsed.get("verdicts"), dict):
            return "response must contain a 'verdicts' object"
        for key, value in parsed["verdicts"].items():
            if not isinstance(value, dict):
                return f"verdict for {key!r} must be an object with 'verdict' and 'reason_code'"
            if str(value.get("verdict", "")).lower() not in VERDICTS:
                return f"verdict for {key!r} must be one of {', '.join(VERDICTS)}"
        return ""

    verdicts_by_adjudicator: dict[int, dict[str, str]] = {}
    for adjudicator in board:
        try:
            _response, parsed = request_with_retries(
                api_client,
                base_prompt=prompt,
                parse_response=parse,
                validate_result=validate,
                request_kwargs=_sampling(api_client, 0.2, 0.9),
                max_attempts=int(getattr(parameters, "LLM_DECISION_MAX_ATTEMPTS", 2)),
                label=f"Adjudicator {adjudicator.agent_id} verdict map",
                retry_prompt_factory=lambda base, _attempt, error: build_failure_retry_prompt(
                    base,
                    "Claim Adjudication",
                    error,
                    fix_guidance=(
                        'Return {"verdicts": {"Agent <id>": {"verdict": "accept|reject|abstain", '
                        '"reason_code": "<code>"}, ...}, "summary": "<one sentence>"}.'
                    ),
                ),
                logger=logger,
            )
            verdicts_by_adjudicator[adjudicator.agent_id] = {
                str(key): str(value.get("verdict", "abstain")).lower()
                for key, value in parsed["verdicts"].items()
            }
        except Exception as exc:
            logger.warning("Adjudicator %s failed: %s", adjudicator.agent_id, exc)
            verdicts_by_adjudicator[adjudicator.agent_id] = {}

    threshold = float(getattr(parameters, "LDF_CLAIM_ACCEPT_FRACTION", 2 / 3))
    n_adjudicators = max(1, len(verdicts_by_adjudicator))
    accept_counts = {
        cid: sum(1 for v in verdicts_by_adjudicator.values() if v.get(f"Agent {cid}") == "accept")
        for cid in claimants
    }
    # An abstention never counts toward acceptance, so a panel that splits its
    # abstentions cannot manufacture a payout by never voting.
    accepted = [cid for cid in claimants if accept_counts[cid] / n_adjudicators >= threshold]

    record["verdicts_by_adjudicator"] = verdicts_by_adjudicator
    record["accept_counts"] = accept_counts
    record["adjudicators"] = [a.agent_id for a in board]
    record["accepted"] = accepted
    record["rejection_incidence"] = 1.0 - (len(accepted) / len(claimants)) if claimants else 0.0
    return accepted, record


# ---------------------------------------------------------------------------
# D4 — constitutional election of the rule
# ---------------------------------------------------------------------------


def apply_elected_rule(fund, proposal: dict | None, round_number: int) -> bool:
    """Route a winning categorical proposal to the fund. Numeric rules are ignored.

    D4 costs zero extra LLM calls: the categorical branch rides the constitutional
    session that already runs, and the tally logic is untouched.
    """
    if not proposal:
        return False
    if str(proposal.get("rule")) != "LDF_ALLOCATION_RULE":
        return False
    rule_name = str(proposal.get("new_value") or "")
    resolved = resolve_rule(rule_name).name if rule_name else None
    if not resolved:
        return False
    return bool(fund.set_elected_rule(resolved, round_number=round_number))
