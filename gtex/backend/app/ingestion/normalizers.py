from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any, Iterable

from .models import MAJOR_COMPETITIONS
from .schemas import (
    ClubUpsert,
    CompetitionUpsert,
    CountryUpsert,
    MatchUpsert,
    PlayerClubTenureUpsert,
    PlayerMatchStatUpsert,
    PlayerSeasonStatUpsert,
    PlayerUpsert,
    RecentUpdate,
    RecentUpdateFeed,
    SeasonUpsert,
    TeamStandingUpsert,
)

WHITESPACE_RE = re.compile(r"\s+")
DIGIT_RE = re.compile(r"(\d+)")

COUNTRY_ALIASES = {
    "england": "England",
    "spain": "Spain",
    "cote d'ivoire": "Ivory Coast",
    "côte d’ivoire": "Ivory Coast",
    "usa": "United States",
    "united states of america": "United States",
}

COMPETITION_ALIASES = {
    "uefa club championship": "UEFA Champions League",
    "premier league ": "Premier League",
}

CLUB_ALIASES = {
    "man united": "Manchester United",
    "man utd": "Manchester United",
    "spurs": "Tottenham Hotspur",
}

LEAGUE_A_COMPETITIONS = MAJOR_COMPETITIONS

POSITION_ALIASES = {
    "goalkeeper": "GK",
    "keeper": "GK",
    "centre-back": "CB",
    "center-back": "CB",
    "central defender": "CB",
    "left-back": "FB",
    "right-back": "FB",
    "full-back": "FB",
    "defensive midfield": "DM",
    "midfielder": "CM",
    "central midfield": "CM",
    "attacking midfield": "AM",
    "left winger": "WINGER",
    "right winger": "WINGER",
    "winger": "WINGER",
    "centre-forward": "ST",
    "center-forward": "ST",
    "striker": "ST",
}


