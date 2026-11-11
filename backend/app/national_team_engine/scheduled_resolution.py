"""Calendar resolution for GTEX competitions.

Representative playoffs and later rounds stay open until a real score is
recorded. The lifecycle does not invent those scores.
"""

from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
from typing import Any

from app.models.base import utcnow
from app.models.national_team import NationalTeamCompetition, NationalTeamCompetitionEntry


def _lifecycle_error(detail: str, *, reason: str) -> None:
    from app.national_team_engine.competition_lifecycle_service import NationalCompetitionLifecycleError

    raise NationalCompetitionLifecycleError(detail, reason=reason)


class ScheduledResolutionMixin:
    def _uses_scheduled_resolution(self, competition: NationalTeamCompetition) -> bool:
        mode = str((competition.metadata_json or {}).get("resolution_mode") or "simulated").strip().lower()
        return mode == "scheduled"

    def _assert_representation_window_closed(self, competition: NationalTeamCompetition) -> None:
        if not self._uses_scheduled_resolution(competition):
            return
        closes = self._as_utc_datetime(competition.entry_closes_at)
        if closes is not None and closes > utcnow():
            _lifecycle_error(
                "Country playoffs start after the join deadline, and before the competition kicks off.",
                reason="entry_window_open",
            )

    def record_scheduled_match_result(
        self,
        *,
        competition_id: str,
        match_id: str,
        home_score: int,
        away_score: int,
        winner_entry_id: str | None = None,
    ) -> dict[str, Any]:
        if home_score < 0 or away_score < 0:
            _lifecycle_error("Match scores cannot be negative.", reason="invalid_match_score")
        competition = self._require_competition(competition_id)
        lifecycle_state = self._lifecycle_state(competition)
        pending = dict(lifecycle_state.get("pending_round") or {})
        matches = [dict(item) for item in list(pending.get("matches") or [])]
        target = next((item for item in matches if item.get("match_id") == match_id), None)
        if target is None:
            _lifecycle_error(
                "That scheduled match is not waiting for a result.",
                reason="scheduled_match_not_found",
            )
        if str(target.get("status") or "") == "played":
            _lifecycle_error("That match already has a result.", reason="scheduled_match_played")
        allow_draw = bool(target.get("allow_draw"))
        winner = winner_entry_id
        if home_score > away_score:
            winner = str(target.get("home_entry_id") or "")
        elif away_score > home_score:
            winner = str(target.get("away_entry_id") or "")
        elif not allow_draw:
            legal = {str(target.get("home_entry_id") or ""), str(target.get("away_entry_id") or "")}
            if winner not in legal:
                _lifecycle_error(
                    "A level knockout match needs the entry that won on penalties.",
                    reason="winner_required",
                )
        else:
            winner = None
        target.update(
            {
                "home_score": int(home_score),
                "away_score": int(away_score),
                "winner_entry_id": winner,
                "status": "played",
                "resolution": "penalties" if home_score == away_score and not allow_draw else "regular_time",
            }
        )
        pending["matches"] = [target if item.get("match_id") == match_id else item for item in matches]
        lifecycle_state["pending_round"] = pending
        competition.metadata_json = {
            **dict(competition.metadata_json or {}),
            "lifecycle_state": lifecycle_state,
        }
        self._remember_matches(competition, stage=str(pending.get("stage") or ""), matches=[target])
        self.session.flush()
        if self._pending_is_open(pending):
            return self.get_lifecycle_payload(competition_id=competition_id)
        return self.advance_lifecycle(competition_id=competition_id)

    def _progress_scheduled_stage(
        self,
        *,
        competition: NationalTeamCompetition,
        lifecycle_state: dict[str, Any],
        stage: str,
        entries: list[NationalTeamCompetitionEntry],
        entry_map: dict[str, NationalTeamCompetitionEntry],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        entries, entry_map = self._narrow_scheduled_field(
            stage=stage,
            entries=entries,
            entry_map=entry_map,
            lifecycle_state=lifecycle_state,
        )
        board = dict(lifecycle_state.get("scheduled_board") or {})
        if board.get("stage") != stage:
            board = self._fresh_board(stage=stage, entries=entries)
        pending = lifecycle_state.get("pending_round")
        if isinstance(pending, dict) and pending.get("stage") == stage and self._pending_is_open(pending):
            lifecycle_state["scheduled_board"] = board
            lifecycle_state["pending_round"] = pending
            return {"waiting": True, "lifecycle_state": lifecycle_state, "result": None}

        if isinstance(pending, dict) and pending.get("stage") == stage:
            board = self._fold_pending(board, pending, entry_map)
            lifecycle_state["pending_round"] = None

        finished = self._scheduled_stage_finished(board)
        if finished is not None:
            result, lifecycle_state = self._complete_scheduled_stage(
                competition=competition,
                lifecycle_state=lifecycle_state,
                stage=stage,
                board=board,
                entries=entries,
                entry_map=entry_map,
                profile=profile,
                result=finished,
            )
            return {"waiting": False, "lifecycle_state": lifecycle_state, "result": result}

        nxt = self._build_pending_round(
            competition=competition,
            stage=stage,
            board=board,
            entry_map=entry_map,
            profile=profile,
        )
        if not self._pending_is_open(nxt):
            if list(nxt.get("matches") or []):
                board = self._fold_pending(board, nxt, entry_map)
            finished = self._scheduled_stage_finished(board)
            if finished is None:
                finished = self._finish_without_open_matches(board, stage=stage)
            if finished is not None:
                result, lifecycle_state = self._complete_scheduled_stage(
                    competition=competition,
                    lifecycle_state=lifecycle_state,
                    stage=stage,
                    board=board,
                    entries=entries,
                    entry_map=entry_map,
                    profile=profile,
                    result=finished,
                )
                return {"waiting": False, "lifecycle_state": lifecycle_state, "result": result}
        lifecycle_state["scheduled_board"] = board
        lifecycle_state["pending_round"] = nxt
        return {"waiting": True, "lifecycle_state": lifecycle_state, "result": None}

    def _narrow_scheduled_field(
        self,
        *,
        stage: str,
        entries: list[NationalTeamCompetitionEntry],
        entry_map: dict[str, NationalTeamCompetitionEntry],
        lifecycle_state: dict[str, Any],
    ) -> tuple[list[NationalTeamCompetitionEntry], dict[str, NationalTeamCompetitionEntry]]:
        if stage == "pre_qualifier":
            return entries, entry_map
        if stage == "qualifier":
            chosen_ids = list(lifecycle_state.get("representative_entry_ids") or [])
        else:
            chosen_ids = list(
                lifecycle_state.get("qualified_entry_ids") or lifecycle_state.get("representative_entry_ids") or []
            )
        chosen = [entry_map[entry_id] for entry_id in chosen_ids if entry_id in entry_map]
        if len(chosen) < 2:
            return entries, entry_map
        return chosen, {entry.id: entry for entry in chosen}

    def _finish_without_open_matches(self, board: dict[str, Any], *, stage: str) -> dict[str, Any] | None:
        if stage == "qualifier" and list(board.get("played_matches") or []):
            return {"qualified_entry_ids": [], "groups": []}
        if stage != "tournament":
            return None
        advancing = [entry_id for entry_id in list(board.get("advancing_ids") or []) if entry_id]
        rounds = list(board.get("knockout_rounds") or [])
        if len(advancing) == 1:
            return {
                "groups": list(board.get("group_results") or []),
                "knockout_rounds": rounds,
                "champion_entry_id": advancing[0],
                "qualified_entry_ids": list(board.get("qualified_entry_ids") or advancing),
            }
        entry_ids = [entry_id for entry_id in list(board.get("entry_ids") or []) if entry_id]
        if len(entry_ids) == 1:
            return {
                "groups": list(board.get("group_results") or []),
                "knockout_rounds": rounds,
                "champion_entry_id": entry_ids[0],
                "qualified_entry_ids": list(board.get("qualified_entry_ids") or entry_ids),
            }
        return None

    def _fresh_board(self, *, stage: str, entries: list[NationalTeamCompetitionEntry]) -> dict[str, Any]:
        if stage == "pre_qualifier":
            remaining: dict[str, list[str]] = {}
            names: dict[str, str] = {}
            for entry in entries:
                remaining.setdefault(entry.country_code, []).append(entry.id)
                names[entry.country_code] = entry.country_name
            for country_code, entry_ids in remaining.items():
                remaining[country_code] = sorted(
                    entry_ids,
                    key=lambda entry_id: (
                        -self._entry_strength(next(item for item in entries if item.id == entry_id)),
                        entry_id,
                    ),
                )
            return {
                "stage": stage,
                "remaining": remaining,
                "country_names": names,
                "country_rounds": {},
                "round_number": 1,
            }
        return {
            "stage": stage,
            "phase": "group",
            "entry_ids": [entry.id for entry in entries],
            "played_matches": [],
            "knockout_rounds": [],
            "round_number": 1,
            "advancing_ids": [],
        }

    @staticmethod
    def _pending_is_open(pending: dict[str, Any]) -> bool:
        return any(
            str(match.get("status") or "") != "played" and not str(match.get("resolution") or "").endswith("_bye")
            for match in list(pending.get("matches") or [])
        )

    def _fold_pending(
        self,
        board: dict[str, Any],
        pending: dict[str, Any],
        entry_map: dict[str, NationalTeamCompetitionEntry],
    ) -> dict[str, Any]:
        matches = [dict(match) for match in list(pending.get("matches") or [])]
        if board.get("stage") == "pre_qualifier":
            remaining = {code: list(ids) for code, ids in dict(board.get("remaining") or {}).items()}
            country_rounds = {code: list(rounds) for code, rounds in dict(board.get("country_rounds") or {}).items()}
            by_country: dict[str, list[dict[str, Any]]] = {}
            for match in matches:
                country = str(match.get("home_country_code") or "")
                by_country.setdefault(country, []).append(match)
                winner_id = match.get("winner_entry_id")
                home_id = match.get("home_entry_id")
                away_id = match.get("away_entry_id")
                loser_id = None
                if winner_id and home_id and away_id:
                    loser_id = away_id if winner_id == home_id else home_id
                pool = remaining.get(country, [])
                if loser_id and loser_id in pool:
                    pool = [entry_id for entry_id in pool if entry_id != loser_id]
                    remaining[country] = pool
                    loser = entry_map.get(str(loser_id))
                    if loser is not None:
                        loser.status = "eliminated"
                        loser.qualified = False
            for country, country_matches in by_country.items():
                country_rounds.setdefault(country, []).append(
                    {"round": int(pending.get("round_number") or 1), "matches": country_matches}
                )
            board["remaining"] = remaining
            board["country_rounds"] = country_rounds
            board["round_number"] = int(board.get("round_number") or 1) + 1
            return board

        played = [dict(match) for match in list(board.get("played_matches") or [])]
        played.extend(matches)
        board["played_matches"] = played
        if board.get("phase") == "knockout":
            winners: list[str] = []
            for match in matches:
                winner_id = match.get("winner_entry_id")
                if winner_id:
                    winners.append(str(winner_id))
                loser_id = None
                home_id = match.get("home_entry_id")
                away_id = match.get("away_entry_id")
                if winner_id and home_id and away_id and winner_id in {home_id, away_id}:
                    loser_id = away_id if winner_id == home_id else home_id
                if loser_id and loser_id in entry_map and str(pending.get("round_label") or "") != "group":
                    entry_map[str(loser_id)].status = "eliminated"
            rounds = list(board.get("knockout_rounds") or [])
            rounds.append({"stage": str(pending.get("round_label") or "knockout"), "matches": matches})
            board["knockout_rounds"] = rounds
            board["advancing_ids"] = winners
        board["round_number"] = int(board.get("round_number") or 1) + 1
        return board

    def _scheduled_stage_finished(self, board: dict[str, Any]) -> dict[str, Any] | None:
        if board.get("stage") == "pre_qualifier":
            remaining = dict(board.get("remaining") or {})
            if not remaining:
                return {"representative_entry_ids": [], "countries": []}
            if any(len(ids) > 1 for ids in remaining.values()):
                return None
            countries = []
            representatives = []
            for country_code, entry_ids in sorted(remaining.items()):
                winner_id = entry_ids[0]
                representatives.append(winner_id)
                countries.append(
                    {
                        "country_code": country_code,
                        "country_name": dict(board.get("country_names") or {}).get(country_code, country_code),
                        "entrant_count": len(entry_ids),
                        "winner_entry_id": winner_id,
                        "rounds": list(dict(board.get("country_rounds") or {}).get(country_code) or []),
                    }
                )
            return {"representative_entry_ids": representatives, "countries": countries}

        if (
            board.get("phase") == "group_scheduled"
            and board.get("played_matches")
            and board.get("stage") == "qualifier"
        ):
            return {"qualified_entry_ids": [], "groups": []}

        if board.get("phase") == "knockout":
            advancing = [entry_id for entry_id in list(board.get("advancing_ids") or []) if entry_id]
            if len(advancing) == 1 and list(board.get("knockout_rounds") or []):
                return {
                    "groups": list(board.get("group_results") or []),
                    "knockout_rounds": list(board.get("knockout_rounds") or []),
                    "champion_entry_id": advancing[0],
                    "qualified_entry_ids": list(board.get("qualified_entry_ids") or advancing),
                }
        return None

    def _build_pending_round(
        self,
        *,
        competition: NationalTeamCompetition,
        stage: str,
        board: dict[str, Any],
        entry_map: dict[str, NationalTeamCompetitionEntry],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        if stage == "pre_qualifier":
            pairings: list[tuple[NationalTeamCompetitionEntry, NationalTeamCompetitionEntry | None]] = []
            for _country, entry_ids in sorted(dict(board.get("remaining") or {}).items()):
                pool = [entry_map[entry_id] for entry_id in entry_ids if entry_id in entry_map]
                if len(pool) < 2:
                    continue
                working: list[NationalTeamCompetitionEntry | None] = list(pool)
                while len(working) < self._next_power_of_two(len(working)):
                    working.append(None)
                for index in range(len(working) // 2):
                    home = working[index]
                    away = working[-(index + 1)]
                    if home is None and away is None:
                        continue
                    if home is None or away is None:
                        present = home or away
                        assert present is not None
                        pairings.append((present, None))
                    else:
                        pairings.append((home, away))
            return self._pending_from_pairings(
                competition=competition,
                stage=stage,
                round_number=int(board.get("round_number") or 1),
                round_label=f"round_{int(board.get('round_number') or 1)}",
                pairings=pairings,
                allow_draw=False,
            )

        if board.get("phase") == "group":
            entries = [entry_map[entry_id] for entry_id in list(board.get("entry_ids") or []) if entry_id in entry_map]
            if stage == "tournament" and len(entries) == 2:
                board["phase"] = "knockout"
                board["advancing_ids"] = [entry.id for entry in entries]
                return self._build_pending_round(
                    competition=competition,
                    stage=stage,
                    board=board,
                    entry_map=entry_map,
                    profile=profile,
                )
            group_size = int(profile["qualifier_group_size"] if stage == "qualifier" else profile["group_size"])
            group_count = max(1, min(len(entries), (len(entries) + max(group_size, 2) - 1) // max(group_size, 2)))
            groups = self._seed_groups(entries, max(1, group_count))
            board["groups"] = [[entry.id for entry in group] for group in groups]
            pairings = []
            for group in groups:
                for home_index in range(len(group)):
                    for away_index in range(home_index + 1, len(group)):
                        pairings.append((group[home_index], group[away_index]))
            board["phase"] = "group_scheduled"
            return self._pending_from_pairings(
                competition=competition,
                stage=stage,
                round_number=1,
                round_label="group",
                pairings=pairings,
                allow_draw=True,
            )

        if board.get("phase") == "group_scheduled":
            board["phase"] = "knockout" if stage == "tournament" else "qualify_ready"
            if stage == "qualifier":
                board["ready_to_qualify"] = True
                return {"stage": stage, "round_number": 0, "round_label": "group", "matches": []}
            entries = [entry_map[entry_id] for entry_id in list(board.get("entry_ids") or []) if entry_id in entry_map]
            group_ids = [list(group) for group in list(board.get("groups") or [])]
            groups = [[entry_map[entry_id] for entry_id in group if entry_id in entry_map] for group in group_ids]
            preset = {
                (str(match.get("home_entry_id")), str(match.get("away_entry_id"))): match
                for match in list(board.get("played_matches") or [])
            }
            group_results, ranked_rows = self._run_group_stage(
                competition=competition,
                stage_code=stage,
                groups=groups or [entries],
                advance_per_group=int(profile["advance_per_group"]),
                best_third_slots=int(profile["best_third_slots"]),
                preset_matches=preset,
            )
            board["group_results"] = group_results
            advancing = [str(row["entry_id"]) for row in ranked_rows]
            board["advancing_ids"] = advancing
            board["qualified_entry_ids"] = advancing
            return self._build_pending_round(
                competition=competition,
                stage=stage,
                board=board,
                entry_map=entry_map,
                profile=profile,
            )

        advancing_ids = [entry_id for entry_id in list(board.get("advancing_ids") or []) if entry_id in entry_map]
        if stage == "qualifier" and board.get("ready_to_qualify"):
            return {"stage": stage, "round_number": 0, "round_label": "group", "matches": []}
        pairings = []
        ordered = [entry_map[entry_id] for entry_id in advancing_ids]
        while len(ordered) < self._next_power_of_two(max(len(ordered), 1)):
            ordered.append(None)  # type: ignore[arg-type]
        real = [entry for entry in ordered if entry is not None]
        if len(real) <= 1:
            return {"stage": stage, "round_number": 0, "round_label": "final", "matches": []}
        field = [entry_map[entry_id] for entry_id in advancing_ids]
        bracket = list(field)
        while len(bracket) < self._next_power_of_two(len(bracket)):
            bracket.append(None)  # type: ignore[arg-type]
        pairs: list[tuple[NationalTeamCompetitionEntry, NationalTeamCompetitionEntry | None]] = []
        for index in range(0, len(bracket), 2):
            left = bracket[index]
            right = bracket[index + 1] if index + 1 < len(bracket) else None
            if left is None and right is None:
                continue
            if left is None or right is None:
                pairs.append((left or right, None))  # type: ignore[arg-type]
            else:
                pairs.append((left, right))
        label = self._round_label(len(bracket))
        return self._pending_from_pairings(
            competition=competition,
            stage=stage,
            round_number=int(board.get("round_number") or 1),
            round_label=label,
            pairings=pairs,
            allow_draw=False,
        )

    def _pending_from_pairings(
        self,
        *,
        competition: NationalTeamCompetition,
        stage: str,
        round_number: int,
        round_label: str,
        pairings: list[tuple[NationalTeamCompetitionEntry, NationalTeamCompetitionEntry | None]],
        allow_draw: bool,
    ) -> dict[str, Any]:
        matches = []
        for index, (home, away) in enumerate(pairings):
            if away is None:
                matches.append(self._bye_match(stage=stage, round_label=round_label, winner=home))
                continue
            match_id = sha256(f"{competition.id}|{stage}|{round_label}|{home.id}|{away.id}".encode()).hexdigest()[:24]
            matches.append(
                {
                    "match_id": match_id,
                    "stage": round_label,
                    "home_entry_id": home.id,
                    "home_user_id": home.user_id,
                    "home_country_code": home.country_code,
                    "home_country_name": home.country_name,
                    "away_entry_id": away.id,
                    "away_user_id": away.user_id,
                    "away_country_code": away.country_code,
                    "away_country_name": away.country_name,
                    "home_score": None,
                    "away_score": None,
                    "winner_entry_id": None,
                    "resolution": "scheduled",
                    "status": "scheduled",
                    "allow_draw": allow_draw,
                    "kickoff_at": self._scheduled_kickoff(competition, index, max(len(pairings), 1)).isoformat(),
                }
            )
        return {
            "stage": stage,
            "round_number": round_number,
            "round_label": round_label,
            "matches": matches,
        }

    def _scheduled_kickoff(self, competition: NationalTeamCompetition, index: int, total: int):
        start = self._as_utc_datetime(competition.entry_closes_at) or utcnow()
        end = self._as_utc_datetime(competition.kickoff_at)
        if end is not None and end > start:
            span = (end - start).total_seconds()
            return start + timedelta(seconds=span * (index + 1) / (total + 1))
        return start + timedelta(hours=index + 1)

    def _complete_scheduled_stage(
        self,
        *,
        competition: NationalTeamCompetition,
        lifecycle_state: dict[str, Any],
        stage: str,
        board: dict[str, Any],
        entries: list[NationalTeamCompetitionEntry],
        entry_map: dict[str, NationalTeamCompetitionEntry],
        profile: dict[str, Any],
        result: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if stage == "qualifier" or (
            stage == "tournament" and "qualified_entry_ids" not in result and board.get("phase") != "knockout"
        ):
            result = self._result_from_played_groups(
                competition=competition,
                stage=stage,
                board=board,
                entries=entries,
                entry_map=entry_map,
                profile=profile,
            )
        if stage == "pre_qualifier":
            representative_ids = list(result["representative_entry_ids"])
            for entry_id in representative_ids:
                winner = entry_map.get(entry_id)
                if winner is not None:
                    winner.status = "representative"
                    winner.qualified = False
            lifecycle_state["stage_results"]["pre_qualifier"] = result
            lifecycle_state["representative_entry_ids"] = representative_ids
            lifecycle_state["current_stage"] = (
                "qualifier" if len(representative_ids) > int(profile["tournament_slots"]) else "tournament"
            )
            self._append_stage_history(
                lifecycle_state,
                stage="pre_qualifier",
                summary=f"Resolved {len(representative_ids)} country representative(s).",
            )
            competition.status = "live"
        elif stage == "qualifier":
            qualified_ids = list(result["qualified_entry_ids"])
            lifecycle_state["stage_results"]["qualifier"] = result
            lifecycle_state["qualified_entry_ids"] = qualified_ids
            lifecycle_state["current_stage"] = "tournament"
            self._append_stage_history(
                lifecycle_state,
                stage="qualifier",
                summary=f"Advanced {len(qualified_ids)} team(s) into the tournament stage.",
            )
            for entry in entries:
                if entry.id in set(lifecycle_state.get("representative_entry_ids") or []):
                    entry.qualified = entry.id in qualified_ids
                    entry.status = "qualified" if entry.qualified else "eliminated"
            competition.status = "live"
        else:
            champion_id = result.get("champion_entry_id")
            lifecycle_state["stage_results"]["tournament"] = result
            lifecycle_state["champion_entry_id"] = champion_id
            lifecycle_state["current_stage"] = "completed"
            self._append_stage_history(
                lifecycle_state,
                stage="tournament",
                summary=f"Completed the tournament stage and crowned {self._entry_label(entry_map.get(champion_id))}.",
            )
            competition.status = "completed"
            competition.completed_at = utcnow()
            feeds_into = str(
                dict((competition.metadata_json or {}).get("qualification_chain") or {}).get("feeds_into_key") or ""
            ).strip()
            if feeds_into and not list(lifecycle_state.get("qualified_entry_ids") or []):
                representatives = [
                    entry_id for entry_id in list(lifecycle_state.get("representative_entry_ids") or []) if entry_id
                ]
                if not representatives:
                    representatives = [entry.id for entry in entries]
                if len(representatives) <= int(profile["tournament_slots"]):
                    lifecycle_state["qualified_entry_ids"] = representatives
            qualified_ids = {
                entry_id for entry_id in list(lifecycle_state.get("qualified_entry_ids") or []) if entry_id
            }
            for entry in entries:
                if champion_id and entry.id == champion_id:
                    entry.status = "champion"
                    entry.qualified = True
                elif entry.id in qualified_ids:
                    entry.status = "qualified"
                    entry.qualified = True
                elif entry.status != "eliminated":
                    entry.status = "eliminated"
        lifecycle_state["scheduled_board"] = {}
        lifecycle_state["pending_round"] = None
        return result, lifecycle_state

    def _result_from_played_groups(
        self,
        *,
        competition: NationalTeamCompetition,
        stage: str,
        board: dict[str, Any],
        entries: list[NationalTeamCompetitionEntry],
        entry_map: dict[str, NationalTeamCompetitionEntry],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        group_ids = [list(group) for group in list(board.get("groups") or [])]
        groups = [[entry_map[entry_id] for entry_id in group if entry_id in entry_map] for group in group_ids]
        if not groups:
            groups = [entries]
        preset = {
            (str(match.get("home_entry_id")), str(match.get("away_entry_id"))): match
            for match in list(board.get("played_matches") or [])
        }
        if stage == "qualifier":
            slots = int(profile["tournament_slots"])
            group_results, _ranked = self._run_group_stage(
                competition=competition,
                stage_code=stage,
                groups=groups,
                advance_per_group=1,
                best_third_slots=0,
                preset_matches=preset,
            )
            all_rows = [dict(row) for group in group_results for row in group["standings"]]
            all_rows.sort(
                key=lambda row: (
                    -int(row["group_rank"] == 1),
                    -int(row["points"]),
                    -int(row["goal_difference"]),
                    -int(row["goals_for"]),
                    -float(row["strength_rating"]),
                    row["country_name"].lower(),
                )
            )
            qualified_ids = [row["entry_id"] for row in all_rows[:slots]]
            return {
                "groups": group_results,
                "qualified_entry_ids": qualified_ids,
                "summary": f"Qualified {len(qualified_ids)} team(s) from played qualifier matches.",
            }
        return {
            "groups": list(board.get("group_results") or []),
            "knockout_rounds": list(board.get("knockout_rounds") or []),
            "champion_entry_id": (list(board.get("advancing_ids") or [None]) or [None])[0],
            "qualified_entry_ids": list(board.get("qualified_entry_ids") or []),
        }
