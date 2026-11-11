"""How fast a GTEX season passes in human time.

A season is still one game year: 365 game days and 12 career months. The
clock runs fast enough for that year to finish in 11 human weeks, the middle
of the 10–12 week season.
"""

from __future__ import annotations

GAME_SEASON_VIRTUAL_DAYS = 365
SEASON_LENGTH_REAL_DAYS = 77
DEFAULT_PROGRESSION_RATE = GAME_SEASON_VIRTUAL_DAYS / SEASON_LENGTH_REAL_DAYS
