"""Input helpers for selection and hotkeys."""

from __future__ import annotations

from core.units import Formation, UnitType


def cycle_formation(unit):
    if unit.unit_type is UnitType.INFANTRY:
        order = [Formation.COLUMN, Formation.LINE, Formation.SQUARE, Formation.SKIRMISH]
    elif unit.unit_type is UnitType.ARTILLERY:
        order = [Formation.LIMBERED, Formation.UNLIMBERED]
    elif unit.unit_type is UnitType.CAVALRY:
        order = [Formation.COLUMN, Formation.LINE]
    else:
        order = [unit.formation]

    index = order.index(unit.formation)
    return order[(index + 1) % len(order)]

