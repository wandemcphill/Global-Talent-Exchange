from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import md5
import json
import logging
import os
import random
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.cache import CacheBackend, NullCacheBackend
from app.ingestion.models import InjuryStatus, Player
from app.models.base import utcnow
from app.models.card_access import CardLoanListing
from app.models.club_profile import ClubProfile
from app.models.club_sale_market import ClubSaleListing, ClubSaleOffer, ClubSaleTransfer
from app.models.competition import UserCompetition
from app.models.hosted_competition import HostedCompetitionStatus, UserHostedCompetition
from app.models.manager_market import ManagerCatalogEntry, ManagerHolding, ManagerTradeListing
from app.models.player_cards import PlayerCard, PlayerCardListing, PlayerMarketValueSnapshot, PlayerStatsSnapshot
from app.models.regen import RegenAward, RegenProfile

logger = logging.getLogger(__name__)

NEWS_TTL_SECONDS = 86_400
STORY_MEMORY_TTL_SECONDS = 172_800
USER_DAILY_LIMIT = 20
LISTING_DAILY_LIMIT = 5
DEFAULT_STORY_LIMIT = 20
BREAKING_TTL_SECONDS = 600

FAN_REACTIONS = (
    "Fans are divided on this move.",
    "Supporters are already arguing over the timing.",
    "The fanbase is watching the next update closely.",
    "The online noise around this one is getting louder.",
    "Fans are furious.",
    "Supporters are excited.",
    "Mixed reactions online.",
)

HEADLINE_MUTATIONS = (
    "as pressure grows",
    "with a fresh twist",
    "as scouts keep watching",
    "after new signals emerge",
    "with the room getting louder",
)

REGEN_LIFECYCLE_STAGES = ("Unknown", "Rising Talent", "Wonderkid", "Superstar", "Legend")
CHAOS_EVENTS = ("surprise_retirement", "takeover", "scandal", "youth_explosion")
_LOCAL_MEMORY: dict[str, tuple[datetime, Any]] = {}

FALLBACK_STORIES = (
    {
        "headline": "GTEX media desk opens the daily file",
        "body": "Scouts are still watching the regen circuit, with fresh reports expected once matches and listings move.",
        "type": "regen",
        "priority": 2,
        "club": None,
        "player_id": None,
        "player_name": None,
        "is_regen": False,
        "journalist": "GTEX Wire",
        "created_at": None,
        "metadata": {"source": "fallback"},
    },
)


@dataclass(frozen=True, slots=True)
class JournalistProfile:
    name: str
    style: str = "balanced"
    loves: tuple[str, ...] = ()
    hates: tuple[str, ...] = ()
    credibility: float = 0.8

    @property
    def likes(self) -> tuple[str, ...]:
        return self.loves

    @property
    def tone(self) -> str:
        return self.style


JOURNALISTS = (
    JournalistProfile(name="Rico Blaze", style="sensational", loves=("Madrid", "superstar"), hates=("Barca",), credibility=0.48),
    JournalistProfile(name="Marco Steele", style="dramatic", loves=("Arsenal", "GTEX Academy"), hates=("Chelsea",), credibility=0.72),
    JournalistProfile(name="Ada Okonkwo", style="scouting", loves=("regen", "academy", "wonderkid"), hates=("stagnation",), credibility=0.86),
    JournalistProfile(name="Luis Calder", style="measured", loves=("market", "tactics"), hates=("panic deals",), credibility=0.91),
    JournalistProfile(name="Tomi Briggs", style="sharp", loves=("underdogs", "local clubs"), hates=("complacency",), credibility=0.66),
)


class GTEXNewsRateLimitError(RuntimeError):
    def __init__(self, message: str, *, limit: int) -> None:
        super().__init__(message)
        self.limit = limit


def _stable_dumps(data: Any) -> str:
    return json.dumps(data, sort_keys=True, default=str)


def _stable_digest(data: Any) -> str:
    return md5(_stable_dumps(data).encode("utf-8")).hexdigest()


def _stable_rng(data: Any) -> random.Random:
    return random.Random(int(_stable_digest(data)[:12], 16))


def _status_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().lower()


def _player_name(player: Any) -> str:
    if isinstance(player, dict):
        return str(
            player.get("name")
            or player.get("player_name")
            or player.get("display_name")
            or player.get("full_name")
            or player.get("id")
            or "Unknown player"
        )
    return str(
        getattr(player, "canonical_display_name", None)
        or getattr(player, "full_name", None)
        or getattr(player, "short_name", None)
        or getattr(player, "id", None)
        or "Unknown player"
    )


def _amount(value: Any) -> str:
    return format(Decimal(str(value or 0)).quantize(Decimal("0.0001")), "f")


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _pick_journalist(story: dict[str, Any], rng: random.Random) -> JournalistProfile:
    story_type = str(story.get("type") or "")
    if story.get("is_regen") or story_type in {"regen", "award", "form"}:
        return JOURNALISTS[2]
    if story_type == "transfer" and int(story.get("priority") or 0) >= 8:
        return JOURNALISTS[3]
    if story_type in {"drama", "rivalry"}:
        return JOURNALISTS[0]
    return JOURNALISTS[rng.randrange(0, len(JOURNALISTS))]


