"""Instrumentation that the manifest claims but the run previously under-delivered.

Two items from the revamp audit:

* item 6 — model provenance stopped at a Hub alias, which is a mutable pointer,
  so the commit sha is what identifies the weights actually served;
* item 8 — gossip exposure was logged as a bulletin length rather than the set
  each agent received, leaving the report's "certain vs possible exposure" bound
  in place of a measurement.
"""

from __future__ import annotations


class _StubAgent:
    """Just enough of an Agent for the gossip receipt."""

    def __init__(self, agent_id: int, recent_gossip: str = ""):
        self.agent_id = agent_id
        self.recent_gossip = recent_gossip


class TestGossipExposureIsMeasuredNotBounded:
    """Item 8: exposure was logged as a bulletin length, not what agents saw.

    `get_gossip_for_agent` withholds any item the receiver authored, so the old
    `saw_items=len(bulletin)` overstated exposure for every agent in the
    bulletin. The whole point of the item was to turn the report's
    "certain vs possible exposure" bound into an exact measurement.
    """

    @staticmethod
    def _bulletin():
        return [
            {"source": 0, "target": 1, "score": 2.0, "reasoning": "a"},
            {"source": 1, "target": 2, "score": 1.0, "reasoning": "b"},
            {"source": 2, "target": 0, "score": 3.0, "reasoning": "c"},
        ]

    def test_author_does_not_receive_own_item(self):
        from core.environment import Environment

        receipt = Environment._gossip_receipt(_StubAgent(0), self._bulletin())
        assert receipt["delivered_count"] == 2
        assert receipt["withheld_as_author"] == 1
        assert all(item["source"] != 0 for item in receipt["saw_items"])

    def test_receipt_names_the_actual_items(self):
        from core.environment import Environment

        receipt = Environment._gossip_receipt(_StubAgent(1), self._bulletin())
        assert {(i["source"], i["target"]) for i in receipt["saw_items"]} == {(0, 1), (2, 0)}
        assert receipt["saw_self_as_target"] is True

    def test_empty_bulletin_receives_nothing(self):
        from core.environment import Environment

        receipt = Environment._gossip_receipt(_StubAgent(0), [])
        assert receipt["delivered_count"] == 0
        assert receipt["saw_items"] == []
        assert receipt["saw_self_as_target"] is False


class TestCheckpointIdentityIsRecorded:
    """Item 6: a Hub alias is a mutable pointer, so the commit sha is the identity."""

    def test_unset_checkpoint_is_not_a_failure(self):
        from core.provenance import checkpoint_identity

        identity = checkpoint_identity("")
        assert identity["revision"] is None
        assert identity["resolved"] is True
        assert identity["source"] == "unset"

    def test_unreachable_checkpoint_reports_unresolved(self, monkeypatch):
        from core import provenance

        monkeypatch.setattr(provenance, "_cached_revision", lambda _name: None)
        monkeypatch.setattr(provenance, "_hub_revision", lambda _name: None)
        identity = provenance.checkpoint_identity("org/model")
        assert identity["resolved"] is False
        assert identity["source"] == "unresolved"

    def test_cached_revision_is_preferred(self, monkeypatch):
        from core import provenance

        monkeypatch.setattr(provenance, "_cached_revision", lambda _name: "abc123")
        monkeypatch.setattr(provenance, "_hub_revision", lambda _name: "should-not-be-used")
        identity = provenance.checkpoint_identity("org/model")
        assert identity["revision"] == "abc123"
        assert identity["source"] == "hf_cache"

    def test_manifest_carries_the_revision_fields(self):
        from core.provenance import inference_provenance

        model = inference_provenance()["model"]
        assert "checkpoint_revision" in model
        assert "checkpoint_revision_source" in model
        assert "checkpoint_revision_resolved" in model
