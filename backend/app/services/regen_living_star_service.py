"""Living-star layer for unique regens: archetype, voice, exit ladder, match brief."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from sqlalchemy.orm import Session

from app.models.player_agency_state import PlayerAgencyState
from app.models.player_personality import PlayerPersonality
from app.models.regen import RegenProfile
from app.schemas.player_agency import PlayerPersonalityView
from app.schemas.regen_living_star import (
    RegenArchetypeView,
    RegenExitLadderView,
    RegenExitPetitionView,
    RegenHeirSparkView,
    RegenInnerMonologueView,
    RegenLivingStarView,
    RegenMatchBehaviorBriefView,
    RegenMoodStatusView,
    RegenPromiseMemoryView,
)
from app.services.player_agency_service import PlayerAgencyService

_EXIT_STAGES: tuple[str, ...] = (
    "settled",
    "quiet_discontent",
    "formal_request",
    "training_exile",
    "termination_petition",
    "force_sale_window",
)

_EXIT_LABELS = {
    "settled": "Settled",
    "quiet_discontent": "Quiet discontent",
    "formal_request": "Formal transfer request",
    "training_exile": "Training exile risk",
    "termination_petition": "Contract termination petition",
    "force_sale_window": "Force-sale window",
}

_STATUS_FROM_TRANSFER = {
    "no_action": "settled",
    "watching": "quiet_discontent",
    "transfer_request": "formal_request",
    "public_unhappy_state": "training_exile",
    "strike_threat": "termination_petition",
    "forced_exit": "force_sale_window",
}


@dataclass(slots=True)
class RegenLivingStarService:
    session: Session

    def get_living_star(self, player_id: str) -> RegenLivingStarView:
        agency_service = PlayerAgencyService(self.session)
        snapshot = agency_service.get_snapshot(player_id)
        player, regen, personality, state, _ = agency_service.sync(player_id)
        archetype = self._archetype(personality)
        mood = self._mood(state, personality)
        monologue = self._monologue(player_id, personality, state, archetype, mood)
        exit_ladder = self._exit_ladder(state, personality)
        promises = self._promises(state)
        grievances = self._grievances(state)
        brief = self._behavior_brief(player_id, personality, state, mood)
        heir = self._heir_spark(regen)
        inbox = self._inbox_notes(mood, exit_ladder, promises, grievances, monologue)
        return RegenLivingStarView(
            player_id=player.id,
            regen_id=snapshot.regen_id or (regen.regen_id if regen is not None else None),
            is_unique_collectible=True,
            archetype=archetype,
            mood=mood,
            monologue=monologue,
            exit_ladder=exit_ladder,
            personality=self._personality_view(personality),
            agency=snapshot.state,
            promises=promises,
            grievances=grievances,
            behavior_brief=brief,
            heir_spark=heir,
            inbox_notes=inbox,
        )

    def get_behavior_brief(self, player_id: str) -> RegenMatchBehaviorBriefView:
        return self.get_living_star(player_id).behavior_brief

    def petition_exit(self, player_id: str, *, reason: str | None = None) -> RegenExitPetitionView:
        agency_service = PlayerAgencyService(self.session)
        _player, regen, personality, state, _ = agency_service.sync(player_id)
        if regen is None:
            raise KeyError(f"Player {player_id} is not a living regen star")
        previous = self._stage_from_state(state)
        if previous == "settled" and personality.loyalty >= 78 and personality.greed <= 40:
            # Loyal romantics do not jump straight to nuclear.
            next_stage = "quiet_discontent"
            state.transfer_request_status = "watching"
            accepted = True
            message = "They are unhappy, but loyalty keeps this off the front pages — for now."
        else:
            next_stage = self._escalate(previous, personality)
            state.transfer_request_status = self._transfer_status_for_stage(next_stage)
            accepted = True
            message = {
                "quiet_discontent": "Dressing-room silence. No formal request — yet.",
                "formal_request": "A formal transfer request has been lodged.",
                "training_exile": "They are refusing full training intensity.",
                "termination_petition": "They have petitioned to terminate the contract.",
                "force_sale_window": "Force-sale window is open. The story is public.",
                "settled": "No petition accepted.",
            }.get(next_stage, "Exit pressure updated.")
        if reason:
            unmet = list(state.unmet_expectations_json or [])
            unmet.append(
                {
                    "code": "exit_petition",
                    "text": reason.strip()[:280],
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            state.unmet_expectations_json = unmet[-12:]
        state.transfer_appetite = min(100.0, float(state.transfer_appetite) + 12.0)
        state.morale = max(0.0, float(state.morale) - 6.0)
        self.session.flush()
        living = self.get_living_star(player_id)
        try:
            from app.story_feed_engine.bridges import publish_exit_petition_story

            publish_exit_petition_story(
                self.session,
                player_id=player_id,
                stage=living.exit_ladder.stage,
                message=message,
                player_name=getattr(regen, "display_name", None),
                country_code=getattr(regen, "nationality_code", None),
                reason=reason,
            )
        except Exception:
            # Desk bridge must never block agency state transitions.
            pass
        return RegenExitPetitionView(
            player_id=player_id,
            previous_stage=previous,
            stage=living.exit_ladder.stage,
            accepted=accepted,
            message=message,
            living_star=living,
        )

    def _personality_view(self, personality: PlayerPersonality) -> PlayerPersonalityView:
        return PlayerPersonalityView(
            ambition=personality.ambition,
            loyalty=personality.loyalty,
            professionalism=personality.professionalism,
            greed=personality.greed,
            temperament=personality.temperament,
            patience=personality.patience,
            adaptability=personality.adaptability,
            competitiveness=personality.competitiveness,
            aggression=getattr(personality, "aggression", 50),
            confidence=getattr(personality, "confidence", 50),
            consistency=getattr(personality, "consistency", 50),
            clutch_factor=getattr(personality, "clutch_factor", 50),
            ego=personality.ego,
            development_focus=personality.development_focus,
            hometown_affinity=personality.hometown_affinity,
            trophy_hunger=personality.trophy_hunger,
            media_appetite=personality.media_appetite,
            default_career_target_band=personality.default_career_target_band,
        )

    def _archetype(self, p: PlayerPersonality) -> RegenArchetypeView:
        clutch = getattr(p, "clutch_factor", 50)
        aggression = getattr(p, "aggression", 50)
        scores: list[tuple[str, str, str, tuple[str, ...], int]] = [
            (
                "mercenary",
                "The Mercenary",
                "Chases wage spikes and will force a move when a bigger bid lands.",
                ("greed", "ambition"),
                p.greed + p.ambition - p.loyalty,
            ),
            (
                "one_club_romantic",
                "The One-Club Romantic",
                "Takes less to stay. Breaks if sold against their will.",
                ("loyalty", "hometown_affinity"),
                p.loyalty + p.hometown_affinity - p.greed,
            ),
            (
                "big_game_ghost",
                "The Big-Game Ghost",
                "Ordinary nights look fine; finals and derbies expose the nerves.",
                ("ego", "low_clutch"),
                p.ego + (100 - clutch) - p.professionalism // 2,
            ),
            (
                "clutch_animal",
                "The Clutch Animal",
                "Transforms when the lights are brightest. Never sell before a cup run.",
                ("clutch", "competitiveness"),
                clutch + p.competitiveness - p.consistency // 4,
            ),
            (
                "dressing_room_bomb",
                "The Dressing-Room Bomb",
                "Wins you games and costs you suspensions. Chemistry is fragile.",
                ("temperament", "aggression"),
                p.temperament + aggression - p.professionalism,
            ),
            (
                "media_hurricane",
                "The Media Hurricane",
                "Interviews move markets. Narrative is half the management job.",
                ("media_appetite", "ego"),
                p.media_appetite + p.ego - p.patience,
            ),
        ]
        code, label, summary, traits, _ = max(scores, key=lambda row: row[4])
        return RegenArchetypeView(code=code, label=label, summary=summary, dominant_traits=traits)

    def _mood(self, state: PlayerAgencyState, personality: PlayerPersonality) -> RegenMoodStatusView:
        unrest = (
            (100.0 - float(state.happiness))
            + (100.0 - float(state.wage_satisfaction)) * 0.8
            + (100.0 - float(state.playing_time_satisfaction)) * 0.9
            + float(state.transfer_appetite) * 0.7
            + float(state.grievance_count) * 8.0
        )
        drivers: list[str] = []
        if state.wage_satisfaction < 45:
            drivers.append("wage dissatisfaction")
        if state.playing_time_satisfaction < 45:
            drivers.append("lack of minutes")
        if state.club_project_belief < 40:
            drivers.append("lost belief in the project")
        if state.grievance_count > 0:
            drivers.append(f"{state.grievance_count} open grievances")
        if state.transfer_request_status not in {"no_action", "watching"}:
            drivers.append("active exit pressure")
        if unrest >= 160 or state.transfer_request_status in {"strike_threat", "forced_exit", "public_unhappy_state"}:
            code, label, severity = "explosive", "Explosive", 3
        elif unrest >= 95 or personality.temperament > 75 and state.happiness < 55:
            code, label, severity = "restless", "Restless", 2
        else:
            code, label, severity = "settled", "Settled", 0 if unrest < 40 else 1
            if severity == 1:
                label = "Watching"
                code = "watching"
        return RegenMoodStatusView(code=code, label=label, severity=severity, drivers=tuple(drivers[:4]))

    def _monologue(
        self,
        player_id: str,
        personality: PlayerPersonality,
        state: PlayerAgencyState,
        archetype: RegenArchetypeView,
        mood: RegenMoodStatusView,
    ) -> RegenInnerMonologueView:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        seed = hashlib.sha256(f"{player_id}:{day}:{archetype.code}:{mood.code}".encode()).hexdigest()[:12]
        lines = {
            ("mercenary", "explosive"): "I see the offers. If this club will not match them, I walk.",
            ("mercenary", "restless"): "I am producing. The wage does not match the output.",
            ("one_club_romantic", "explosive"): "I bled for this shirt. Selling me would end something permanent.",
            ("one_club_romantic", "restless"): "I want to stay — but I need to feel wanted here.",
            ("big_game_ghost", "explosive"): "Everyone talks about the final. Leave me alone.",
            ("big_game_ghost", "restless"): "The derby is coming. I can feel the weight already.",
            ("clutch_animal", "explosive"): "Bench me in a final and this relationship is over.",
            ("clutch_animal", "restless"): "Give me the big nights. That is what I am for.",
            ("dressing_room_bomb", "explosive"): "If the captain talks again, this will get ugly.",
            ("dressing_room_bomb", "restless"): "Training is soft. Someone needs to wake this place up.",
            ("media_hurricane", "explosive"): "I will say what I think. The club can deal with the headlines.",
            ("media_hurricane", "restless"): "People ask me questions. I am done protecting the narrative.",
        }
        voice = lines.get((archetype.code, mood.code))
        if voice is None:
            if mood.code == "settled":
                voice = "The project still feels real. I am in."
            elif state.playing_time_satisfaction < 40:
                voice = "I scored when I played. Sitting is not development."
            elif state.wage_satisfaction < 40:
                voice = "Respect shows up on the contract as much as in the huddle."
            else:
                voice = "I am watching how this club treats people like me."
        tone = {
            "settled": "calm",
            "watching": "wary",
            "restless": "tense",
            "explosive": "hostile",
        }.get(mood.code, "wary")
        return RegenInnerMonologueView(
            voice_line=voice,
            tone=tone,
            generated_at=datetime.now(timezone.utc),
            seed=seed,
        )

    def _stage_from_state(self, state: PlayerAgencyState) -> str:
        return _STATUS_FROM_TRANSFER.get(state.transfer_request_status, "quiet_discontent")

    def _exit_ladder(self, state: PlayerAgencyState, personality: PlayerPersonality) -> RegenExitLadderView:
        stage = self._stage_from_state(state)
        idx = _EXIT_STAGES.index(stage) if stage in _EXIT_STAGES else 1
        next_stage = _EXIT_STAGES[idx + 1] if idx + 1 < len(_EXIT_STAGES) else None
        can_terminate = idx >= 2 and (personality.loyalty < 70 or personality.greed >= 60 or personality.ego >= 70)
        actions: list[str] = []
        if stage == "settled":
            actions.extend(["praise publicly", "protect minutes", "keep promises"])
        elif stage == "quiet_discontent":
            actions.extend(["private meeting", "wage review", "role guarantee"])
        elif stage == "formal_request":
            actions.extend(["negotiate stay", "list at ask", "freeze out carefully"])
        elif stage == "training_exile":
            actions.extend(["fine / discipline", "expedite sale", "repair with captain"])
        else:
            actions.extend(["accept termination risk", "force sale", "protect squad chemistry"])
        return RegenExitLadderView(
            stage=stage,
            label=_EXIT_LABELS.get(stage, stage),
            severity=idx,
            next_stage=next_stage,
            can_petition_termination=can_terminate,
            owner_actions=tuple(actions),
        )

    def _escalate(self, stage: str, personality: PlayerPersonality) -> str:
        idx = _EXIT_STAGES.index(stage) if stage in _EXIT_STAGES else 0
        step = 2 if personality.greed >= 75 and personality.loyalty < 40 else 1
        return _EXIT_STAGES[min(len(_EXIT_STAGES) - 1, idx + step)]

    def _transfer_status_for_stage(self, stage: str) -> str:
        reverse = {value: key for key, value in _STATUS_FROM_TRANSFER.items()}
        return reverse.get(stage, "transfer_request")

    def _promises(self, state: PlayerAgencyState) -> tuple[RegenPromiseMemoryView, ...]:
        memory = dict(state.promise_memory_json or {})
        views: list[RegenPromiseMemoryView] = []
        for key, raw in memory.items():
            if isinstance(raw, dict):
                statement = str(raw.get("statement") or raw.get("text") or key)
                status = str(raw.get("status") or "open")
                broken = bool(raw.get("broken")) or status in {"broken", "failed"}
            else:
                statement = str(raw)
                status = "open"
                broken = False
            views.append(
                RegenPromiseMemoryView(key=str(key), statement=statement, status=status, broken=broken)
            )
        for item in list(state.unmet_expectations_json or [])[:6]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or item.get("code") or "Unmet expectation")
            views.append(
                RegenPromiseMemoryView(
                    key=str(item.get("code") or text[:24]),
                    statement=text,
                    status="broken",
                    broken=True,
                )
            )
        return tuple(views[:8])

    def _grievances(self, state: PlayerAgencyState) -> tuple[str, ...]:
        notes: list[str] = []
        if state.grievance_count:
            notes.append(f"{state.grievance_count} recorded grievance(s)")
        if state.wage_satisfaction < 40:
            notes.append("Wage respect is below their threshold")
        if state.playing_time_satisfaction < 40:
            notes.append("Minutes promise feels broken")
        if state.development_satisfaction < 40:
            notes.append("Development pathway disbelief")
        return tuple(notes[:5])

    def _behavior_brief(
        self,
        player_id: str,
        personality: PlayerPersonality,
        state: PlayerAgencyState,
        mood: RegenMoodStatusView,
    ) -> RegenMatchBehaviorBriefView:
        clutch = getattr(personality, "clutch_factor", 50) / 100.0
        aggression = getattr(personality, "aggression", 50) / 100.0
        unrest = mood.severity / 3.0
        risk = min(1.0, 0.35 + personality.ego / 200.0 + unrest * 0.25)
        pressing = min(1.0, 0.4 + personality.competitiveness / 180.0)
        nerves = min(1.0, max(0.0, (1.0 - clutch) * 0.7 + unrest * 0.3))
        celebration = min(1.0, personality.media_appetite / 100.0 * 0.6 + personality.ego / 200.0)
        captaincy = min(1.0, max(0.0, personality.professionalism / 100.0 * 0.5 + personality.loyalty / 200.0 - unrest * 0.4))
        shot_greed = min(1.0, personality.ego / 120.0 + personality.greed / 300.0)
        discipline = min(1.0, aggression * 0.55 + (100 - personality.professionalism) / 200.0 + unrest * 0.2)
        notes: list[str] = []
        if nerves > 0.65:
            notes.append("Big-game nerves elevated")
        if captaincy < 0.35:
            notes.append("May refuse armband")
        if discipline > 0.7:
            notes.append("Card risk high")
        if mood.code == "explosive":
            notes.append("Explosive mood — intensity unpredictable")
        return RegenMatchBehaviorBriefView(
            player_id=player_id,
            risk_appetite=round(risk, 3),
            pressing_intensity=round(pressing, 3),
            big_game_nerves=round(nerves, 3),
            celebration_hunger=round(celebration, 3),
            captaincy_willingness=round(captaincy, 3),
            shot_greed=round(shot_greed, 3),
            discipline_risk=round(discipline, 3),
            notes=tuple(notes),
        )

    def _heir_spark(self, regen: RegenProfile | None) -> RegenHeirSparkView | None:
        if regen is None:
            return None
        career = dict((regen.metadata_json or {}).get("career_state") or {})
        plan = dict(career.get("legacy_intake_plan") or {})
        if not plan and not career.get("retired"):
            return RegenHeirSparkView(status="inactive")
        if not plan:
            return RegenHeirSparkView(status="retired_pending_plan")
        return RegenHeirSparkView(
            status=str(plan.get("generation_status") or plan.get("status") or "planned"),
            trigger_key=str(plan.get("trigger_key") or "") or None,
            successor_count=int(plan.get("successor_count") or 0),
            prospect_ids=tuple(str(x) for x in (plan.get("prospect_ids") or [])),
            exceptional=bool(plan.get("exceptional_successor_candidate")),
        )

    def _inbox_notes(
        self,
        mood: RegenMoodStatusView,
        exit_ladder: RegenExitLadderView,
        promises: tuple[RegenPromiseMemoryView, ...],
        grievances: tuple[str, ...],
        monologue: RegenInnerMonologueView,
    ) -> tuple[str, ...]:
        notes = [f"Mood: {mood.label}", f"Exit stage: {exit_ladder.label}", f'Voice: "{monologue.voice_line}"']
        broken = [p.statement for p in promises if p.broken]
        if broken:
            notes.append(f"Broken promise: {broken[0]}")
        notes.extend(grievances[:2])
        return tuple(notes[:6])


__all__ = ["RegenLivingStarService"]
