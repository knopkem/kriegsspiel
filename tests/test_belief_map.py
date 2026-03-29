"""Tests for the AI belief map (fog-of-war inference, D10)."""

import unittest

from ai.belief import BeliefMap, EnemyBelief
from core.fog_of_war import LastKnownEnemy
from core.map import HexCoord
from core.units import Side


class _FakeVisibility:
    """Minimal VisibilitySnapshot stand-in for tests."""

    def __init__(
        self,
        visible: dict[str, HexCoord] | None = None,
        last_known: dict[str, "LastKnownEnemy"] | None = None,
    ) -> None:
        self.visible_enemy_units: list[str] = list((visible or {}).keys())
        self.last_known_enemies: dict[str, LastKnownEnemy] = last_known or {}
        self._visible = visible or {}


class BeliefMapTestCase(unittest.TestCase):
    def _last_known(self, unit_id: str, q: int, r: int, turn: int) -> LastKnownEnemy:
        return LastKnownEnemy(unit_id=unit_id, position=HexCoord(q, r), seen_on_turn=turn)

    def test_update_creates_belief_from_last_known(self) -> None:
        bm = BeliefMap()
        vis = _FakeVisibility(
            last_known={"e1": self._last_known("e1", 5, 5, 1)}
        )
        bm.update(vis, current_turn=1)
        beliefs = bm.estimated_enemies(min_confidence=0.0)
        self.assertEqual(len(beliefs), 1)
        self.assertEqual(beliefs[0].unit_id, "e1")

    def test_confidence_decays_over_time(self) -> None:
        bm = BeliefMap()
        vis = _FakeVisibility(last_known={"e1": self._last_known("e1", 5, 5, 1)})
        bm.update(vis, current_turn=1)
        conf_t1 = bm.estimated_enemies(min_confidence=0.0)[0].confidence

        # Update with no sightings for several turns
        empty_vis = _FakeVisibility()
        bm.update(empty_vis, current_turn=5)
        beliefs = bm.estimated_enemies(min_confidence=0.0)
        if beliefs:
            conf_t5 = beliefs[0].confidence
            self.assertLess(conf_t5, conf_t1)

    def test_min_confidence_filter(self) -> None:
        bm = BeliefMap()
        vis = _FakeVisibility(last_known={"e1": self._last_known("e1", 5, 5, 1)})
        bm.update(vis, current_turn=1)
        all_beliefs = bm.estimated_enemies(min_confidence=0.0)
        high_conf_beliefs = bm.estimated_enemies(min_confidence=0.99)
        # Fresh belief should pass a 0 threshold but not necessarily 0.99
        self.assertGreaterEqual(len(all_beliefs), len(high_conf_beliefs))

    def test_update_with_empty_visibility(self) -> None:
        bm = BeliefMap()
        vis = _FakeVisibility()
        # Should not crash
        bm.update(vis, current_turn=1)
        self.assertEqual(len(bm.estimated_enemies(min_confidence=0.0)), 0)

    def test_estimated_enemies_returns_sorted_by_confidence(self) -> None:
        bm = BeliefMap()
        vis = _FakeVisibility(last_known={
            "e1": self._last_known("e1", 1, 1, 1),
            "e2": self._last_known("e2", 3, 3, 1),
        })
        bm.update(vis, current_turn=1)
        # Decay e1 confidence more
        empty_vis = _FakeVisibility()
        bm.update(empty_vis, current_turn=5)
        beliefs = bm.estimated_enemies(min_confidence=0.0)
        if len(beliefs) >= 2:
            self.assertGreaterEqual(beliefs[0].confidence, beliefs[1].confidence)


if __name__ == "__main__":
    unittest.main()
