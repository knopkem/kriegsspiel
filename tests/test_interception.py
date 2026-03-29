"""Tests for messenger interception mechanic (J7)."""
from __future__ import annotations

import random
import unittest

from core.map import HexCoord, HexGridMap, TerrainType
from core.messenger import is_intercepted, MessengerSystem
from core.units import (
    Side, Unit, UnitType, Formation, MoraleState, FacingDirection,
    make_cavalry_squadron, make_skirmisher_detachment, make_infantry_half_battalion,
)


def _make_unit(uid: str, utype: UnitType, side: Side, q: int, r: int) -> Unit:
    _factories = {
        UnitType.CAVALRY:   make_cavalry_squadron,
        UnitType.SKIRMISHER: make_skirmisher_detachment,
        UnitType.INFANTRY:  make_infantry_half_battalion,
    }
    factory = _factories.get(utype, make_infantry_half_battalion)
    unit = factory(uid, uid, side, position=HexCoord(q, r))
    return unit


class MessengerInterceptionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rng = random.Random(42)

    def test_no_threat_never_intercepted(self) -> None:
        """Path with no nearby enemy units: is_intercepted returns False."""
        path = [HexCoord(0, 0), HexCoord(1, 0), HexCoord(2, 0)]
        # Enemy is far away (q=10)
        enemy = _make_unit("e1", UnitType.CAVALRY, Side.RED, 10, 10)
        result = is_intercepted(path, [enemy], self.rng, base_chance=1.0)
        self.assertFalse(result)

    def test_cavalry_within_radius_triggers_roll(self) -> None:
        """Enemy cavalry within intercept_radius causes a roll."""
        path = [HexCoord(0, 0), HexCoord(1, 0), HexCoord(2, 0)]
        # Enemy cavalry adjacent to path step (1,0)
        enemy = _make_unit("e1", UnitType.CAVALRY, Side.RED, 1, 1)
        # With base_chance=1.0, interception guaranteed if threat exists
        result = is_intercepted(path, [enemy], self.rng, base_chance=1.0, intercept_radius=2)
        self.assertTrue(result)

    def test_skirmisher_within_radius_triggers_roll(self) -> None:
        """Enemy skirmisher also counts as interceptor."""
        path = [HexCoord(5, 5), HexCoord(6, 5)]
        enemy = _make_unit("e1", UnitType.SKIRMISHER, Side.RED, 5, 6)
        result = is_intercepted(path, [enemy], self.rng, base_chance=1.0, intercept_radius=2)
        self.assertTrue(result)

    def test_infantry_does_not_intercept(self) -> None:
        """Enemy infantry adjacent to path does NOT count as an interceptor."""
        path = [HexCoord(0, 0), HexCoord(1, 0)]
        enemy = _make_unit("e1", UnitType.INFANTRY, Side.RED, 1, 0)
        result = is_intercepted(path, [enemy], self.rng, base_chance=1.0, intercept_radius=2)
        self.assertFalse(result)

    def test_zero_base_chance_never_intercepted(self) -> None:
        """base_chance=0.0 means even threats never succeed."""
        path = [HexCoord(0, 0), HexCoord(1, 0)]
        enemy = _make_unit("e1", UnitType.CAVALRY, Side.RED, 1, 0)
        result = is_intercepted(path, [enemy], self.rng, base_chance=0.0, intercept_radius=2)
        self.assertFalse(result)

    def test_removed_unit_not_a_threat(self) -> None:
        """A removed (destroyed) enemy unit does not intercept."""
        path = [HexCoord(0, 0), HexCoord(1, 0)]
        enemy = _make_unit("e1", UnitType.CAVALRY, Side.RED, 1, 0)
        enemy.hit_points = 0  # marks unit as removed
        result = is_intercepted(path, [enemy], self.rng, base_chance=1.0, intercept_radius=2)
        self.assertFalse(result)

    def test_threat_outside_radius_not_intercepted(self) -> None:
        """Enemy outside intercept_radius is not a threat."""
        path = [HexCoord(0, 0), HexCoord(1, 0)]
        enemy = _make_unit("e1", UnitType.CAVALRY, Side.RED, 5, 5)
        result = is_intercepted(path, [enemy], self.rng, base_chance=1.0, intercept_radius=2)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
