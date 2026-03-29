"""Colours and layout constants for the pygame UI."""

WINDOW_SIZE = (1280, 800)
FPS = 60

PARCHMENT = (245, 230, 200)
PANEL_BG = (32, 35, 42)
PANEL_BORDER = (88, 96, 108)
TEXT = (236, 239, 244)
MUTED_TEXT = (170, 176, 186)

BLUE_UNIT = (52, 101, 164)
RED_UNIT = (164, 52, 52)
NEUTRAL_UNIT = (110, 110, 110)
GHOST_UNIT = (150, 150, 150)

OPEN = (229, 216, 178)
ROAD = (194, 163, 90)
FOREST = (58, 107, 53)
HILL = (139, 111, 71)
RIVER = (74, 124, 155)
VILLAGE = (170, 130, 100)
MARSH = (109, 128, 83)
FORT = (110, 100, 120)

HIDDEN_OVERLAY = (25, 28, 33, 220)
EXPLORED_OVERLAY = (45, 48, 56, 130)
FOG_EDGE_OVERLAY = (35, 38, 48, 55)       # B10: soft border inside explored hexes near fog
MOVE_HIGHLIGHT = (70, 180, 90, 70)
ATTACK_HIGHLIGHT = (190, 70, 70, 90)       # B4: enemy positions — solid red tint
ATTACK_RANGE_OVERLAY = (190, 70, 70, 30)   # B4: in-range empty hexes — faint red ring
SELECTION = (255, 220, 90)
HOVER = (255, 255, 255)

# ── Colour-blind mode ────────────────────────────────────────────────────────
COLORBLIND_MODE: bool = False

# Originals kept for toggling back
_RED_UNIT_ORIG = RED_UNIT
_FOREST_ORIG = FOREST
_MOVE_HIGHLIGHT_ORIG = MOVE_HIGHLIGHT
_ATTACK_HIGHLIGHT_ORIG = ATTACK_HIGHLIGHT


def apply_colorblind_mode() -> None:
    """Toggle colour-blind safe palette, updating module-level colour constants.

    Replaces problematic red/green pairs with orange/blue and teal/amber
    alternatives that are distinguishable under deuteranopia and protanopia.
    Call again to revert to the default palette.
    """
    global COLORBLIND_MODE, RED_UNIT, FOREST, MOVE_HIGHLIGHT, ATTACK_HIGHLIGHT
    COLORBLIND_MODE = not COLORBLIND_MODE
    if COLORBLIND_MODE:
        RED_UNIT = (213, 94, 0)              # orange (replaces red)
        FOREST = (0, 114, 178)               # blue-green (replaces green)
        MOVE_HIGHLIGHT = (0, 158, 115, 70)   # teal
        ATTACK_HIGHLIGHT = (230, 159, 0, 90) # amber
    else:
        RED_UNIT = _RED_UNIT_ORIG
        FOREST = _FOREST_ORIG
        MOVE_HIGHLIGHT = _MOVE_HIGHLIGHT_ORIG
        ATTACK_HIGHLIGHT = _ATTACK_HIGHLIGHT_ORIG

