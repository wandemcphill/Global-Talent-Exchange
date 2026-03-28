from __future__ import annotations


def base_rank_score(
    *,
    viral_score: int,
    engagement: float,
    freshness: float,
    favorite_team_match: bool = False,
    favorite_event_match: bool = False,
) -> float:
    personalization = 0.0
    if favorite_team_match:
        personalization += 10.0
    if favorite_event_match:
        personalization += 6.0
    return round((viral_score * 0.6) + (engagement * 0.3) + (freshness * 0.1) + personalization, 2)


def blend_session_affinity(*, base_score: float, session_affinity: float) -> float:
    return round((0.7 * float(base_score)) + (0.3 * max(float(session_affinity), 0.0)), 2)


def rank_score(
    *,
    viral_score: int,
    engagement: float,
    freshness: float,
    favorite_team_match: bool = False,
    favorite_event_match: bool = False,
    session_boost: float = 0.0,
    session_affinity: float | None = None,
) -> float:
    base_score = base_rank_score(
        viral_score=viral_score,
        engagement=engagement,
        freshness=freshness,
        favorite_team_match=favorite_team_match,
        favorite_event_match=favorite_event_match,
    )
    if session_affinity is not None:
        return blend_session_affinity(
            base_score=base_score,
            session_affinity=session_affinity,
        )
    return round(base_score + session_boost, 2)
