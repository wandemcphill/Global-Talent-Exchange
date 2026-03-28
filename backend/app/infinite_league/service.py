from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import os
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any, Iterable, Sequence

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.infinite_league.schemas import (
    InfiniteLeagueEconomyView,
    InfiniteLeagueLivestreamSegmentView,
    InfiniteLeagueLivestreamView,
    InfiniteLeagueMatchView,
    InfiniteLeagueStatusView,
    InfiniteLeagueWalletView,
)
from app.live_matches.schemas import (
    LiveMatchRenderPointView,
    LiveMatchStreamEventView,
    MatchHighlightResponseView,
    MatchHighlightSummaryView,
)
from app.match_engine.schemas import (
    MatchCommentaryCueView,
    MatchCrowdStateView,
    MatchExperienceLayerView,
    MatchSpectatorSyncView,
)
from app.pundits.personas import PUNDITS
from app.pundits.schemas import (
    PunditDebateLineView,
    PunditDebateResponse,
    PunditMatchAnalysisView,
    PunditPersonaView,
)
from app.viral.accounts import catalog_accounts
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralContentFormatView,
    ViralDistributionAccountView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralFeedResponse,
    ViralPersonaView,
    ViralScoreBreakdownView,
)
from services.economy import RewardEngine, Token, Wallet, quote_cash_out
from services.influencers import build_publishable_persona_clip, generate_persona_content, select_persona
from services.livestream import (
    FFmpegStreamConfig,
    LivestreamScheduler,
    StreamSegment,
    StreamWindow,
    build_concat_playlist,
    build_ffmpeg_command,
    build_playlist,
    compose_highlight_segment,
    compose_match_segment,
    compose_studio_segment,
)
from services.publisher import PublisherQueue, PublisherSchedulePolicy, PublisherScheduler
from services.universe import (
    Fixture,
    League,
    LeagueEngine,
    MatchEvent,
    MatchResult,
    UniverseGenerator,
    UniverseStore,
    create_league,
    generate_fixtures,
)

logger = logging.getLogger(__name__)
_RUNTIME_LOCK = RLock()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _get_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _display_name(owner_id: str) -> str:
    if owner_id.startswith("persona:") or owner_id.startswith("club:"):
        return owner_id.split(":", 1)[1]
    return owner_id


@dataclass(slots=True)
class RuntimeMatchRecord:
    result: MatchResult
    season: int
    league_name: str
    created_at: datetime
    persona_name: str
    persona_tone: str
    persona_caption: str
    highlights: MatchHighlightResponseView
    viral_clip: ViralClipView
    pundit_debate: PunditDebateResponse
    queued_publish_jobs: tuple[str, ...]
    livestream_segments: tuple[StreamSegment, ...]


@dataclass(slots=True)
class RuntimeLiveMatchStream:
    match_id: str
    home_team_id: str
    away_team_id: str
    home_team_name: str
    away_team_name: str
    base_home_possession: int
    base_away_possession: int
    atmosphere_profile: str
    sync_strategy: str
    checkpoint_interval_seconds: int
    max_latency_ms: int
    events: tuple[LiveMatchStreamEventView, ...]


