from __future__ import annotations

from typing import Any


def generate_hot_takes(analysis: dict[str, Any]) -> list[str]:
    takes: list[str] = []
    winner = analysis.get("winner_team_name")
    xg_diff = float(analysis.get("xg_diff") or 0.0)
    if analysis.get("upset") and winner:
        takes.append(f"{winner} just turned the script upside down.")
    if abs(xg_diff) >= 0.8:
        team = analysis.get("winner_team_name") or "One side"
        takes.append(f"{team} won the xG war and the scoreline backed it up.")
    else:
        takes.append("The margins were tiny and the drama was bigger than the process.")
    if analysis.get("key_player"):
        takes.append(f"{analysis['key_player']} owned the biggest moments.")
    else:
        takes.append("No passenger performances were hiding in this one.")
    return takes[:3]
