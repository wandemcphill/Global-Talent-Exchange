from __future__ import annotations


def jackpot_balance(pool_key: str = "global") -> str:
    return f"jackpot:{pool_key}_balance"


def jackpot_trigger_state(pool_key: str = "global") -> str:
    return f"jackpot:{pool_key}:trigger_state"


def jackpot_last_winner(pool_key: str = "global") -> str:
    return f"jackpot:{pool_key}:last_winner"


def jackpot_participants(round_id: str) -> str:
    return f"jackpot:{round_id}:participants:set"


def jackpot_state(round_id: str) -> str:
    return f"jackpot:{round_id}:state"


def creator_price(player_id: str) -> str:
    return f"player:{player_id}:price"


def creator_demand(player_id: str) -> str:
    return f"player:{player_id}:demand_score"


def creator_cooldown(user_id: str, player_id: str) -> str:
    return f"market:{user_id}:{player_id}:cooldown"


def trending_players() -> str:
    return "market:trending_players"


def ai_state(ai_id: str) -> str:
    return f"ai:{ai_id}:state"


def ai_elo(ai_id: str) -> str:
    return f"ai:{ai_id}:elo"


def league_leaderboard(league_id: str) -> str:
    return f"leaderboard:league:{league_id}"


def queue_waiting() -> str:
    return "match:queue"


def stream_matchmaking() -> str:
    return "gtex.stream.matchmaking"


def stream_ai_brain() -> str:
    return "gtex.stream.ai_brain"


def stream_valuation() -> str:
    return "gtex.stream.valuation"


def stream_jackpot() -> str:
    return "gtex.stream.jackpot"