@dataclass(slots=True)
class InfiniteLeagueRuntime:
    root_path: Path
    session_factory: sessionmaker[Session] | None = None
    enabled: bool = True
    auto_advance: bool = True
    tick_interval_seconds: float = 12.0
    club_count: int = 20
    initial_match_count: int = 3
    seed: int = 20260328
    rtmp_url: str = "rtmp://live.example.com/app/GTEX_DEMO"
    league_name: str = "GTEX Infinite League"
    max_recent_matches: int = 64
    store: UniverseStore | None = None
    publisher_queue: PublisherQueue | None = None
    publisher_scheduler: PublisherScheduler | None = None
    reward_engine: RewardEngine = field(default_factory=RewardEngine)
    token: Token = field(default_factory=Token)
    _season: int = 1
    _league: League | None = None
    _fixtures: list[Fixture] = field(default_factory=list)
    _fixture_cursor: int = 0
    _engine: LeagueEngine | None = None
    _records: dict[str, RuntimeMatchRecord] = field(default_factory=dict)
    _match_order: list[str] = field(default_factory=list)
    _wallets: dict[str, Wallet] = field(default_factory=dict)
    _segments: list[StreamSegment] = field(default_factory=list)
    _stream_window: StreamWindow | None = None
    _worker: Thread | None = None
    _stop_event: Event = field(default_factory=Event)
    _lock: RLock = field(default_factory=RLock)

    def __post_init__(self) -> None:
        self.root_path.mkdir(parents=True, exist_ok=True)
        if self.store is None:
            self.store = UniverseStore(self.root_path / "universe.db")
        if self.publisher_queue is None:
            self.publisher_queue = PublisherQueue(self.root_path / "publisher.db")
        if self.publisher_scheduler is None:
            self.publisher_scheduler = PublisherScheduler(
                queue=self.publisher_queue,
                policy=PublisherSchedulePolicy.from_env(os.environ),
                adapters={},
            )

    @classmethod
    def from_environment(
        cls,
        *,
        settings: Any | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> InfiniteLeagueRuntime:
        project_root = Path(getattr(settings, "project_root", Path.cwd()))
        return cls(
            root_path=project_root / "tmp" / "infinite_league",
            session_factory=session_factory,
            enabled=_get_bool("GTE_INFINITE_LEAGUE_ENABLED", True),
            auto_advance=_get_bool("GTE_INFINITE_LEAGUE_AUTO_ADVANCE", True),
            tick_interval_seconds=max(_get_float("GTE_INFINITE_LEAGUE_INTERVAL_SECONDS", 12.0), 1.0),
            club_count=max(_get_int("GTE_INFINITE_LEAGUE_CLUB_COUNT", 20), 2),
            initial_match_count=max(_get_int("GTE_INFINITE_LEAGUE_INITIAL_MATCH_COUNT", 3), 1),
            seed=_get_int("GTE_INFINITE_LEAGUE_SEED", 20260328),
            rtmp_url=os.environ.get("GTE_INFINITE_LEAGUE_RTMP_URL", "rtmp://live.example.com/app/GTEX_DEMO"),
        )

    def start(self) -> None:
        if not self.enabled or not self.auto_advance:
            self.ensure_seeded()
            return
        self.ensure_seeded()
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return
            self._stop_event.clear()
            self._worker = Thread(target=self._run_loop, name="gtex-infinite-league", daemon=True)
            self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=2)

    def ensure_seeded(self) -> None:
        with self._lock:
            self._ensure_bootstrap_locked()
            seeded = bool(self._match_order)
        if not seeded:
            self.advance(count=self.initial_match_count)

    def advance(self, *, count: int = 1) -> list[RuntimeMatchRecord]:
        generated: list[RuntimeMatchRecord] = []
        for _ in range(max(count, 1)):
            with self._lock:
                self._ensure_bootstrap_locked()
                if self._fixture_cursor >= len(self._fixtures):
                    self._roll_season_locked()
                fixture = self._fixtures[self._fixture_cursor]
                previous_results = self.store.recent_results(league_id=self._league.league_id, limit=240)
                result = self._engine.simulate_fixture(
                    league=self._league,
                    fixture=fixture,
                    previous_results=previous_results,
                )
                self.store.save_match_result(result)
                self._fixture_cursor += 1
                record = self._record_result_locked(result)
                generated.append(record)
            self._publish_story_feed(record)
        return generated

    def has_match(self, match_id: str) -> bool:
        self.ensure_seeded()
        with self._lock:
            return match_id in self._records

    def get_match(self, match_id: str) -> RuntimeMatchRecord | None:
        self.ensure_seeded()
        with self._lock:
            return self._records.get(match_id)

    def get_match_view(self, match_id: str) -> InfiniteLeagueMatchView | None:
        record = self.get_match(match_id)
        if record is None:
            return None
        return self._to_match_view(record)

    def list_matches(self, *, limit: int = 10) -> list[InfiniteLeagueMatchView]:
        self.ensure_seeded()
        with self._lock:
            return [self._to_match_view(self._records[match_id]) for match_id in self._match_order[: max(limit, 1)]]

    def highlight_response(self, match_id: str) -> MatchHighlightResponseView | None:
        record = self.get_match(match_id)
        return None if record is None else record.highlights

    def build_match_viral_feed(
        self,
        match_id: str,
        *,
        favorite_team: str | None = None,
        favorite_event_types: Sequence[str] = (),
    ) -> ViralFeedResponse | None:
        record = self.get_match(match_id)
        if record is None:
            return None
        clip = self._personalize_clip(record.viral_clip, favorite_team=favorite_team, favorite_event_types=favorite_event_types)
        return ViralFeedResponse(
            clips=[clip],
            generated_at=_utcnow(),
            personalization={
                "favorite_team": favorite_team,
                "favorite_event_types": list(favorite_event_types),
            },
        )

    def live_stream(self, match_id: str) -> RuntimeLiveMatchStream | None:
        record = self.get_match(match_id)
        if record is None:
            return None
        result = record.result
        base_home_possession = self._base_home_possession(result)
        atmosphere_profile = self._atmosphere_profile(result)
        return RuntimeLiveMatchStream(
            match_id=result.match_id,
            home_team_id=result.home_club_id,
            away_team_id=result.away_club_id,
            home_team_name=result.home_club_name,
            away_team_name=result.away_club_name,
            base_home_possession=base_home_possession,
            base_away_possession=100 - base_home_possession,
            atmosphere_profile=atmosphere_profile,
            sync_strategy="deterministic_playback",
            checkpoint_interval_seconds=15,
            max_latency_ms=320,
            events=self._build_live_stream_events(result, atmosphere_profile=atmosphere_profile),
        )

    def build_viral_feed(
        self,
        *,
        limit: int = 12,
        match_ids: Sequence[str] = (),
        favorite_team: str | None = None,
        favorite_event_types: Sequence[str] = (),
    ) -> ViralFeedResponse:
        self.ensure_seeded()
        with self._lock:
            records = (
                [self._records[match_id] for match_id in match_ids if match_id in self._records]
                if match_ids
                else [self._records[match_id] for match_id in self._match_order[: max(limit * 2, 6)]]
            )
        clips = [
            self._personalize_clip(record.viral_clip, favorite_team=favorite_team, favorite_event_types=favorite_event_types)
            for record in records
        ]
        clips.sort(key=lambda item: (-item.ranking_score, -item.viral_score, item.minute, item.highlight_id))
        return ViralFeedResponse(
            clips=clips[: max(limit, 1)],
            generated_at=_utcnow(),
            personalization={
                "favorite_team": favorite_team,
                "favorite_event_types": list(favorite_event_types),
            },
        )

    def build_pundit_debate(self, match_id: str, *, format: str = "chat") -> PunditDebateResponse | None:
        record = self.get_match(match_id)
        if record is None:
            return None
        return record.pundit_debate.model_copy(update={"format": format})

    def status_view(self) -> InfiniteLeagueStatusView:
        self.ensure_seeded()
        with self._lock:
            queue_depth = len(self.publisher_queue.list_jobs(status="queued"))
            next_fixture_id = self._fixtures[self._fixture_cursor].fixture_id if self._fixture_cursor < len(self._fixtures) else None
            featured_match_id = self._match_order[0] if self._match_order else None
            window_duration = 0 if self._stream_window is None else self._stream_window.total_duration_seconds
            return InfiniteLeagueStatusView(
                enabled=self.enabled,
                auto_advance=self.auto_advance,
                worker_active=self._worker is not None and self._worker.is_alive(),
                tick_interval_seconds=self.tick_interval_seconds,
                league_name=self.league_name,
                season=self._season,
                club_count=0 if self._league is None else len(self._league.clubs),
                total_fixtures=len(self._fixtures),
                completed_matches=len(self._match_order),
                queue_depth=queue_depth,
                featured_match_id=featured_match_id,
                next_fixture_id=next_fixture_id,
                livestream_window_duration_seconds=window_duration,
            )

    def livestream_view(self) -> InfiniteLeagueLivestreamView:
        self.ensure_seeded()
        with self._lock:
            self._rebuild_stream_window_locked()
            window = self._stream_window
        if window is None:
            return InfiniteLeagueLivestreamView(total_duration_seconds=0, playlist_manifest="", ffmpeg_command=[], segments=[])
        playlist_manifest = build_concat_playlist(window.segments)
        command = build_ffmpeg_command(FFmpegStreamConfig(rtmp_url=self.rtmp_url), playlist_path="playlist.txt")
        return InfiniteLeagueLivestreamView(
            total_duration_seconds=window.total_duration_seconds,
            playlist_manifest=playlist_manifest,
            ffmpeg_command=command,
            segments=[
                InfiniteLeagueLivestreamSegmentView(
                    kind=segment.kind,
                    title=segment.title,
                    path=segment.path,
                    duration_seconds=segment.duration_seconds,
                    metadata=dict(segment.metadata),
                )
                for segment in window.segments
            ],
        )

    def economy_view(self) -> InfiniteLeagueEconomyView:
        self.ensure_seeded()
        with self._lock:
            wallets = sorted(self._wallets.values(), key=lambda item: item.coins, reverse=True)
            payload = []
            for wallet in wallets[:10]:
                cash_out_preview = quote_cash_out(token=self.token, coins=wallet.coins)
                payload.append(
                    InfiniteLeagueWalletView(
                        owner_id=wallet.user_id,
                        display_name=_display_name(wallet.user_id),
                        coins=wallet.coins,
                        usd_balance=f"{wallet.usd_balance:.2f}",
                        cash_out_preview_usd=str(cash_out_preview.net_usd),
                        last_event=None if not wallet.entries else wallet.entries[-1].event,
                    )
                )
        return InfiniteLeagueEconomyView(
            token_name=self.token.name,
            token_symbol=self.token.symbol,
            usd_per_coin=str(self.token.usd_per_coin),
            wallets=payload,
        )

    @staticmethod
    def merge_viral_feeds(responses: Iterable[ViralFeedResponse], *, limit: int) -> ViralFeedResponse:
        clips: list[ViralClipView] = []
        personalization: dict[str, Any] = {}
        for response in responses:
            clips.extend(response.clips)
            personalization.update(response.personalization)
        clips.sort(key=lambda item: (-item.ranking_score, -item.viral_score, item.minute, item.highlight_id))
        return ViralFeedResponse(
            clips=clips[: max(limit, 1)],
            generated_at=_utcnow(),
            personalization=personalization,
        )

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            interrupted = self._stop_event.wait(self.tick_interval_seconds)
            if interrupted:
                break
            try:
                self.advance(count=1)
            except Exception:
                logger.exception("Infinite league tick failed.")

    def _ensure_bootstrap_locked(self) -> None:
        if self._league is not None:
            return
        generator = UniverseGenerator(seed=self.seed + self._season)
        self._league = create_league(name=self.league_name, season=self._season, club_count=self.club_count, generator=generator)
        self._fixtures = generate_fixtures(self._league.clubs)
        self._fixture_cursor = 0
        self._engine = LeagueEngine(seed=self.seed + (self._season * 97))
        self.store.save_league(self._league)
        self.store.save_fixtures(league_id=self._league.league_id, fixtures=self._fixtures)

    def _roll_season_locked(self) -> None:
        self._season += 1
        self._league = None
        self._fixtures = []
        self._fixture_cursor = 0
        self._engine = None
        self._ensure_bootstrap_locked()

    def _record_result_locked(self, result: MatchResult) -> RuntimeMatchRecord:
        persona = select_persona(result.highlight_payload, story_tags=result.storyline.tags)
        persona_payload = generate_persona_content(persona, result.highlight_payload, story_tags=result.storyline.tags)
        persona_clip = build_publishable_persona_clip(result.highlight_payload, persona=persona, story_tags=result.storyline.tags)
        scheduled = self.publisher_scheduler.schedule_clip(result.highlight_payload)
        scheduled.extend(self.publisher_scheduler.schedule_clip(persona_clip))
        queued_publish_jobs = tuple(record.job.job_id for record in scheduled)
        highlights = self._build_highlights(result)
        pundit_debate = self._build_pundit_debate(result)
        viral_clip = self._build_viral_clip(result, persona_payload=persona_payload, queued_publish_jobs=queued_publish_jobs)
        segments = self._build_segments(result, pundit_debate)
        record = RuntimeMatchRecord(
            result=result,
            season=self._season,
            league_name=self.league_name,
            created_at=_utcnow(),
            persona_name=str(persona_payload["persona"]["name"]),
            persona_tone=str(persona_payload["persona"]["tone"]),
            persona_caption=str(persona_payload["caption"]),
            highlights=highlights,
            viral_clip=viral_clip,
            pundit_debate=pundit_debate,
            queued_publish_jobs=queued_publish_jobs,
            livestream_segments=segments,
        )
        self._records[result.match_id] = record
        self._match_order.insert(0, result.match_id)
        while len(self._match_order) > self.max_recent_matches:
            stale_match_id = self._match_order.pop()
            self._records.pop(stale_match_id, None)
        self._segments.extend(segments)
        self._reward_wallet(f"persona:{record.persona_name}", "viral_clip", {"viral_score": result.viral_score})
        if result.winner_club_id is not None:
            winner_name = result.home_club_name if result.winner_club_id == result.home_club_id else result.away_club_name
            self._reward_wallet(f"club:{winner_name}", "match_win", {"upset": result.upset})
        self._rebuild_stream_window_locked()
        return record

    def _build_highlights(self, result: MatchResult) -> MatchHighlightResponseView:
        items = [
            MatchHighlightSummaryView(minute=event.minute, type=event.event_type, description=event.description)
            for event in result.events
            if event.event_type in {"goal", "red_card"}
        ]
        if not items:
            items = [
                MatchHighlightSummaryView(
                    minute=90,
                    type="full_time",
                    description=f"Full time: {result.home_club_name} {result.home_goals}-{result.away_goals} {result.away_club_name}.",
                )
            ]
        return MatchHighlightResponseView(highlights=items)

    def _build_pundit_debate(self, result: MatchResult) -> PunditDebateResponse:
        winner_name = result.home_club_name if result.winner_club_id == result.home_club_id else result.away_club_name if result.winner_club_id else None
        possession_winner = result.home_club_name if result.home_goals >= result.away_goals else result.away_club_name
        turning_point = result.events[-1].description if result.events else result.storyline.hook
        analysis = PunditMatchAnalysisView(
            score=f"{result.home_goals}-{result.away_goals}",
            winner_team_name=winner_name,
            xg_diff=round((result.home_goals - result.away_goals) * 0.35, 2),
            shot_diff=(result.home_goals - result.away_goals) * 2,
            possession_winner=possession_winner,
            upset=result.upset,
            is_final=True,
            key_player=result.man_of_the_match,
            key_player_team=winner_name,
            key_player_rating=round(7.0 + (result.viral_score / 40.0), 1),
            summary_line=result.storyline.hook,
            turning_point=turning_point,
        )
        lines: list[PunditDebateLineView] = []
        for pundit in PUNDITS:
            if pundit["stance"] == "structure":
                line = f"{result.home_club_name} vs {result.away_club_name} became a {', '.join(result.storyline.tags)} game because the spacing broke first."
            elif pundit["stance"] == "mentality":
                line = f"{winner_name or 'Both clubs'} survived the emotional pressure better, and {result.man_of_the_match} carried the belief."
            else:
                line = f"{result.storyline.headline} turned into clip fuel the moment the score hit {result.home_goals}-{result.away_goals}."
            lines.append(
                PunditDebateLineView(
                    speaker=pundit["name"],
                    style=pundit["style"],
                    stance=pundit["stance"],
                    line=line,
                    emphasis="high" if pundit["stance"] == "chaos" else "medium",
                )
            )
        return PunditDebateResponse(
            match_id=result.match_id,
            headline=result.storyline.headline,
            format="chat",
            analysis=analysis,
            personas=[PunditPersonaView(**persona) for persona in PUNDITS],
            hot_takes=[
                f"{winner_name or 'Nobody'} handled the pressure best.",
                f"{result.man_of_the_match} decided the narrative swing.",
                f"The {', '.join(result.storyline.tags)} layer matters as much as the scoreline.",
            ],
            lines=lines,
            generated_at=_utcnow(),
        )

    def _build_viral_clip(
        self,
        result: MatchResult,
        *,
        persona_payload: dict[str, Any],
        queued_publish_jobs: Sequence[str],
    ) -> ViralClipView:
        breakdown = ViralScoreBreakdownView(
            base_event=42,
            late_drama_bonus=10 if result.events and result.events[-1].minute >= 80 else 0,
            rivalry_bonus=10 if result.storyline.rivalry else 0,
            upset_bonus=14 if result.upset else 0,
            chaos_bonus=4 if any(event.event_type == "red_card" for event in result.events) else 0,
            total=result.viral_score,
        )
        caption = ViralCaptionView(
            hook=result.storyline.headline,
            caption=str(persona_payload["caption"]),
            hashtags=["#GTEX", *[f"#{tag.replace('-', '')}" for tag in result.storyline.tags]],
            source="infinite_league_runtime",
        )
        accounts = []
        for account in catalog_accounts()[:2]:
            fit = 70 + (8 if result.storyline.rivalry else 0) + (6 if result.upset else 0)
            accounts.append(
                ViralDistributionAccountView(
                    handle=account.handle,
                    niche=account.niche,
                    target_audience=account.target_audience,
                    fit_score=min(fit, 100),
                    persona=ViralPersonaView(name=str(persona_payload["persona"]["name"]), tone=str(persona_payload["persona"]["tone"])),
                    cross_promo_handles=[],
                    caption_tests=[],
                )
            )
        editor = ViralEditPlanView(
            crop_filter="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            overlay_text=result.storyline.headline,
            transcode_command=["ffmpeg", "-i", result.highlight_payload["video_path"], "-vf", "scale=1080:1920", "out.mp4"],
            overlay_command=["ffmpeg", "-i", result.highlight_payload["video_path"], "-vf", "drawtext=text=GTEX", "out.mp4"],
            share_targets=["tiktok", "instagram", "youtube"],
            commentary_prompt=result.commentary_prompt,
        )
        analytics = ViralClipAnalyticsView(
            clip_id=str(result.highlight_payload["clip_id"]),
            view_count=max(1200, result.viral_score * 140),
            watch_time=float(max(8, int(result.highlight_payload["duration"])) * 0.72),
            loop_rate=min(0.92, 0.32 + (result.viral_score / 160.0)),
            shares=max(10, result.viral_score // 3),
            comments=max(4, result.viral_score // 6),
            completion_rate=min(0.96, 0.45 + (result.viral_score / 180.0)),
            drop_off_point_seconds=float(max(2, int(result.highlight_payload["duration"]) - 3)),
            share_rate=min(0.40, result.viral_score / 260.0),
            comment_rate=min(0.22, result.viral_score / 420.0),
        )
        feedback = ViralFeedbackLoopView(
            performance_tier="elite" if result.viral_score >= 90 else "strong" if result.viral_score >= 75 else "steady",
            recommendation="Keep pushing rivalry and underdog edits through persona-led distribution.",
            increase_similar_clips=result.viral_score >= 80,
            adjust_captions=result.viral_score < 70,
            shorten_clips=int(result.highlight_payload["duration"]) > 22,
            actions=["promote_persona_voice", "keep_vertical_crop", "queue_polished_cut"],
            viral_analysis=result.storyline.hook,
            analysis_source="infinite_league_runtime",
        )
        return ViralClipView(
            clip_id=str(result.highlight_payload["clip_id"]),
            match_id=result.match_id,
            highlight_id=str(result.highlight_payload["clip_id"]),
            title=str(result.highlight_payload["title"]),
            reel_title=result.storyline.headline,
            team_name=str(result.highlight_payload["team_name"]),
            player_name=str(result.highlight_payload["player_name"]),
            event_type=str(result.highlight_payload["event_type"]),
            minute=int(result.highlight_payload["minute"]),
            scoreline_label=f"{result.home_club_name} {result.home_goals}-{result.away_goals} {result.away_club_name}",
            storage_key=str(result.highlight_payload["video_path"]),
            video_url=str(result.highlight_payload["video_path"]),
            render_status="ready",
            viral_score=result.viral_score,
            engagement=round(min(99.0, result.viral_score * 0.9), 2),
            freshness=1.0,
            ranking_score=float(result.viral_score),
            tags=list(result.storyline.tags),
            share_channel="whatsapp",
            breakdown=breakdown,
            caption=caption,
            distribution_accounts=accounts,
            editor=editor,
            formats=[
                ViralContentFormatView(
                    format_key="instant_vertical",
                    title="Instant Vertical",
                    description="Fast 9:16 cut for social distribution.",
                    editor=editor,
                )
            ],
            analytics=analytics,
            feedback=feedback,
            metadata={
                "queued_publish_jobs": list(queued_publish_jobs),
                "commentary_prompt": result.commentary_prompt,
                "pundit_prompt": result.pundit_prompt,
            },
        )

    def _build_segments(self, result: MatchResult, debate: PunditDebateResponse) -> tuple[StreamSegment, ...]:
        match_segment = compose_match_segment(
            {
                **result.as_dict(),
                "duration_seconds": 900,
                "video_path": f"generated/{result.match_id}/full_match.mp4",
            }
        )
        highlight_segment = compose_highlight_segment(result.highlight_payload)
        debate_segment = compose_studio_segment(
            kind="debate",
            title=debate.headline,
            path=f"generated/{result.match_id}/debate.mp4",
            duration_seconds=180,
            metadata={"match_id": result.match_id},
        )
        ad_segment = compose_studio_segment(
            kind="ad",
            title="GTEX Creator Economy",
            path="generated/ads/gtex_creator_economy.mp4",
            duration_seconds=30,
            metadata={"token": self.token.symbol},
        )
        return (match_segment, highlight_segment, debate_segment, ad_segment)

    def _reward_wallet(self, owner_id: str, event: str, metadata: dict[str, object]) -> None:
        wallet = self._wallets.setdefault(owner_id, Wallet(user_id=owner_id))
        self.reward_engine.apply(wallet, event, metadata=metadata)

    def _rebuild_stream_window_locked(self) -> None:
        playlist = build_playlist(
            matches=[segment for segment in self._segments[-24:] if segment.kind == "match"],
            highlights=[segment for segment in self._segments[-24:] if segment.kind == "highlight"],
            debates=[segment for segment in self._segments[-24:] if segment.kind == "debate"],
            ads=[segment for segment in self._segments[-24:] if segment.kind == "ad"],
            sponsor_interval=2,
        )
        if not playlist:
            self._stream_window = None
            return
        self._stream_window = LivestreamScheduler(playlist).build_window(minimum_duration_seconds=1800)

    def _personalize_clip(
        self,
        clip: ViralClipView,
        *,
        favorite_team: str | None,
        favorite_event_types: Sequence[str],
    ) -> ViralClipView:
        ranking = clip.ranking_score
        if favorite_team and clip.team_name and clip.team_name.strip().lower() == favorite_team.strip().lower():
            ranking += 18.0
        event_types = {item.strip().lower() for item in favorite_event_types if item.strip()}
        if event_types and clip.event_type.strip().lower() in event_types:
            ranking += 12.0
        return clip.model_copy(update={"ranking_score": ranking})

    def _to_match_view(self, record: RuntimeMatchRecord) -> InfiniteLeagueMatchView:
        result = record.result
        winner_name = (
            result.home_club_name
            if result.winner_club_id == result.home_club_id
            else result.away_club_name
            if result.winner_club_id == result.away_club_id
            else None
        )
        return InfiniteLeagueMatchView(
            match_id=result.match_id,
            league_id=result.league_id,
            league_name=record.league_name,
            season=record.season,
            round_number=result.round_number,
            home_club_name=result.home_club_name,
            away_club_name=result.away_club_name,
            home_goals=result.home_goals,
            away_goals=result.away_goals,
            winner_club_id=result.winner_club_id,
            winner_club_name=winner_name,
            upset=result.upset,
            headline=result.storyline.headline,
            hook=result.storyline.hook,
            man_of_the_match=result.man_of_the_match,
            viral_score=result.viral_score,
            story_tags=list(result.storyline.tags),
            narrative_flags={
                "rivalry": result.storyline.rivalry,
                "revenge_match": result.storyline.revenge_match,
                "underdog": result.storyline.underdog,
                "pressure_match": result.storyline.pressure_match,
                "title_race": result.storyline.title_race,
            },
            commentary_prompt=result.commentary_prompt,
            pundit_prompt=result.pundit_prompt,
            influencer_persona=record.persona_name,
            influencer_caption=record.persona_caption,
            highlight_count=len(record.highlights.highlights),
            queued_publish_jobs=list(record.queued_publish_jobs),
        )

    def _build_live_stream_events(
        self,
        result: MatchResult,
        *,
        atmosphere_profile: str,
    ) -> tuple[LiveMatchStreamEventView, ...]:
        events: list[LiveMatchStreamEventView] = []
        home_score = 0
        away_score = 0
        timeline = list(result.events)
        for index, event in enumerate(timeline, start=1):
            team_side = self._team_side(result, team_id=event.team_id)
            if event.event_type == "goal":
                if team_side == "home":
                    home_score += 1
                elif team_side == "away":
                    away_score += 1
            raw_event_type = event.event_type
            stream_event_type = "card" if event.event_type == "red_card" else event.event_type
            presentation_second = max(index, event.minute * 60)
            commentary_line = self._commentary_line(result, event=event, home_score=home_score, away_score=away_score)
            metadata = {
                "description": commentary_line,
                "raw_event_type": raw_event_type,
                "team_name": event.team_name,
                "player_name": event.player_name,
                "team_side": team_side,
                "home_score": home_score,
                "away_score": away_score,
                "card_type": "red" if raw_event_type == "red_card" else None,
                "commentary_context": {
                    "scoreline": f"{home_score}-{away_score}",
                    "story_tags": list(result.storyline.tags),
                    "headline": result.storyline.headline,
                    "source": "infinite_league",
                },
                "commentary_tier": "generated",
                "commentary_provider": "infinite_league",
            }
            events.append(
                LiveMatchStreamEventView(
                    match_id=result.match_id,
                    event_id=f"{result.match_id}:{index}:{raw_event_type}",
                    tick=presentation_second,
                    minute=event.minute,
                    event_type=stream_event_type,
                    team_id=event.team_id,
                    team=event.team_name,
                    player=event.player_name,
                    position=self._event_position(team_side=team_side, minute=event.minute, player_name=event.player_name),
                    target_position=self._target_position(team_side=team_side, raw_event_type=raw_event_type),
                    meta={
                        "presentation_second": presentation_second,
                        "source": "infinite_league",
                    },
                    metadata=metadata,
                    experience=self._stream_experience(
                        result,
                        event=event,
                        commentary_line=commentary_line,
                        raw_event_type=raw_event_type,
                        atmosphere_profile=atmosphere_profile,
                        tick=presentation_second,
                        presentation_second=presentation_second,
                        team_side=team_side,
                    ),
                )
            )
        full_time_minute = max(90, timeline[-1].minute if timeline else 90)
        full_time_second = max(full_time_minute * 60, (events[-1].tick if events else 0) + 1)
        final_line = (
            f"Full time: {result.home_club_name} {result.home_goals}-{result.away_goals} "
            f"{result.away_club_name}. {result.storyline.hook}"
        )
        events.append(
            LiveMatchStreamEventView(
                match_id=result.match_id,
                event_id=f"{result.match_id}:full_time",
                tick=full_time_second,
                minute=full_time_minute,
                event_type="full_time",
                meta={
                    "presentation_second": full_time_second,
                    "source": "infinite_league",
                },
                metadata={
                    "description": final_line,
                    "raw_event_type": "full_time",
                    "home_score": result.home_goals,
                    "away_score": result.away_goals,
                    "commentary_context": {
                        "scoreline": f"{result.home_goals}-{result.away_goals}",
                        "story_tags": list(result.storyline.tags),
                        "headline": result.storyline.headline,
                        "source": "infinite_league",
                    },
                    "commentary_tier": "generated",
                    "commentary_provider": "infinite_league",
                },
                experience=MatchExperienceLayerView(
                    commentary=MatchCommentaryCueView(
                        line=final_line,
                        tone="wrap_up",
                        commentator="lead",
                        language="en",
                        intensity=0.62,
                        tts_ready=True,
                        banter_layer=False,
                        audio_channel="match_bed",
                    ),
                    crowd=MatchCrowdStateView(
                        profile=atmosphere_profile,
                        home_intensity=0.72 if result.home_goals >= result.away_goals else 0.54,
                        away_intensity=0.72 if result.away_goals >= result.home_goals else 0.54,
                        dominant_side="home" if result.home_goals >= result.away_goals else "away",
                        chant_level=0.74,
                        hostility=0.36 if result.storyline.rivalry else 0.18,
                        spike=False,
                    ),
                    spectator_sync=MatchSpectatorSyncView(
                        room_id=f"match_{result.match_id}",
                        sync_strategy="deterministic_playback",
                        shared_clock_second=full_time_second,
                        tick=full_time_second,
                        max_latency_ms=320,
                        checkpoint_interval_seconds=15,
                        pause_replay_enabled=False,
                        reactions_enabled=True,
                    ),
                ),
            )
        )
        return tuple(events)

    def _team_side(self, result: MatchResult, *, team_id: str | None) -> str | None:
        if team_id == result.home_club_id:
            return "home"
        if team_id == result.away_club_id:
            return "away"
        return None

    def _base_home_possession(self, result: MatchResult) -> int:
        swing = (result.home_goals - result.away_goals) * 3
        if result.storyline.rivalry:
            swing += 2
        if result.upset:
            swing -= 3
        return max(38, min(62, 50 + swing))

    def _atmosphere_profile(self, result: MatchResult) -> str:
        if result.storyline.rivalry:
            return "derby"
        if result.storyline.title_race or result.storyline.pressure_match:
            return "fever"
        if result.upset or result.storyline.underdog:
            return "volatile"
        return "standard"

    def _commentary_line(
        self,
        result: MatchResult,
        *,
        event: MatchEvent,
        home_score: int,
        away_score: int,
    ) -> str:
        if event.event_type == "goal":
            return (
                f"{event.minute}': {event.player_name} strikes for {event.team_name}. "
                f"Score now {result.home_club_name} {home_score}-{away_score} {result.away_club_name}."
            )
        if event.event_type == "red_card":
            return f"{event.minute}': Red card for {event.player_name} and the match mood flips immediately."
        return event.description

    def _event_position(self, *, team_side: str | None, minute: int, player_name: str) -> LiveMatchRenderPointView:
        lane_offset = sum(ord(char) for char in player_name) % 26
        y = float(min(88, 12 + lane_offset))
        if team_side == "home":
            x = float(min(88, 58 + (minute % 24)))
        elif team_side == "away":
            x = float(max(12, 42 - (minute % 24)))
        else:
            x = 50.0
        return LiveMatchRenderPointView(x=x, y=y)

    def _target_position(self, *, team_side: str | None, raw_event_type: str) -> LiveMatchRenderPointView | None:
        if raw_event_type == "goal":
            return LiveMatchRenderPointView(x=94.0 if team_side == "home" else 6.0, y=50.0)
        if raw_event_type == "red_card":
            return LiveMatchRenderPointView(x=50.0, y=18.0 if team_side == "home" else 82.0)
        return None

    def _stream_experience(
        self,
        result: MatchResult,
        *,
        event: MatchEvent,
        commentary_line: str,
        raw_event_type: str,
        atmosphere_profile: str,
        tick: int,
        presentation_second: int,
        team_side: str | None,
    ) -> MatchExperienceLayerView:
        if raw_event_type == "goal":
            tone = "hype"
            intensity = 0.94
            audio_channel = "headline"
        elif raw_event_type == "red_card":
            tone = "chaos"
            intensity = 0.86
            audio_channel = "headline"
        else:
            tone = "tactical"
            intensity = 0.48
            audio_channel = "match_bed"
        home_intensity = 0.88 if team_side == "home" and raw_event_type == "goal" else 0.58
        away_intensity = 0.88 if team_side == "away" and raw_event_type == "goal" else 0.58
        if raw_event_type == "red_card":
            if team_side == "home":
                away_intensity = min(0.94, away_intensity + 0.18)
            elif team_side == "away":
                home_intensity = min(0.94, home_intensity + 0.18)
        return MatchExperienceLayerView(
            commentary=MatchCommentaryCueView(
                line=commentary_line,
                tone=tone,
                commentator="lead",
                language="en",
                intensity=intensity,
                tts_ready=True,
                banter_layer=raw_event_type in {"goal", "red_card"},
                audio_channel=audio_channel,
            ),
            crowd=MatchCrowdStateView(
                profile=atmosphere_profile,
                home_intensity=home_intensity,
                away_intensity=away_intensity,
                dominant_side="home" if home_intensity >= away_intensity else "away",
                chant_level=max(home_intensity, away_intensity),
                hostility=0.46 if result.storyline.rivalry else 0.24,
                spike=raw_event_type in {"goal", "red_card"},
            ),
            spectator_sync=MatchSpectatorSyncView(
                room_id=f"match_{result.match_id}",
                sync_strategy="deterministic_playback",
                shared_clock_second=presentation_second,
                tick=tick,
                max_latency_ms=320,
                checkpoint_interval_seconds=15,
                pause_replay_enabled=False,
                reactions_enabled=True,
            ),
        )

    def _publish_story_feed(self, record: RuntimeMatchRecord) -> None:
        if self.session_factory is None:
            return
        try:
            from app.story_feed_engine.service import StoryFeedService

            with self.session_factory() as session:
                StoryFeedService(session).publish(
                    story_type="infinite_league",
                    title=record.result.storyline.headline,
                    body=(
                        f"{record.result.storyline.hook} "
                        f"Final score: {record.result.home_club_name} {record.result.home_goals}-{record.result.away_goals} {record.result.away_club_name}. "
                        f"Influencer take: {record.persona_caption}"
                    ),
                    subject_type="match",
                    subject_id=record.result.match_id,
                    metadata_json={
                        "viral_score": record.result.viral_score,
                        "story_tags": list(record.result.storyline.tags),
                    },
                    featured=record.result.viral_score >= 90,
                )
                session.commit()
        except Exception:
            logger.exception("Failed to publish infinite league story feed item.")


def ensure_infinite_league_runtime(app: FastAPI) -> InfiniteLeagueRuntime:
    with _RUNTIME_LOCK:
        runtime = getattr(app.state, "infinite_league_runtime", None)
        if runtime is None:
            runtime = InfiniteLeagueRuntime.from_environment(
                settings=getattr(app.state, "settings", None),
                session_factory=getattr(app.state, "session_factory", None),
            )
            app.state.infinite_league_runtime = runtime
        runtime.ensure_seeded()
        return runtime


def bind_infinite_league_runtime(app: FastAPI, _context) -> None:
    ensure_infinite_league_runtime(app).start()


def shutdown_infinite_league_runtime(app: FastAPI, _context) -> None:
    runtime = getattr(app.state, "infinite_league_runtime", None)
    if runtime is not None:
        runtime.stop()
