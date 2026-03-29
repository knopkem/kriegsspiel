"""Tests for core/campaign.py."""

from __future__ import annotations

import json
import tempfile
import unittest

from core.campaign import (
    BattleResult,
    CampaignScenario,
    CampaignState,
    STANDARD_CAMPAIGN,
)
from core.units import Side


def _fake_unit(uid: str, side: Side, hp: int = 80, max_hp: int = 100, removed: bool = False):
    class FakeUnit:
        def __init__(self):
            self.id = uid
            self.side = side
            self.hit_points = hp
            self.max_hit_points = max_hp
            self.is_removed = removed
    return FakeUnit()


class TestCampaignProgress(unittest.TestCase):

    def _make_state(self) -> CampaignState:
        return CampaignState(campaign=STANDARD_CAMPAIGN)

    def test_initial_state(self):
        state = self._make_state()
        self.assertEqual(state.current_scenario_index, 0)
        self.assertFalse(state.is_complete)
        self.assertEqual(state.current_scenario.scenario_id, "tutorial")

    def test_record_result_advances_index(self):
        state = self._make_state()
        state.record_result(
            "tutorial",
            winner=Side.BLUE,
            turns_taken=4,
            surviving_units=[_fake_unit("b1", Side.BLUE)],
        )
        self.assertEqual(state.current_scenario_index, 1)

    def test_blue_wins_count(self):
        state = self._make_state()
        state.record_result("tutorial", winner=Side.BLUE, turns_taken=3, surviving_units=[])
        state.record_result("skirmish_small", winner=Side.RED, turns_taken=6, surviving_units=[])
        self.assertEqual(state.blue_wins, 1)
        self.assertEqual(state.red_wins, 1)

    def test_campaign_winner_after_completion(self):
        campaign = [
            CampaignScenario("a", "A", ""),
            CampaignScenario("b", "B", ""),
        ]
        state = CampaignState(campaign=campaign)
        state.record_result("a", winner=Side.BLUE, turns_taken=3, surviving_units=[])
        state.record_result("b", winner=Side.BLUE, turns_taken=3, surviving_units=[])
        self.assertTrue(state.is_complete)
        self.assertIs(state.campaign_winner, Side.BLUE)

    def test_campaign_draw(self):
        campaign = [
            CampaignScenario("a", "A", ""),
            CampaignScenario("b", "B", ""),
        ]
        state = CampaignState(campaign=campaign)
        state.record_result("a", winner=Side.BLUE, turns_taken=3, surviving_units=[])
        state.record_result("b", winner=Side.RED, turns_taken=3, surviving_units=[])
        self.assertIsNone(state.campaign_winner)

    def test_hp_carry_over_fraction(self):
        state = self._make_state()
        unit = _fake_unit("b1", Side.BLUE, hp=80, max_hp=100)
        state.record_result(
            "tutorial", winner=Side.BLUE, turns_taken=2, surviving_units=[unit]
        )
        # HP fraction should be 0.8 * 0.9 (tutorial carry fraction) = 0.72
        self.assertAlmostEqual(state.unit_hp_carry["b1"], 0.72, places=5)

    def test_apply_carry_over_modifies_unit_hp(self):
        state = CampaignState(campaign=STANDARD_CAMPAIGN)
        state.unit_hp_carry = {"b1": 0.5}
        unit = _fake_unit("b1", Side.BLUE, hp=100, max_hp=100)
        units_dict = {"b1": unit}
        state.apply_carry_over(units_dict)
        self.assertEqual(units_dict["b1"].hit_points, 50)

    def test_apply_carry_over_minimum_hp(self):
        # apply_carry_over clamps to max(1, ...) so even a tiny ratio → at least 1 HP
        state = CampaignState(campaign=STANDARD_CAMPAIGN)
        state.unit_hp_carry = {"b1": 0.001}
        unit = _fake_unit("b1", Side.BLUE, hp=100, max_hp=100)
        units_dict = {"b1": unit}
        state.apply_carry_over(units_dict)
        self.assertGreaterEqual(units_dict["b1"].hit_points, 1)

    def test_save_and_load_roundtrip(self):
        state = self._make_state()
        state.record_result(
            "tutorial",
            winner=Side.BLUE,
            turns_taken=5,
            surviving_units=[_fake_unit("b1", Side.BLUE, 70, 100)],
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        state.save(path)
        loaded = CampaignState.load(path, STANDARD_CAMPAIGN)

        self.assertEqual(loaded.current_scenario_index, 1)
        self.assertEqual(loaded.blue_wins, 1)
        self.assertIn("b1", loaded.unit_hp_carry)

    def test_summary_contains_titles(self):
        state = self._make_state()
        summary = state.summary()
        self.assertIn("Drill Day", summary)
        self.assertIn("Decisive Engagement", summary)

    def test_record_result_uses_matching_scenario_even_if_state_is_overfull(self):
        campaign = [CampaignScenario("a", "A", ""), CampaignScenario("b", "B", "")]
        state = CampaignState(
            campaign=campaign,
            results=[
                BattleResult("a", Side.BLUE, 3, 1, 0),
                BattleResult("b", Side.BLUE, 3, 1, 0),
            ],
        )

        state.record_result("b", winner=Side.BLUE, turns_taken=4, surviving_units=[_fake_unit("b1", Side.BLUE)])

        self.assertIn("b1", state.unit_hp_carry)

    def test_load_truncates_results_to_campaign_length(self):
        campaign = [CampaignScenario("a", "A", ""), CampaignScenario("b", "B", "")]
        payload = {
            "results": [
                {"scenario_id": "a", "winner": "blue", "turns_taken": 1, "blue_units_surviving": 1, "red_units_surviving": 0},
                {"scenario_id": "b", "winner": "blue", "turns_taken": 1, "blue_units_surviving": 1, "red_units_surviving": 0},
                {"scenario_id": "c", "winner": "red", "turns_taken": 1, "blue_units_surviving": 0, "red_units_surviving": 1},
            ],
            "unit_hp_carry": {},
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

        loaded = CampaignState.load(path, campaign)

        self.assertEqual(len(loaded.results), 2)


if __name__ == "__main__":
    unittest.main()