def _news_story(
    *,
    headline: str,
    body: str,
    story_type: str,
    priority: int,
    club: str | None = None,
    player_id: str | None = None,
    player_name: str | None = None,
    is_regen: bool = False,
    journalist: str = "GTEX Wire",
    created_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata_payload = dict(metadata or {})
    identity = {
        "headline": headline,
        "type": story_type,
        "club": club,
        "player_id": player_id,
        "metadata": metadata_payload,
    }
    return {
        "id": f"news_{_stable_digest(identity)[:20]}",
        "headline": headline,
        "body": body,
        "type": story_type,
        "priority": max(1, min(int(priority), 10)),
        "club": club,
        "player_id": player_id,
        "player_name": player_name,
        "is_regen": bool(is_regen),
        "journalist": journalist,
        "created_at": created_at,
        "metadata": metadata_payload,
    }


def apply_bias(
    story: dict[str, Any],
    journalist: JournalistProfile | dict[str, Any],
    *,
    prefix_reporter: bool = False,
) -> dict[str, Any]:
    resolved_story = dict(story)
    club = str(resolved_story.get("club") or "")
    if isinstance(journalist, dict):
        name = str(journalist.get("name") or "GTEX Wire")
        bias = dict(journalist.get("bias") or {})
        likes = tuple(str(item) for item in bias.get("loves") or bias.get("likes", ()))
        hates = tuple(str(item) for item in bias.get("hates", ()))
        style = str(journalist.get("style") or journalist.get("tone") or "balanced")
        credibility = float(journalist.get("credibility") or 0.8)
        profile = JournalistProfile(name=name, style=style, loves=likes, hates=hates, credibility=credibility)
    else:
        profile = journalist

    if club and club in profile.hates:
        resolved_story["body"] = f"{resolved_story['body']} Questions are being raised internally."
        resolved_story["priority"] = min(10, int(resolved_story.get("priority") or 1) + 1)
    elif club and club in profile.loves:
        resolved_story["body"] = f"{resolved_story['body']} The tone around the club is warmer than usual."

    if profile.credibility < 0.6 and resolved_story.get("type") in {"transfer", "drama", "rivalry"}:
        resolved_story["body"] = f"{resolved_story['body']} One source close to the room insists the noise is real."
        resolved_story["priority"] = min(10, int(resolved_story.get("priority") or 1) + 1)
    elif profile.credibility >= 0.85 and int(resolved_story.get("priority") or 0) >= 8:
        resolved_story["body"] = f"{resolved_story['body']} The confidence behind this report is unusually strong."

    if prefix_reporter and not str(resolved_story.get("body") or "").startswith(f"{profile.name} reports:"):
        resolved_story["body"] = f"{profile.name} reports: {resolved_story['body']}"

    resolved_story["journalist"] = profile.name
    metadata = dict(resolved_story.get("metadata") or {})
    metadata["media_personality"] = {
        "name": profile.name,
        "style": profile.style,
        "bias": {"loves": list(profile.loves), "hates": list(profile.hates)},
        "credibility": profile.credibility,
    }
    metadata["journalist_tone"] = profile.tone
    metadata["bias_propagation"] = _bias_propagation_score(resolved_story, profile)
    resolved_story["metadata"] = metadata
    return resolved_story


def _bias_propagation_score(story: dict[str, Any], journalist: JournalistProfile) -> float:
    score = journalist.credibility
    club = str(story.get("club") or "")
    body = str(story.get("body") or "")
    if club and club in journalist.loves:
        score += 0.15
    if club and club in journalist.hates:
        score += 0.2
    if story.get("is_regen") and any(token in journalist.loves for token in ("regen", "academy", "wonderkid")):
        score += 0.2
    if journalist.style == "sensational" and any(token in body.lower() for token in ("unhappy", "talks", "tensions")):
        score += 0.1
    return round(max(0.0, min(score, 1.5)), 3)


def pundit_reaction(story: dict[str, Any]) -> list[str]:
    story_type = str(story.get("type") or "")
    if story_type == "transfer":
        return [
            "This is a brilliant move if the terms are real.",
            "I completely disagree with this valuation.",
            "This could backfire badly if the dressing room does not buy in.",
        ]
    if story_type == "regen":
        return [
            "The ceiling is obvious, but the pressure starts now.",
            "People are getting carried away too early.",
            "This is exactly why clubs should scout regens aggressively.",
        ]
    if story_type == "manager":
        return [
            "The tactical fit makes sense on paper.",
            "Managers need time, but this app rarely gives it.",
            "One bad tournament can turn this appointment toxic.",
        ]
    return [
        "This is a brilliant move.",
        "I completely disagree with this decision.",
        "This could backfire badly.",
    ]


def fan_reaction(story: dict[str, Any], rng: random.Random) -> str:
    story_type = str(story.get("type") or "")
    priority = int(story.get("priority") or 0)
    if story_type in {"drama", "rivalry"}:
        options = ("Fans are furious.", "Mixed reactions online.", "Supporters are already arguing over the timing.")
    elif story_type in {"regen", "award", "form"} and story.get("is_regen"):
        options = ("Supporters are excited.", "The fanbase is watching the next update closely.", "Mixed reactions online.")
    elif priority >= 8:
        options = ("The online noise around this one is getting louder.", "Fans are divided on this move.")
    else:
        options = FAN_REACTIONS
    return options[rng.randrange(len(options))]


def regen_lifecycle_stage(player: dict[str, Any]) -> dict[str, Any]:
    potential = _int_value(player.get("potential"), 0)
    gsi = _int_value(player.get("current_gsi"), 0)
    morale = _int_value(player.get("morale"), 50)
    goals_last_3 = _int_value(player.get("goals_last_3"), 0)
    hype = max(0, min(100, int((potential * 0.45) + (gsi * 0.4) + (goals_last_3 * 4) + max(0, morale - 50) * 0.15)))
    if hype >= 95 or gsi >= 94:
        stage = "Legend"
    elif hype >= 86 or gsi >= 88:
        stage = "Superstar"
    elif hype >= 74 or potential >= 88:
        stage = "Wonderkid"
    elif hype >= 55 or potential >= 75:
        stage = "Rising Talent"
    else:
        stage = "Unknown"
    return {"player_id": player.get("id"), "stage": stage, "hype": hype}


def update_value(player: dict[str, Any]) -> dict[str, Any]:
    lifecycle = dict(player.get("lifecycle") or regen_lifecycle_stage(player))
    market_value = dict(player.get("market_value") or {})
    base_value = (
        market_value.get("listing_floor_price_credits")
        or market_value.get("avg_trade_price_credits")
        or market_value.get("last_trade_price_credits")
        or player.get("value")
        or 0
    )
    value = Decimal(str(base_value or 0))
    multiplier = Decimal("1") + (Decimal(str(lifecycle.get("hype") or 0)) / Decimal("1000"))
    if player.get("form") == "cold" or player.get("is_unhappy"):
        multiplier -= Decimal("0.035")
    projected = max(Decimal("0"), value * multiplier)
    return {
        "base_value": _amount(value),
        "projected_value": _amount(projected),
        "multiplier": float(multiplier),
        "hype": lifecycle.get("hype", 0),
    }


def dressing_room_story(player: dict[str, Any]) -> dict[str, Any] | None:
    morale = _int_value(player.get("morale"), 50)
    if morale >= 35 and not player.get("is_unhappy") and not player.get("transfer_blocked"):
        return None
    name = _player_name(player)
    reason = "transfer blocking" if player.get("transfer_blocked") else "low morale"
    return _news_story(
        headline=f"{name} frustration becomes a dressing room story",
        body="Locker room unrest is being discussed behind the scenes, and the next decision may define the mood.",
        story_type="drama",
        priority=7 if morale < 25 else 6,
        club=player.get("club"),
        player_id=player.get("id"),
        player_name=name,
        is_regen=bool(player.get("is_regen")),
        metadata={"narrative": "dressing_room_unrest", "reason": reason, "morale": morale},
    )


def progressive_transfer_leak(player: dict[str, Any], club: str, timeline: dict[str, Any]) -> dict[str, Any]:
    stage = max(1, min(_int_value(timeline.get("stage"), 1), 5))
    story = transfer_leak(player, club, stage)
    days_in_stage = _int_value(timeline.get("days_in_stage"), 0)
    story["body"] = f"{story['body']} This leak has been sitting at stage {stage} for {days_in_stage} day(s)."
    metadata = dict(story.get("metadata") or {})
    metadata.update(
        {
            "timeline": {
                "stage": stage,
                "days_in_stage": days_in_stage,
                "arc_id": timeline.get("arc_id"),
            },
            "narrative": "leak_progression",
        }
    )
    story["metadata"] = metadata
    story["priority"] = max(story["priority"], 4 + stage)
    return story


def narrative_arc_story(arc: dict[str, Any]) -> dict[str, Any]:
    progress = max(1, min(_int_value(arc.get("progress"), 1), 5))
    player = dict(arc.get("player") or {})
    name = _player_name(player)
    club = str(arc.get("club") or player.get("club") or "the club")
    beats = {
        1: (f"{name} uncertainty starts to build", "People close to the player sense the first signs of frustration."),
        2: (f"{club} deny {name} exit noise", "Club sources are pushing back, but the room is not fully convinced."),
        3: (f"Talks begin around {name}", "A quiet pathway is forming and the market is beginning to react."),
        4: (f"{name} deal edges closer", "The next update could decide whether this becomes a full breaking story."),
        5: (f"Here we go arc: {name} reaches the final beat", "The storyline has moved from smoke to a high-impact decision point."),
    }
    headline, body = beats[progress]
    return _news_story(
        headline=headline,
        body=body,
        story_type="arc",
        priority=5 + progress,
        club=club,
        player_id=player.get("id"),
        player_name=name,
        is_regen=bool(player.get("is_regen")),
        metadata={
            "arc_id": arc.get("arc_id"),
            "progress": progress,
            "arc_type": arc.get("arc_type") or "transfer_drama",
        },
    )


def manager_career_snapshot(manager: dict[str, Any]) -> dict[str, Any]:
    seed = int(_stable_digest({"manager": manager})[:8], 16)
    win_rate = 35 + (seed % 51)
    pressure = max(5, min(100, 90 - win_rate + (10 if str(manager.get("rarity", "")).lower() in {"elite", "legendary"} else 0)))
    sentiment = "praise" if win_rate >= 62 else "criticism" if pressure >= 60 else "neutral"
    if pressure >= 82:
        sentiment = "sack_watch"
    return {"win_rate": win_rate, "pressure_level": pressure, "media_sentiment": sentiment}


def club_personality(club_name: str | None) -> dict[str, Any]:
    resolved_name = club_name or "Unknown Club"
    rng = _stable_rng({"club_personality": resolved_name})
    styles = ("big spender", "academy-first", "chaotic", "patient builder", "defensive identity")
    patience = round(rng.uniform(0.2, 0.9), 2)
    return {"club": resolved_name, "style": styles[rng.randrange(len(styles))], "patience": patience}


def chaos_event_story(data: dict[str, Any]) -> dict[str, Any] | None:
    rng = _stable_rng({"chaos": data.get("cycle_key"), "players": data.get("players", [])[:5]})
    if rng.random() > 0.035:
        return None
    event_type = CHAOS_EVENTS[rng.randrange(len(CHAOS_EVENTS))]
    regen_players = [dict(item) for item in data.get("players", []) if dict(item).get("is_regen")]
    player = regen_players[rng.randrange(len(regen_players))] if regen_players else {}
    name = _player_name(player) if player else "A hidden academy name"
    templates = {
        "surprise_retirement": (f"{name} camp hit by surprise future talk", "A sudden career-path twist has shocked the room."),
        "takeover": ("Takeover whispers shake a GTEX club", "Ownership noise is threatening to change the transfer mood."),
        "scandal": ("Scandal rumor hits the market desk", "The facts are still thin, but the noise is impossible to ignore."),
        "youth_explosion": (f"Youth explosion alert around {name}", "A rare academy jump has pushed scouts into emergency meetings."),
    }
    headline, body = templates[event_type]
    return _news_story(
        headline=headline,
        body=body,
        story_type="chaos",
        priority=9,
        club=player.get("club") if player else None,
        player_id=player.get("id") if player else None,
        player_name=name if player else None,
        is_regen=bool(player),
        metadata={"chaos_event": event_type, "probability": "rare"},
    )


def transfer_leak(player: dict[str, Any] | str, club: str, stage: int) -> dict[str, Any]:
    stages = {
        1: "Initial talks happening quietly.",
        2: "Serious interest developing.",
        3: "Advanced negotiations ongoing.",
        4: "Deal almost complete.",
        5: "Here we go! Transfer confirmed.",
    }
    safe_stage = max(1, min(int(stage), 5))
    player_name = _player_name(player)
    player_id = player.get("id") if isinstance(player, dict) else None
    is_regen = bool(player.get("is_regen")) if isinstance(player, dict) else False
    return _news_story(
        headline=f"{club} pushing for {player_name}",
        body=stages[safe_stage],
        story_type="transfer",
        priority=safe_stage,
        club=club,
        player_id=player_id,
        player_name=player_name,
        is_regen=is_regen,
        metadata={"leak_stage": safe_stage},
    )


def here_we_go_story(
    player: dict[str, Any] | str,
    club: str,
    *,
    deal_score: float,
    player_agrees_terms: bool,
    club_funds_available: bool,
) -> dict[str, Any] | None:
    if deal_score <= 0.9 or not player_agrees_terms or not club_funds_available:
        return None
    story = transfer_leak(player, club, 5)
    story["headline"] = f"Here we go: {club} land {_player_name(player)}"
    story["priority"] = 10
    metadata = dict(story.get("metadata") or {})
    metadata.update(
        {
            "deal_score": round(float(deal_score), 3),
            "player_agrees_terms": True,
            "club_funds_available": True,
            "impact": "confirmed_transfer",
        }
    )
    story["metadata"] = metadata
    return story


def regen_hype(player: dict[str, Any]) -> dict[str, Any]:
    name = _player_name(player)
    club = player.get("club")
    potential = _int_value(player.get("potential"), 0)
    gsi = _int_value(player.get("current_gsi"), 0)
    lifecycle = dict(player.get("lifecycle") or regen_lifecycle_stage(player))
    market_projection = update_value({**player, "lifecycle": lifecycle})
    body = "A new superstar may be rising."
    if lifecycle["stage"] in {"Superstar", "Legend"}:
        body = f"The regen lifecycle desk now treats this as a {lifecycle['stage']} track, not a normal prospect."
    elif potential >= 88:
        body = "Scouts think this could become one of the rare regen stories of the cycle."
    elif gsi >= 80:
        body = "The performance floor is jumping fast, and the hype is starting to follow."
    return _news_story(
        headline=f"{name} taking the league by storm",
        body=body,
        story_type="regen",
        priority=5 + int(potential >= 85) + int(gsi >= 82),
        club=club,
        player_id=player.get("id"),
        player_name=name,
        is_regen=True,
        metadata={
            "potential": potential,
            "current_gsi": gsi,
            "market_value_signal": "up",
            "regen_lifecycle": lifecycle,
            "market_value_projection": market_projection,
            "narrative": "regen_hype",
        },
    )


def generate_listing(data: dict[str, Any]) -> dict[str, Any]:
    rng = _stable_rng(data)
    player = dict(data.get("player") or data)
    name = _player_name(player)
    club = str(data.get("club") or player.get("club") or "the market")
    listing_type = str(data.get("listing_type") or data.get("type") or "").strip().lower()
    is_regen = bool(player.get("is_regen"))
    morale = _int_value(player.get("morale"), 50)
    potential = _int_value(player.get("potential"), 0)
    form = str(player.get("form") or "normal").strip().lower()

    if listing_type in {"transfer", "sale", "loan", "listing"}:
        stage = _int_value(data.get("stage"), 2 if listing_type != "loan" else 1)
        story = transfer_leak(player, club, stage)
        if listing_type == "loan":
            story["headline"] = f"Loan desk opens around {name}"
            story["body"] = f"{club} has a short-term path for {name}. {story['body']}"
            story["priority"] = max(3, story["priority"])
            story["metadata"] = {**dict(story.get("metadata") or {}), "listing_type": "loan"}
    elif is_regen and (potential >= 80 or form == "hot"):
        story = regen_hype({**player, "club": club})
    elif morale < 35 or bool(player.get("is_unhappy")):
        story = _news_story(
            headline=f"{name} situation getting tense",
            body="Dressing room sources suggest the mood has dipped and a decision may be coming.",
            story_type="drama",
            priority=5,
            club=club,
            player_id=player.get("id"),
            player_name=name,
            is_regen=is_regen,
            metadata={"morale": morale, "narrative": "dressing_room_drama"},
        )
    elif str(data.get("event") or "").lower() == "injury":
        story = _news_story(
            headline=f"{name} injury update changes the week",
            body="The player is expected to step away from the spotlight while recovery is tracked.",
            story_type="injury",
            priority=4,
            club=club,
            player_id=player.get("id"),
            player_name=name,
            is_regen=is_regen,
            metadata={"narrative": "injury_news"},
        )
    else:
        story = _news_story(
            headline=f"{name} remains on the media watchlist",
            body="The desk is tracking form, value and club mood before the next update.",
            story_type="market",
            priority=3,
            club=club,
            player_id=player.get("id"),
            player_name=name,
            is_regen=is_regen,
            metadata={"narrative": "watchlist"},
        )

    journalist = _pick_journalist(story, rng)
    story = apply_bias(story, journalist)
    if rng.random() < 0.7:
        story["body"] = f"{story['body']} {FAN_REACTIONS[rng.randrange(len(FAN_REACTIONS))]}"
    return story


def generate_daily_news(data: dict[str, Any]) -> list[dict[str, Any]]:
    cycle_key = data.get("cycle_key") or date.today().isoformat()
    rng = _stable_rng({"cycle_key": cycle_key, "data": data})
    stories: list[dict[str, Any]] = []

    for award in list(data.get("awards") or [])[:5]:
        player = dict(award.get("player") or {})
        name = _player_name(player)
        award_name = award.get("award_name") or "a major regen award"
        stories.append(
            _news_story(
                headline=f"{name} wins {award_name}",
                body="The regen awards desk has moved this story into the front row.",
                story_type="award",
                priority=8 if _int_value(award.get("impact_score"), 0) >= 80 else 6,
                club=player.get("club"),
                player_id=player.get("id"),
                player_name=name,
                is_regen=True,
                metadata={"award": award_name, "impact_score": award.get("impact_score")},
            )
        )

    regen_players = [dict(item) for item in data.get("players", ()) if dict(item).get("is_regen")]
    for player in regen_players:
        player["lifecycle"] = dict(player.get("lifecycle") or regen_lifecycle_stage(player))
        player["market_value_projection"] = update_value(player)
    regen_players.sort(
        key=lambda item: (
            _int_value(dict(item.get("lifecycle") or {}).get("hype"), 0),
            _int_value(item.get("potential"), 0),
            _int_value(item.get("current_gsi"), 0),
            _int_value(item.get("morale"), 50),
        ),
        reverse=True,
    )
    for player in regen_players[:10]:
        if player.get("injured"):
            continue
        dressing_room = dressing_room_story(player)
        if dressing_room is not None:
            stories.append(dressing_room)
            continue
        if _int_value(player.get("goals_last_3"), 0) >= 5:
            stories.append(_form_streak_story(player))
        elif _int_value(player.get("morale"), 50) < 35 or player.get("is_unhappy"):
            stories.append(generate_listing({"player": player, "club": player.get("club"), "event": "drama"}))
        elif (
            rng.random() < 0.75
            or _int_value(player.get("potential"), 0) >= 82
            or dict(player.get("lifecycle") or {}).get("stage") in {"Wonderkid", "Superstar", "Legend"}
        ):
            stories.append(regen_hype(player))
        else:
            stories.append(_market_value_story(player, rising=True))

    for arc in list(data.get("arcs") or [])[:6]:
        stories.append(narrative_arc_story(dict(arc)))

    for injury in list(data.get("injuries") or [])[:4]:
        player = dict(injury.get("player") or {})
        player["injured"] = True
        stories.append(
            _news_story(
                headline=f"{_player_name(player)} steps away with injury concern",
                body="The medical update removes the player from the main hype cycle for now.",
                story_type="injury",
                priority=4,
                club=player.get("club"),
                player_id=player.get("id"),
                player_name=_player_name(player),
                is_regen=bool(player.get("is_regen")),
                metadata={"detail": injury.get("detail"), "expected_return_at": injury.get("expected_return_at")},
            )
        )

    for listing in list(data.get("transfers") or [])[:6]:
        player = dict(listing.get("player") or {})
        target_club = str(listing.get("target_club") or player.get("club") or "a buying club")
        confirmed = here_we_go_story(
            player,
            target_club,
            deal_score=float(listing.get("deal_score") or 0),
            player_agrees_terms=bool(listing.get("player_agrees_terms")),
            club_funds_available=bool(listing.get("club_funds_available")),
        )
        if confirmed is not None:
            stories.append(confirmed)
            continue
        timeline = dict(listing.get("timeline") or {})
        if timeline:
            story = progressive_transfer_leak(player, target_club, timeline)
        else:
            stage = max(1, min(_int_value(listing.get("stage"), 2), 4))
            story = transfer_leak(player, target_club, stage)
        story["body"] = f"{story['body']} Asking price sits near {_amount(listing.get('price'))} GTEX Coin."
        story["metadata"] = {**dict(story.get("metadata") or {}), "listing_id": listing.get("listing_id")}
        stories.append(story)

    for listing in list(data.get("loans") or [])[:4]:
        player = dict(listing.get("player") or {})
        stories.append(
            generate_listing(
                {
                    "player": player,
                    "club": player.get("club") or "the loan market",
                    "listing_type": "loan",
                    "stage": 1,
                    "listing_id": listing.get("listing_id"),
                }
            )
        )

    for manager in list(data.get("managers") or [])[:4]:
        stories.append(_manager_story(dict(manager)))

    for club_sale in list(data.get("club_sales") or [])[:5]:
        stories.append(_club_sale_story(dict(club_sale)))

    for competition in list(data.get("competitions") or [])[:5]:
        stories.append(_competition_story(dict(competition)))

    if len(regen_players) >= 2:
        first, second = regen_players[0], regen_players[1]
        stories.append(
            _news_story(
                headline=f"{_player_name(first)} and {_player_name(second)} split scout opinion",
                body="Two regen tracks are rising at once, and the market is trying to decide which story is real.",
                story_type="rivalry",
                priority=5,
                club=first.get("club"),
                player_id=first.get("id"),
                player_name=_player_name(first),
                is_regen=True,
                metadata={"rival_regen_id": second.get("id"), "narrative": "regen_rivalry"},
            )
        )

    for rivalry in list(data.get("rivalries") or [])[:5]:
        player = dict(rivalry.get("player") or {})
        hated_club = str(rivalry.get("hated_club") or "a rival club")
        intensity = float(rivalry.get("intensity") or 0.5)
        stories.append(
            _news_story(
                headline=f"{_player_name(player)} rivalry with {hated_club} gets hostile",
                body="Crowd hostility is expected to lift the temperature before the next match.",
                story_type="rivalry",
                priority=6 + int(intensity >= 0.8),
                club=player.get("club"),
                player_id=player.get("id"),
                player_name=_player_name(player),
                is_regen=bool(player.get("is_regen")),
                metadata={
                    "rivalry": {
                        "player_id": player.get("id"),
                        "hated_club": hated_club,
                        "intensity": intensity,
                    },
                    "narrative": "revenge_match",
                },
            )
        )

    chaos = chaos_event_story(data)
    if chaos is not None:
        stories.append(chaos)

    if not stories:
        stories.extend(dict(item) for item in FALLBACK_STORIES)

    enriched: list[dict[str, Any]] = []
    for story in stories:
        seeded_rng = _stable_rng({"cycle_key": cycle_key, "story": story})
        journalist = _pick_journalist(story, seeded_rng)
        biased = apply_bias(story, journalist, prefix_reporter=True)
        metadata = dict(biased.get("metadata") or {})
        if int(biased.get("priority") or 0) >= 7:
            metadata["pundit_reactions"] = pundit_reaction(biased)
        biased["metadata"] = metadata
        if seeded_rng.random() < 0.65 and not str(biased["body"]).endswith(tuple(FAN_REACTIONS)):
            biased["body"] = f"{biased['body']} {fan_reaction(biased, seeded_rng)}"
        enriched.append(biased)

    return _dedupe_and_sort(enriched)[:DEFAULT_STORY_LIMIT]


def _form_streak_story(player: dict[str, Any]) -> dict[str, Any]:
    goals = _int_value(player.get("goals_last_3"), 5)
    lifecycle = dict(player.get("lifecycle") or regen_lifecycle_stage(player))
    return _news_story(
        headline=f"{_player_name(player)} hits a serious scoring streak",
        body=f"{goals} goals in 3 matches has shifted the hype cycle and raised the market temperature.",
        story_type="form",
        priority=8 if bool(player.get("is_regen")) and goals >= 5 else 7,
        club=player.get("club"),
        player_id=player.get("id"),
        player_name=_player_name(player),
        is_regen=bool(player.get("is_regen")),
        metadata={
            "goals_last_3": goals,
            "market_value_signal": "up",
            "regen_lifecycle": lifecycle,
            "market_value_projection": update_value({**player, "lifecycle": lifecycle}),
        },
    )


def _market_value_story(player: dict[str, Any], *, rising: bool) -> dict[str, Any]:
    direction = "rising" if rising else "cooling"
    projection = update_value(player)
    return _news_story(
        headline=f"{_player_name(player)} value is {direction}",
        body="The desk links the move to form, scout confidence and the latest market attention.",
        story_type="market",
        priority=5 if rising else 3,
        club=player.get("club"),
        player_id=player.get("id"),
        player_name=_player_name(player),
        is_regen=bool(player.get("is_regen")),
        metadata={"market_value_signal": "up" if rising else "down", "market_value_projection": projection},
    )


def _manager_story(manager: dict[str, Any]) -> dict[str, Any]:
    name = str(manager.get("name") or "A manager")
    club = manager.get("club")
    tactics = ", ".join(list(manager.get("tactics") or [])[:2]) or manager.get("mentality") or "adaptive"
    career = manager_career_snapshot(manager)
    pressure_text = "under pressure" if career["pressure_level"] >= 70 else "building credibility"
    return _news_story(
        headline=f"{name} becomes a tactical market story",
        body=f"Appointments, sackings and card movement around {name} now matter because the fit reads {tactics}. The career desk has them {pressure_text}.",
        story_type="manager",
        priority=7 if career["media_sentiment"] == "sack_watch" else 5,
        club=club,
        player_name=None,
        is_regen=False,
        metadata={
            "manager_id": manager.get("manager_id"),
            "asset_id": manager.get("asset_id"),
            "price": manager.get("price"),
            "tactics": manager.get("tactics") or [],
            "career": career,
        },
    )


def _club_sale_story(club_sale: dict[str, Any]) -> dict[str, Any]:
    club_name = str(club_sale.get("club_name") or "A club")
    state = str(club_sale.get("state") or "available")
    price = _amount(club_sale.get("price"))
    personality = club_personality(club_name)
    return _news_story(
        headline=f"{club_name} ownership story moves to {state}",
        body=f"The club sale desk has {club_name} at {price} GTEX Coin, with local identity still central. The club profile reads {personality['style']}.",
        story_type="club_sale",
        priority=7 if state in {"settled", "accepted"} else 4,
        club=club_name,
        metadata={
            "club_id": club_sale.get("club_id"),
            "listing_id": club_sale.get("listing_id"),
            "state": state,
            "price": price,
            "club_personality": personality,
        },
    )


def _competition_story(competition: dict[str, Any]) -> dict[str, Any]:
    name = str(competition.get("name") or "GTEX competition")
    status = str(competition.get("status") or "open")
    return _news_story(
        headline=f"Competition watch: {name}",
        body=f"{name} is in {status}, and the media desk expects player narratives to move once results land.",
        story_type="competition",
        priority=6 if status in {"live", "active", "running", "launched"} else 4,
        metadata={
            "competition_id": competition.get("id"),
            "competition_kind": competition.get("kind"),
            "format": competition.get("format"),
            "status": status,
        },
    )


def _dedupe_and_sort(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str | None]] = set()
    unique: list[dict[str, Any]] = []
    for story in stories:
        key = (str(story.get("headline")), story.get("player_id"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(story)
    return sorted(unique, key=lambda item: (-int(item.get("priority") or 0), str(item.get("headline") or "")))


def _headline_hash(story: dict[str, Any]) -> str:
    normalized = " ".join(str(story.get("headline") or "").lower().split())
    return _stable_digest({"headline": normalized})


def _mutate_story(story: dict[str, Any], mutation_index: int) -> dict[str, Any]:
    mutated = dict(story)
    suffix = HEADLINE_MUTATIONS[mutation_index % len(HEADLINE_MUTATIONS)]
    headline = str(mutated.get("headline") or "GTEX story")
    if suffix not in headline:
        mutated["headline"] = f"{headline} {suffix}"
    body_tail = (
        " The detail has shifted enough for the desk to reopen the file."
        if mutation_index % 2
        else " Fresh context has changed how the room reads it."
    )
    if body_tail.strip() not in str(mutated.get("body") or ""):
        mutated["body"] = f"{mutated.get('body')}{body_tail}"
    return mutated


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        resolved = value
    else:
        try:
            resolved = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)
    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=timezone.utc)
    return resolved


