"""Project-wide constants for the current implementation slice."""

TURN_DURATION_MINUTES = 2
HEX_SIZE_METERS = 75.0

DEFAULT_MAP_WIDTH = 50
DEFAULT_MAP_HEIGHT = 40

# UI text scale. 1=Small, 2=Medium, 3=Large.
# Main font uses TEXT_SCALE + 1, small font uses TEXT_SCALE.
# Default to the compact setting; larger values remain available in-game.
TEXT_SCALE: int = 1