def clean_name(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = WHITESPACE_RE.sub(" ", value).strip()
    return collapsed or None


def slugify(value: str | None) -> str:
    cleaned = clean_name(value) or "unknown"
    lowered = cleaned.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "unknown"


def normalize_country_name(value: str | None) -> str | None:
    cleaned = clean_name(value)
    if not cleaned:
        return None
    return COUNTRY_ALIASES.get(cleaned.lower(), cleaned)


def normalize_competition_name(value: str | None) -> str | None:
    cleaned = clean_name(value)
    if not cleaned:
        return None
    return COMPETITION_ALIASES.get(cleaned.lower(), cleaned)


def normalize_club_name(value: str | None) -> str | None:
    cleaned = clean_name(value)
    if not cleaned:
        return None
    return CLUB_ALIASES.get(cleaned.lower(), cleaned)


def normalize_position(value: str | None) -> str | None:
    cleaned = clean_name(value)
    if not cleaned:
        return None
    normalized = POSITION_ALIASES.get(cleaned.lower())
    if normalized:
        return normalized
    compact = cleaned.upper()
    if compact in {"GK", "CB", "FB", "DM", "CM", "AM", "WINGER", "ST"}:
        return compact
    return compact[:16]


def parse_date(value: Any) -> date | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_measurement(value: Any) -> int | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = DIGIT_RE.search(str(value))
    return int(match.group(1)) if match else None


def parse_money(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = DIGIT_RE.search(str(value).replace(",", ""))
    return float(match.group(1)) if match else None


def infer_internal_league_code(*, competition_name: str, competition_type: str) -> str:
    normalized_name = (competition_name or "").strip().lower()
    normalized_type = (competition_type or "").strip().lower()
    if normalized_name in LEAGUE_A_COMPETITIONS:
        return "league_a"
    if normalized_type == "league":
        return "league_b"
    if normalized_type == "cup":
        return "league_c"
    return "league_d"


def estimate_player_profile_completeness(payload: dict[str, Any]) -> float:
    candidate_values = (
        payload.get("name") or payload.get("fullName") or payload.get("displayName"),
        payload.get("firstName"),
        payload.get("lastName"),
        payload.get("shortName") or payload.get("shirtName"),
        payload.get("position"),
        payload.get("dateOfBirth") or payload.get("birthDate"),
        payload.get("nationality") or payload.get("country") or payload.get("countryName"),
        payload.get("height"),
        payload.get("weight"),
        payload.get("preferredFoot"),
        payload.get("shirtNumber"),
        payload.get("marketValueEur") or payload.get("marketValue") or payload.get("valueEur"),
    )
    present = sum(1 for value in candidate_values if value not in (None, "", "null"))
    return round(present / len(candidate_values), 4)


def _season_label(start_date: date | None, end_date: date | None, fallback: str | None = None) -> str:
    if fallback:
        cleaned = clean_name(fallback)
        if cleaned:
            return cleaned
    if start_date and end_date:
        return f"{start_date.year}/{str(end_date.year)[-2:]}"
    if start_date:
        return str(start_date.year)
    return "unknown"


def normalize_country_payload(provider_name: str, payload: dict[str, Any]) -> CountryUpsert:
    return CountryUpsert(
        provider_name=provider_name,
        provider_external_id=str(payload.get("id") or payload.get("countryId") or payload.get("code") or payload.get("name")),
        name=normalize_country_name(payload.get("name")) or "Unknown Country",
        alpha2_code=clean_name(payload.get("countryCode") or payload.get("alpha2Code")),
        alpha3_code=clean_name(payload.get("code") or payload.get("alpha3Code")),
        flag_url=payload.get("flag") or payload.get("flagUrl"),
    )


def normalize_competition_payload(provider_name: str, payload: dict[str, Any]) -> CompetitionUpsert:
    area = payload.get("area") or {}
    competition_name = normalize_competition_name(payload.get("name")) or "Unknown Competition"
    competition_type = clean_name(payload.get("type") or payload.get("competitionType") or "league") or "league"
    current_season = payload.get("currentSeason") or payload.get("season") or {}
    return CompetitionUpsert(
        provider_name=provider_name,
        provider_external_id=str(payload.get("id") or payload.get("competitionId") or competition_name),
        name=competition_name,
        slug=slugify(competition_name),
        code=clean_name(payload.get("code")),
        country_provider_external_id=str(area.get("id")) if area.get("id") is not None else None,
        country_name=normalize_country_name(area.get("name")),
        internal_league_code=clean_name(payload.get("internalLeagueCode"))
        or infer_internal_league_code(
            competition_name=competition_name,
            competition_type=competition_type,
        ),
        competition_type=competition_type,
        gender=clean_name(payload.get("gender")),
        emblem_url=payload.get("emblem") or payload.get("emblemUrl"),
        is_major=competition_name.lower() in MAJOR_COMPETITIONS,
        current_season_external_id=str(current_season.get("id")) if current_season.get("id") is not None else None,
    )


def normalize_season_payload(
    provider_name: str,
    payload: dict[str, Any],
    *,
    competition_external_id: str,
) -> SeasonUpsert:
    start_date = parse_date(payload.get("startDate") or payload.get("start_date"))
    end_date = parse_date(payload.get("endDate") or payload.get("end_date"))
    provider_external_id = str(payload.get("id") or payload.get("seasonId") or payload.get("year") or competition_external_id)
    return SeasonUpsert(
        provider_name=provider_name,
        provider_external_id=provider_external_id,
        competition_provider_external_id=competition_external_id,
        label=_season_label(start_date, end_date, payload.get("label") or payload.get("displayName")),
        year_start=payload.get("yearStart") or payload.get("year_start") or (start_date.year if start_date else None),
        year_end=payload.get("yearEnd") or payload.get("year_end") or (end_date.year if end_date else None),
        start_date=start_date,
        end_date=end_date,
        is_current=bool(payload.get("current") or payload.get("isCurrent")),
        current_matchday=payload.get("currentMatchday"),
    )


def normalize_club_payload(provider_name: str, payload: dict[str, Any]) -> ClubUpsert:
    area = payload.get("area") or payload.get("country") or {}
    club_name = normalize_club_name(payload.get("name")) or "Unknown Club"
    return ClubUpsert(
        provider_name=provider_name,
        provider_external_id=str(payload.get("id") or payload.get("teamId") or club_name),
        name=club_name,
        slug=slugify(club_name),
        short_name=clean_name(payload.get("shortName") or payload.get("short_name") or payload.get("tla")),
        code=clean_name(payload.get("tla") or payload.get("code")),
        country_provider_external_id=str(area.get("id")) if area.get("id") is not None else None,
        country_name=normalize_country_name(area.get("name") or payload.get("countryName")),
        founded_year=payload.get("founded"),
        website=clean_name(payload.get("website")),
        venue=clean_name(payload.get("venue")),
        crest_url=payload.get("crest") or payload.get("crestUrl"),
    )


def normalize_player_payload(
    provider_name: str,
    payload: dict[str, Any],
    *,
    club_external_id: str | None = None,
) -> PlayerUpsert:
    full_name = clean_name(payload.get("name") or payload.get("fullName") or payload.get("displayName")) or "Unknown Player"
    country = normalize_country_name(payload.get("nationality") or payload.get("country") or payload.get("countryName"))
    return PlayerUpsert(
        provider_name=provider_name,
        provider_external_id=str(payload.get("id") or payload.get("playerId") or full_name),
        full_name=full_name,
        first_name=clean_name(payload.get("firstName")),
        last_name=clean_name(payload.get("lastName")),
        short_name=clean_name(payload.get("shortName") or payload.get("shirtName")),
        country_name=country,
        country_provider_external_id=str(payload.get("countryId")) if payload.get("countryId") is not None else None,
        current_club_provider_external_id=club_external_id or (str(payload.get("currentTeamId")) if payload.get("currentTeamId") else None),
        position=clean_name(payload.get("position")),
        normalized_position=normalize_position(payload.get("position")),
        date_of_birth=parse_date(payload.get("dateOfBirth") or payload.get("birthDate")),
        height_cm=parse_measurement(payload.get("height")),
        weight_kg=parse_measurement(payload.get("weight")),
        preferred_foot=clean_name(payload.get("preferredFoot")),
        shirt_number=payload.get("shirtNumber"),
        market_value_eur=parse_money(
            payload.get("marketValueEur") or payload.get("marketValue") or payload.get("valueEur")
        ),
        profile_completeness_score=estimate_player_profile_completeness(payload),
    )


def build_player_tenure_payload(
    provider_name: str,
    player: PlayerUpsert,
    *,
    club_external_id: str,
    season_external_id: str | None,
) -> PlayerClubTenureUpsert:
    season_suffix = season_external_id or "current"
    return PlayerClubTenureUpsert(
        provider_name=provider_name,
        provider_external_id=f"{player.provider_external_id}:{club_external_id}:{season_suffix}",
        player_provider_external_id=player.provider_external_id,
        club_provider_external_id=club_external_id,
        season_provider_external_id=season_external_id,
        squad_number=player.shirt_number,
        is_current=True,
    )


def normalize_match_payload(
    provider_name: str,
    payload: dict[str, Any],
    *,
    competition_external_id: str | None = None,
    season_external_id: str | None = None,
) -> MatchUpsert:
    competition = payload.get("competition") or {}
    season = payload.get("season") or {}
    home_team = payload.get("homeTeam") or payload.get("home_team") or {}
    away_team = payload.get("awayTeam") or payload.get("away_team") or {}
    score = payload.get("score") or {}
    full_time = score.get("fullTime") or {}
    winner = payload.get("winner") or payload.get("winningTeam") or {}
    return MatchUpsert(
        provider_name=provider_name,
        provider_external_id=str(payload.get("id") or payload.get("matchId") or payload.get("fixture_id")),
        competition_provider_external_id=competition_external_id or str(competition.get("id") or payload.get("competitionId")),
        season_provider_external_id=season_external_id or (
            str(season.get("id")) if season.get("id") is not None else None
        ),
        home_club_provider_external_id=str(home_team.get("id") or payload.get("homeTeamId")),
        away_club_provider_external_id=str(away_team.get("id") or payload.get("awayTeamId")),
        winner_club_provider_external_id=str(winner.get("id")) if winner.get("id") is not None else None,
        venue=clean_name(payload.get("venue")),
        kickoff_at=parse_datetime(payload.get("utcDate") or payload.get("kickoff_at")),
        status=(clean_name(payload.get("status")) or "scheduled").lower(),
        stage=clean_name(payload.get("stage")),
        matchday=payload.get("matchday"),
        home_score=full_time.get("home") if full_time else payload.get("homeScore"),
        away_score=full_time.get("away") if full_time else payload.get("awayScore"),
        last_provider_update_at=parse_datetime(payload.get("lastUpdated")),
    )


def normalize_team_standing_payload(
    provider_name: str,
    payload: dict[str, Any],
    *,
    competition_external_id: str,
    season_external_id: str | None,
    standing_type: str = "total",
) -> TeamStandingUpsert:
    team = payload.get("team") or {}
    provider_external_id = payload.get("id") or f"{competition_external_id}:{season_external_id}:{team.get('id')}:{standing_type}"
    return TeamStandingUpsert(
        provider_name=provider_name,
        provider_external_id=str(provider_external_id),
        competition_provider_external_id=competition_external_id,
        season_provider_external_id=season_external_id,
        club_provider_external_id=str(team.get("id") or payload.get("teamId")),
        standing_type=(clean_name(payload.get("type")) or standing_type).lower(),
        position=int(payload.get("position") or 0),
        played=int(payload.get("playedGames") or payload.get("played") or 0),
        won=int(payload.get("won") or 0),
        drawn=int(payload.get("draw") or payload.get("drawn") or 0),
        lost=int(payload.get("lost") or 0),
        goals_for=int(payload.get("goalsFor") or payload.get("goals_for") or 0),
        goals_against=int(payload.get("goalsAgainst") or payload.get("goals_against") or 0),
        goal_difference=int(payload.get("goalDifference") or payload.get("goal_difference") or 0),
        points=int(payload.get("points") or 0),
        form=clean_name(payload.get("form")),
    )


def normalize_player_stats_payload(
    provider_name: str,
    payload: dict[str, Any],
    *,
    player_external_id: str,
    club_external_id: str | None,
    competition_external_id: str | None,
    season_external_id: str | None,
) -> tuple[PlayerSeasonStatUpsert | None, list[PlayerMatchStatUpsert]]:
    season_summary = payload.get("season") or payload.get("summary") or {}
    match_stats: list[PlayerMatchStatUpsert] = []
    for match_payload in payload.get("matches", []):
        match_stats.append(
            PlayerMatchStatUpsert(
                provider_name=provider_name,
                provider_external_id=str(
                    match_payload.get("id") or match_payload.get("statId") or f"{player_external_id}:{match_payload.get('matchId')}"
                ),
                player_provider_external_id=player_external_id,
                match_provider_external_id=str(match_payload.get("matchId") or match_payload.get("id")),
                club_provider_external_id=club_external_id,
                competition_provider_external_id=competition_external_id,
                season_provider_external_id=season_external_id,
                appearances=int(match_payload.get("appearances") or 1),
                starts=int(match_payload.get("starts") or (1 if match_payload.get("started") else 0)),
                minutes=match_payload.get("minutes"),
                goals=match_payload.get("goals"),
                assists=match_payload.get("assists"),
                saves=match_payload.get("saves"),
                clean_sheet=match_payload.get("cleanSheet"),
                rating=float(match_payload["rating"]) if match_payload.get("rating") is not None else None,
                raw_position=clean_name(match_payload.get("position")),
            )
        )

    season_stat = None
    if season_summary:
        season_stat = PlayerSeasonStatUpsert(
            provider_name=provider_name,
            provider_external_id=str(
                season_summary.get("id")
                or season_summary.get("statId")
                or f"{player_external_id}:{competition_external_id or 'competition'}:{season_external_id or 'season'}"
            ),
            player_provider_external_id=player_external_id,
            club_provider_external_id=club_external_id,
            competition_provider_external_id=competition_external_id,
            season_provider_external_id=season_external_id,
            appearances=season_summary.get("appearances"),
            starts=season_summary.get("starts"),
            minutes=season_summary.get("minutes"),
            goals=season_summary.get("goals"),
            assists=season_summary.get("assists"),
            yellow_cards=season_summary.get("yellowCards"),
            red_cards=season_summary.get("redCards"),
            clean_sheets=season_summary.get("cleanSheets"),
            saves=season_summary.get("saves"),
            average_rating=float(season_summary["averageRating"]) if season_summary.get("averageRating") is not None else None,
        )
    return season_stat, match_stats


def normalize_recent_update_feed(provider_name: str, payload: dict[str, Any]) -> RecentUpdateFeed:
    updates = [
        RecentUpdate(
            entity_type=clean_name(item.get("entity_type") or item.get("entityType")) or "unknown",
            provider_external_id=str(item.get("id") or item.get("providerExternalId")),
            competition_provider_external_id=(
                str(item.get("competitionId")) if item.get("competitionId") is not None else None
            ),
            club_provider_external_id=str(item.get("clubId")) if item.get("clubId") is not None else None,
            season_provider_external_id=str(item.get("seasonId")) if item.get("seasonId") is not None else None,
        )
        for item in payload.get("updates", [])
    ]
    return RecentUpdateFeed(
        provider_name=provider_name,
        cursor_value=clean_name(payload.get("cursor")),
        next_cursor=clean_name(payload.get("next_cursor") or payload.get("nextCursor")),
        updates=updates,
    )


def flatten_standings(payload: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    standings = payload.get("standings")
    if isinstance(standings, list) and standings:
        for standing_group in standings:
            standing_type = clean_name(standing_group.get("type")) or "total"
            for row in standing_group.get("table", []):
                yield standing_type.lower(), row
        return
    for row in payload.get("table", []):
        yield "total", row