def _flatten_news_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bucket in ("breaking", "top_stories", "rumors"):
        for story in list(payload.get(bucket) or []):
            story_id = str(story.get("id") or story.get("headline"))
            if story_id in seen:
                continue
            seen.add(story_id)
            stories.append(dict(story))
    return stories


class GTEXNewsEngineService:
    def __init__(self, session: Session, *, cache_backend: CacheBackend | None = None) -> None:
        self.session = session
        self.cache_backend = cache_backend or NullCacheBackend()

    def daily_news(
        self,
        *,
        user_id: str | None = None,
        force: bool = False,
        scope: str = "daily",
    ) -> dict[str, list[dict[str, Any]]]:
        normalized_scope = "light" if scope == "light" else "daily"
        cache_key = self._daily_cache_key(normalized_scope)
        if not force:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        if user_id:
            self._enforce_daily_user_limit(user_id)

        data = self._collect_news_data(scope=normalized_scope)
        stories = generate_daily_news(data)
        stories = self._apply_story_memory(stories, scope=normalized_scope)
        payload = self._group_stories(stories)
        self.cache_backend.set(cache_key, json.dumps(payload, default=str), NEWS_TTL_SECONDS)
        logger.info("NEWS_GENERATED", extra={"event": "NEWS_GENERATED", "stories_count": len(stories)})
        return payload

    def breaking_news(self, *, force: bool = False, limit: int = 8) -> list[dict[str, Any]]:
        cache_key = "gtex-news:breaking"
        if not force:
            cached = self._get_cached(cache_key)
            if isinstance(cached, list):
                return cached[:limit]
        data = self._collect_news_data(scope="light")
        stories = generate_daily_news(data)
        breaking = [
            story
            for story in stories
            if int(story.get("priority") or 0) >= 8
            or story.get("type") in {"chaos", "manager", "arc"}
            and int(story.get("priority") or 0) >= 7
        ]
        breaking = self._apply_story_memory(_dedupe_and_sort(breaking), scope="breaking")[:limit]
        stamped = []
        generated_at = utcnow().isoformat()
        for story in breaking:
            item = dict(story)
            item["created_at"] = item.get("created_at") or generated_at
            stamped.append(item)
        self.cache_backend.set(cache_key, json.dumps(stamped, default=str), BREAKING_TTL_SECONDS)
        return stamped

    def personalized_news(self, user_context: dict[str, Any], *, force: bool = False) -> dict[str, list[dict[str, Any]]]:
        from app.services.personalized_feed import rank_for_user

        payload = self.daily_news(user_id=str(user_context.get("user_id") or "anonymous"), force=force)
        ranked = rank_for_user(_flatten_news_payload(payload), user_context)
        return self._group_stories(ranked)

    def generate_listing_with_cache(
        self,
        data: dict[str, Any],
        *,
        user_id: str | None = None,
        listing_id: str | None = None,
    ) -> dict[str, Any]:
        cache_key = f"sle:{_stable_digest(data)}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        if user_id:
            self._enforce_daily_user_limit(user_id)
        if listing_id:
            self._enforce_listing_limit(listing_id)
        story = self.generate_with_ai_pipeline_control(data)
        self.cache_backend.set(cache_key, json.dumps(story, default=str), NEWS_TTL_SECONDS)
        return story

    def generate_with_ai_pipeline_control(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            if not os.getenv("OPENAI_API_KEY") or os.getenv("GTE_NEWS_AI_ENABLED", "0").lower() not in {
                "1",
                "true",
                "yes",
                "on",
            }:
                raise RuntimeError("AI disabled")
            raise TimeoutError("External AI calls are disabled for the offline GTEX News Engine")
        except Exception:
            return generate_listing(data)

    def _collect_news_data(self, *, scope: str) -> dict[str, Any]:
        limit = 18 if scope == "light" else 40
        today = date.today().isoformat()
        data: dict[str, Any] = {
            "cycle_key": f"{today}:{scope}",
            "players": [],
            "awards": [],
            "injuries": [],
            "transfers": [],
            "loans": [],
            "managers": [],
            "club_sales": [],
            "competitions": [],
            "arcs": [],
            "rivalries": [],
        }
        data["players"].extend(self._regen_players(limit=limit))
        data["awards"].extend(self._regen_awards(limit=min(8, limit)))
        data["injuries"].extend(self._injury_items(limit=min(6, limit)))
        data["transfers"].extend(self._transfer_items(limit=min(10, limit)))
        data["loans"].extend(self._loan_items(limit=min(6, limit)))
        data["managers"].extend(self._manager_items(limit=min(6, limit)))
        data["club_sales"].extend(self._club_sale_items(limit=min(8, limit)))
        data["competitions"].extend(self._competition_items(limit=min(8, limit)))
        data["rivalries"].extend(self._rivalry_items(data["players"], limit=min(6, limit)))
        self._advance_leaks(data)
        self._advance_arcs(data)
        self._store_regen_lifecycle(data["players"])
        return data

    def _advance_leaks(self, data: dict[str, Any]) -> None:
        today = date.today().isoformat()
        memory = dict(self._load_json_memory("gtex-news:leaks") or {})
        updated: dict[str, Any] = dict(memory)
        for item in data.get("transfers", []):
            listing_id = str(item.get("listing_id") or _stable_digest(item)[:16])
            previous = dict(memory.get(listing_id) or {})
            incoming_stage = max(1, min(_int_value(item.get("stage"), 1), 5))
            stage = max(incoming_stage, _int_value(previous.get("stage"), incoming_stage))
            days_in_stage = _int_value(previous.get("days_in_stage"), 0)
            if previous.get("last_updated_date") != today:
                if stage < 5 and days_in_stage >= 1:
                    stage += 1
                    days_in_stage = 0
                else:
                    days_in_stage += 1
            timeline = {
                "arc_id": f"leak_{listing_id}",
                "stage": stage,
                "days_in_stage": days_in_stage,
                "last_updated_date": today,
            }
            item["stage"] = stage
            item["timeline"] = timeline
            updated[listing_id] = timeline
        self._store_json_memory("gtex-news:leaks", updated, ttl_seconds=STORY_MEMORY_TTL_SECONDS * 7)

    def _advance_arcs(self, data: dict[str, Any]) -> None:
        today = date.today().isoformat()
        memory = dict(self._load_json_memory("gtex-news:arcs") or {})
        updated: dict[str, Any] = dict(memory)
        arcs: list[dict[str, Any]] = []
        for item in data.get("transfers", []):
            player = dict(item.get("player") or {})
            player_id = str(player.get("id") or _stable_digest(player)[:16])
            club = str(item.get("target_club") or player.get("club") or "the market")
            arc_id = f"arc_{_stable_digest({'player_id': player_id, 'club': club})[:16]}"
            previous = dict(memory.get(arc_id) or {})
            progress = max(1, min(_int_value(previous.get("progress"), _int_value(item.get("stage"), 1)), 5))
            if previous.get("last_updated_date") != today:
                progress = min(5, progress + 1)
            arc = {
                "arc_id": arc_id,
                "arc_type": "transfer_drama",
                "progress": progress,
                "player": player,
                "club": club,
                "last_updated_date": today,
            }
            arcs.append(arc)
            updated[arc_id] = arc
        unhappy_players = [
            dict(player)
            for player in data.get("players", [])
            if dict(player).get("is_unhappy") or _int_value(dict(player).get("morale"), 50) < 35
        ]
        for player in unhappy_players[:4]:
            arc_id = f"arc_{_stable_digest({'player_id': player.get('id'), 'type': 'unrest'})[:16]}"
            previous = dict(memory.get(arc_id) or {})
            progress = max(1, min(_int_value(previous.get("progress"), 1), 5))
            if previous.get("last_updated_date") != today:
                progress = min(5, progress + 1)
            arc = {
                "arc_id": arc_id,
                "arc_type": "unrest",
                "progress": progress,
                "player": player,
                "club": player.get("club") or "the dressing room",
                "last_updated_date": today,
            }
            arcs.append(arc)
            updated[arc_id] = arc
        data["arcs"] = arcs
        self._store_json_memory("gtex-news:arcs", updated, ttl_seconds=STORY_MEMORY_TTL_SECONDS * 7)

    def _store_regen_lifecycle(self, players: list[dict[str, Any]]) -> None:
        memory = dict(self._load_json_memory("gtex-news:regen-lifecycle") or {})
        for player in players:
            if not dict(player).get("is_regen"):
                continue
            lifecycle = regen_lifecycle_stage(dict(player))
            player["lifecycle"] = lifecycle
            if player.get("id"):
                memory[str(player["id"])] = lifecycle
        self._store_json_memory("gtex-news:regen-lifecycle", memory, ttl_seconds=STORY_MEMORY_TTL_SECONDS * 7)

    def _rivalry_items(self, players: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
        rivalries: list[dict[str, Any]] = []
        for player in players:
            raw = dict(player)
            rivalry = dict(raw.get("rivalry") or {})
            hated_club = rivalry.get("hated_club")
            if not hated_club:
                continue
            rivalries.append(
                {
                    "player": raw,
                    "hated_club": hated_club,
                    "intensity": float(rivalry.get("intensity") or 0.5),
                }
            )
        return sorted(rivalries, key=lambda item: float(item.get("intensity") or 0), reverse=True)[:limit]

    def _regen_players(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(RegenProfile, Player, ClubProfile)
            .join(Player, RegenProfile.player_id == Player.id)
            .outerjoin(ClubProfile, RegenProfile.generated_for_club_id == ClubProfile.id)
            .where(RegenProfile.status == "active")
            .order_by(RegenProfile.current_gsi.desc(), RegenProfile.generated_at.desc())
            .limit(limit)
        ).all()
        return [self._player_state(player, regen=regen, club=club) for regen, player, club in rows]

    def _regen_awards(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(RegenAward, RegenProfile, Player, ClubProfile)
            .join(RegenProfile, RegenAward.regen_id == RegenProfile.id)
            .join(Player, RegenProfile.player_id == Player.id)
            .outerjoin(ClubProfile, RegenAward.club_id == ClubProfile.id)
            .order_by(RegenAward.awarded_at.desc(), RegenAward.impact_score.desc().nullslast())
            .limit(limit)
        ).all()
        return [
            {
                "award_name": award.award_name,
                "impact_score": award.impact_score,
                "player": self._player_state(player, regen=regen, club=club),
            }
            for award, regen, player, club in rows
        ]

    def _injury_items(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(InjuryStatus, Player)
            .join(Player, InjuryStatus.player_id == Player.id)
            .where(InjuryStatus.status.notin_(("fit", "cleared", "recovered")))
            .order_by(InjuryStatus.updated_at.desc())
            .limit(limit)
        ).all()
        return [
            {
                "detail": injury.detail,
                "expected_return_at": injury.expected_return_at,
                "player": self._player_state(player, injury=injury),
            }
            for injury, player in rows
        ]

    def _transfer_items(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(PlayerCardListing, PlayerCard, Player)
            .join(PlayerCard, PlayerCardListing.player_card_id == PlayerCard.id)
            .join(Player, PlayerCard.player_id == Player.id)
            .where(PlayerCardListing.status == "open")
            .order_by(PlayerCardListing.updated_at.desc())
            .limit(limit)
        ).all()
        items: list[dict[str, Any]] = []
        for listing, _card, player in rows:
            metadata = dict(listing.metadata_json or {})
            items.append(
                {
                    "listing_id": listing.listing_id,
                    "price": listing.price_per_card_credits,
                    "target_club": metadata.get("target_club") or "the user market",
                    "stage": metadata.get("leak_stage") or (3 if listing.is_negotiable else 2),
                    "deal_score": float(metadata.get("deal_score") or 0),
                    "player_agrees_terms": bool(metadata.get("player_agrees_terms")),
                    "club_funds_available": bool(metadata.get("club_funds_available")),
                    "player": self._player_state(player),
                }
            )
        return items

    def _loan_items(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(CardLoanListing, PlayerCard, Player)
            .join(PlayerCard, CardLoanListing.player_card_id == PlayerCard.id)
            .join(Player, PlayerCard.player_id == Player.id)
            .where(CardLoanListing.status == "open", CardLoanListing.available_slots > 0)
            .order_by(CardLoanListing.updated_at.desc())
            .limit(limit)
        ).all()
        return [
            {
                "listing_id": listing.id,
                "fee": listing.loan_fee_credits,
                "duration_days": listing.duration_days,
                "player": self._player_state(player),
            }
            for listing, _card, player in rows
        ]

    def _manager_items(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(ManagerTradeListing, ManagerHolding, ManagerCatalogEntry)
            .join(ManagerHolding, ManagerTradeListing.asset_id == ManagerHolding.asset_id)
            .join(ManagerCatalogEntry, ManagerHolding.manager_id == ManagerCatalogEntry.manager_id)
            .where(ManagerTradeListing.status == "open")
            .order_by(ManagerTradeListing.updated_at.desc())
            .limit(limit)
        ).all()
        return [
            {
                "manager_id": manager.manager_id,
                "asset_id": holding.asset_id,
                "name": manager.display_name,
                "rarity": manager.rarity,
                "mentality": manager.mentality,
                "tactics": list(manager.tactics or []),
                "traits": list(manager.traits or []),
                "price": listing.asking_price_credits,
            }
            for listing, holding, manager in rows
        ]

    def _club_sale_items(self, *, limit: int) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        transfer_rows = self.session.execute(
            select(ClubSaleTransfer, ClubProfile)
            .join(ClubProfile, ClubSaleTransfer.club_id == ClubProfile.id)
            .where(ClubSaleTransfer.status == "settled")
            .order_by(ClubSaleTransfer.created_at.desc())
            .limit(limit)
        ).all()
        for transfer, club in transfer_rows:
            items.append(
                {
                    "club_id": club.id,
                    "club_name": club.club_name,
                    "state": "settled",
                    "price": transfer.executed_sale_price,
                    "listing_id": transfer.listing_id,
                }
            )
        listing_rows = self.session.execute(
            select(ClubSaleListing, ClubProfile)
            .join(ClubProfile, ClubSaleListing.club_id == ClubProfile.id)
            .where(ClubSaleListing.status.in_(("active", "under_offer")))
            .order_by(ClubSaleListing.updated_at.desc())
            .limit(limit)
        ).all()
        for listing, club in listing_rows:
            items.append(
                {
                    "club_id": club.id,
                    "club_name": club.club_name,
                    "state": _status_value(listing.status) or "active",
                    "price": listing.asking_price,
                    "listing_id": listing.listing_id,
                }
            )
        offer_rows = self.session.execute(
            select(ClubSaleOffer, ClubProfile)
            .join(ClubProfile, ClubSaleOffer.club_id == ClubProfile.id)
            .where(ClubSaleOffer.status == "accepted")
            .order_by(ClubSaleOffer.updated_at.desc())
            .limit(limit)
        ).all()
        for offer, club in offer_rows:
            items.append(
                {
                    "club_id": club.id,
                    "club_name": club.club_name,
                    "state": "accepted",
                    "price": offer.offered_price,
                    "listing_id": offer.listing_id,
                }
            )
        return items[:limit]

    def _competition_items(self, *, limit: int) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        user_rows = self.session.scalars(
            select(UserCompetition)
            .where(
                UserCompetition.status.in_(("registration", "open", "launched", "active", "running")),
                or_(UserCompetition.visibility == "public", UserCompetition.visibility.is_(None)),
            )
            .order_by(UserCompetition.updated_at.desc())
            .limit(limit)
        ).all()
        for competition in user_rows:
            items.append(
                {
                    "id": competition.id,
                    "kind": "user_hosted",
                    "name": competition.name,
                    "status": competition.status,
                    "format": competition.format,
                }
            )
        hosted_rows = self.session.scalars(
            select(UserHostedCompetition)
            .where(
                UserHostedCompetition.status.in_(
                    (
                        HostedCompetitionStatus.OPEN,
                        HostedCompetitionStatus.LOCKED,
                        HostedCompetitionStatus.LIVE,
                    )
                ),
                or_(UserHostedCompetition.visibility == "public", UserHostedCompetition.visibility.is_(None)),
            )
            .order_by(UserHostedCompetition.updated_at.desc())
            .limit(limit)
        ).all()
        for competition in hosted_rows:
            items.append(
                {
                    "id": competition.id,
                    "kind": "platform_hosted",
                    "name": competition.title,
                    "status": _status_value(competition.status),
                    "format": "hosted",
                }
            )
        return items[:limit]

    def _player_state(
        self,
        player: Player,
        *,
        regen: RegenProfile | None = None,
        club: ClubProfile | None = None,
        injury: InjuryStatus | None = None,
    ) -> dict[str, Any]:
        regen = regen or self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id).limit(1))
        club_name = club.club_name if club is not None else player.real_world_club_name
        potential = _potential_from_regen(regen)
        stats = self._latest_stats(player.id)
        value = self._latest_market_value(player.id)
        morale = _int_value(getattr(player, "morale", 50), 50)
        hidden_state = dict(getattr(player, "dna_profile", None) or {})
        loyalty = _int_value(hidden_state.get("loyalty"), 55 + int((potential or 0) / 10))
        is_unhappy = bool(hidden_state.get("is_unhappy")) or morale < 35
        rivalry = dict(hidden_state.get("rivalry") or {})
        hated_club = hidden_state.get("hated_club") or rivalry.get("hated_club")
        if hated_club:
            rivalry = {
                "player_id": player.id,
                "hated_club": hated_club,
                "intensity": float(rivalry.get("intensity") or hidden_state.get("rivalry_intensity") or 0.65),
            }
        form = "normal"
        if _int_value(stats.get("goals_last_3"), 0) >= 5 or (regen is not None and regen.current_gsi >= 82):
            form = "hot"
        elif morale < 35:
            form = "cold"
        state = {
            "id": player.id,
            "name": _player_name(player),
            "club": club_name,
            "potential": potential,
            "form": form,
            "morale": morale,
            "is_regen": bool(regen is not None or not player.is_real_player),
            "is_unhappy": is_unhappy,
            "loyalty": max(1, min(loyalty, 100)),
            "current_gsi": regen.current_gsi if regen is not None else _int_value(hidden_state.get("gsi"), 0),
            "goals_last_3": stats.get("goals_last_3"),
            "market_value": value,
            "injured": injury is not None,
            "transfer_blocked": bool(hidden_state.get("transfer_blocked")),
            "rivalry": rivalry,
        }
        state["lifecycle"] = regen_lifecycle_stage(state) if state["is_regen"] else None
        state["market_value_projection"] = update_value(state)
        return state

    def _latest_stats(self, player_id: str) -> dict[str, Any]:
        snapshot = self.session.scalar(
            select(PlayerStatsSnapshot)
            .where(PlayerStatsSnapshot.player_id == player_id)
            .order_by(PlayerStatsSnapshot.as_of.desc())
            .limit(1)
        )
        stats = dict(snapshot.stats_json or {}) if snapshot is not None else {}
        goals_last_3 = stats.get("goals_last_3") or stats.get("goals_recent") or stats.get("recent_goals") or 0
        stats["goals_last_3"] = _int_value(goals_last_3)
        return stats

    def _latest_market_value(self, player_id: str) -> dict[str, Any] | None:
        snapshot = self.session.scalar(
            select(PlayerMarketValueSnapshot)
            .where(PlayerMarketValueSnapshot.player_id == player_id)
            .order_by(PlayerMarketValueSnapshot.as_of.desc())
            .limit(1)
        )
        if snapshot is None:
            return None
        return {
            "last_trade_price_credits": _amount(snapshot.last_trade_price_credits),
            "avg_trade_price_credits": _amount(snapshot.avg_trade_price_credits),
            "listing_floor_price_credits": _amount(snapshot.listing_floor_price_credits),
            "listing_count": snapshot.listing_count,
        }

    def _group_stories(self, stories: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        stamped = []
        generated_at = utcnow().isoformat()
        for story in _dedupe_and_sort(stories)[:DEFAULT_STORY_LIMIT]:
            item = dict(story)
            item["created_at"] = item.get("created_at") or generated_at
            stamped.append(item)
        breaking = [story for story in stamped if int(story.get("priority") or 0) >= 8][:5]
        breaking_ids = {story["id"] for story in breaking}
        rumors = [
            story
            for story in stamped
            if story["id"] not in breaking_ids and story.get("type") in {"transfer", "drama", "club_sale", "arc"}
        ][:6]
        assigned_ids = breaking_ids | {story["id"] for story in rumors}
        top_limit = max(0, DEFAULT_STORY_LIMIT - len(breaking) - len(rumors))
        top_stories = [story for story in stamped if story["id"] not in assigned_ids][:top_limit]
        return {
            "breaking": breaking,
            "top_stories": top_stories,
            "rumors": rumors,
        }

    def _daily_cache_key(self, scope: str) -> str:
        return f"gtex-news:{scope}:{date.today().isoformat()}"

    def _apply_story_memory(self, stories: list[dict[str, Any]], *, scope: str) -> list[dict[str, Any]]:
        memory_key = f"gtex-news:story-memory:{scope}"
        now = utcnow()
        raw_memory = list(self._load_json_memory(memory_key) or [])
        fresh_memory = [
            dict(item)
            for item in raw_memory
            if _parse_datetime(item.get("created_at")) >= now - timedelta(seconds=STORY_MEMORY_TTL_SECONDS)
        ]
        used_hashes = {str(item.get("hash")) for item in fresh_memory if item.get("hash")}
        accepted: list[dict[str, Any]] = []
        new_memory = list(fresh_memory)
        for story in _dedupe_and_sort(stories):
            mutated = dict(story)
            for mutation_index in range(len(HEADLINE_MUTATIONS) + 1):
                headline_hash = _headline_hash(mutated)
                if headline_hash not in used_hashes:
                    metadata = dict(mutated.get("metadata") or {})
                    metadata["story_memory"] = {
                        "hash": headline_hash,
                        "mutation_index": mutation_index,
                        "dedupe_window_hours": 48,
                    }
                    mutated["metadata"] = metadata
                    mutated["id"] = f"news_{_stable_digest({'headline': mutated.get('headline'), 'player_id': mutated.get('player_id'), 'mutation': mutation_index})[:20]}"
                    accepted.append(mutated)
                    used_hashes.add(headline_hash)
                    new_memory.append(
                        {
                            "hash": headline_hash,
                            "headline": mutated.get("headline"),
                            "created_at": now.isoformat(),
                        }
                    )
                    break
                mutated = _mutate_story(mutated, mutation_index)
            if len(accepted) >= DEFAULT_STORY_LIMIT:
                break
        self._store_json_memory(memory_key, new_memory[-200:], ttl_seconds=STORY_MEMORY_TTL_SECONDS)
        return accepted

    def _load_json_memory(self, key: str) -> Any | None:
        raw = self.cache_backend.get(key)
        if raw is None:
            local = _LOCAL_MEMORY.get(key)
            if local is None:
                return None
            expires_at, payload = local
            if expires_at <= utcnow():
                _LOCAL_MEMORY.pop(key, None)
                return None
            return payload
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("gtex_news.memory.decode_failed", extra={"key": key})
            return None

    def _store_json_memory(self, key: str, payload: Any, *, ttl_seconds: int) -> None:
        self.cache_backend.set(key, json.dumps(payload, default=str), ttl_seconds)
        if isinstance(self.cache_backend, NullCacheBackend) or not getattr(self.cache_backend, "enabled", False):
            _LOCAL_MEMORY[key] = (utcnow() + timedelta(seconds=ttl_seconds), payload)

    def _get_cached(self, key: str) -> Any | None:
        raw = self.cache_backend.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("gtex_news.cache.decode_failed", extra={"key": key})
            return None

    def _enforce_daily_user_limit(self, user_id: str) -> None:
        key = f"gtex-news:rate:user:{user_id}:{date.today().isoformat()}"
        count = self.cache_backend.increment(key, 1, ttl_seconds=NEWS_TTL_SECONDS)
        if count and count > USER_DAILY_LIMIT:
            raise GTEXNewsRateLimitError("Daily news generation limit reached.", limit=USER_DAILY_LIMIT)

    def _enforce_listing_limit(self, listing_id: str) -> None:
        key = f"gtex-news:rate:listing:{listing_id}:{date.today().isoformat()}"
        count = self.cache_backend.increment(key, 1, ttl_seconds=NEWS_TTL_SECONDS)
        if count and count > LISTING_DAILY_LIMIT:
            raise GTEXNewsRateLimitError("Listing news generation limit reached.", limit=LISTING_DAILY_LIMIT)


def _potential_from_regen(regen: RegenProfile | None) -> int:
    if regen is None:
        return 0
    raw = dict(regen.potential_range_json or {})
    return _int_value(raw.get("maximum") or raw.get("max") or raw.get("high") or raw.get("upper"), regen.current_gsi)


__all__ = [
    "GTEXNewsEngineService",
    "GTEXNewsRateLimitError",
    "apply_bias",
    "chaos_event_story",
    "club_personality",
    "dressing_room_story",
    "generate_daily_news",
    "generate_listing",
    "here_we_go_story",
    "manager_career_snapshot",
    "narrative_arc_story",
    "progressive_transfer_leak",
    "pundit_reaction",
    "regen_lifecycle_stage",
    "regen_hype",
    "transfer_leak",
    "update_value",
]
