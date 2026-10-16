from __future__ import annotations

from typing import Any


def build_headline(analysis: dict[str, Any]) -> str:
    winner = analysis.get("winner_team_name")
    if winner:
        return f"{winner} spark post-match chaos"
    return "No full-time handshake in this debate"
