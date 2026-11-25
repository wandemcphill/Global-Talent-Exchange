import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  OrthographicPitch,
  type PitchCameraMode,
  type SampledPitchFrame,
} from "@/match2d/OrthographicPitch";
import { resolveDistinctKitPalette } from "@/match2d/kitContrast";
import { FMCommentaryStrip, resolveCommentaryPhase } from "@/match2d/FMCommentaryStrip";
import { ClassicMatchBar } from "@/pages/match-center/ClassicMatchBar";
import { ballPlaneVelocity, classicLineupStat } from "@/pages/match-center/classicMatchMarkers";
import type { KitPattern } from "@/match2d/playerRig";
import {
  deriveBroadcastBanner,
  extractShotMarkers,
  interpolate,
  LiveRenderBuffer,
  metricText,
  pitchSource,
  playerIdentityKey,
  resolveFeedPresentationStatus,
  classicActionWindows,
  isClassicPitchAction,
  seekTime,
  suppliedCrest,
  type CardDetailSummary,
  type FeedFreshnessStatus,
  type LivePitchSample,
  type OffsideSnapshot,
  type PitchFrame,
  type PitchPlayer,
  type VarReviewSummary,
} from "@/match2d/matchStateAdapter";

type RawPoint = { x?: number; y?: number; position?: { x?: number; y?: number } };
type RawPlayer = {
  player_id?: string;
  id?: string;
  player_name?: string;
  name?: string;
  label?: string;
  shirt_number?: number;
  role?: string;
  line?: string;
  side?: string;
  is_home?: boolean;
  x?: number;
  y?: number;
  position?: { x?: number; y?: number };
  has_ball?: boolean;
  has_possession?: boolean;
  animation_state?: string;
  state?: string;
  speed_mps?: number;
  stamina_pct?: number | null;
  velocity?: { x?: number; y?: number } | null;
  facing?: { x?: number; y?: number } | null;
  anchor_position?: { x?: number; y?: number } | null;
  speed_ratio?: number | null;
  highlighted?: boolean;
  active?: boolean;
  skin_tone?: string | null;
  hair_color?: string | null;
  hair_style?: string | null;
  build_profile?: string | null;
  boot_color?: string | null;
  kit_pattern?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  accent_color?: string | null;
  shorts_color?: string | null;
  socks_color?: string | null;
};
type RawFrame = {
  frame_id?: string;
  time_seconds?: number;
  timeSeconds?: number;
  clock_minute?: number;
  clockMinute?: number;
  phase?: string;
  home_score?: number;
  away_score?: number;
  players?: RawPlayer[];
  pitch_players?: RawPlayer[];
  ball?: RawPoint & { owner_player_id?: string | null; trajectory?: RawPoint[]; state?: string };
  event_type?: string;
  active_event?: { type?: string; event_type?: string } | null;
  offside_snapshot?: OffsideSnapshot | null;
  var_review?: VarReviewSummary | null;
  card_detail?: CardDetailSummary | null;
};
type MatchEventRow = {
  type?: string;
  event_type?: string;
  player_id?: string;
  primary_player_id?: string;
  secondary_player_id?: string;
  minute?: number;
  clock_minute?: number;
  time_seconds?: number;
  text?: string;
  description?: string;
  summary?: string;
  banner_text?: string;
  team?: string;
  side?: string;
  player_name?: string;
  primary_player_name?: string;
};

export type Pitch2DViewProps = {
  matchId?: string;
  frames?: RawFrame[] | null;
  timeSeconds?: number;
  snapshotVersion?: number;
  snapshotPlayers?: RawPlayer[] | null;
  snapshotBall?: RawPoint | null;
  socketFrame?: {
    frame_id?: string;
    sequence?: number;
    time_seconds?: number;
    clock_minute?: number;
    phase?: string;
    players?: RawPlayer[];
    pitch_players?: RawPlayer[];
    ball?: (RawPoint & { owner_player_id?: string | null; trajectory?: RawPoint[] }) | null;
    event_type?: string;
    active_event?: { type?: string; event_type?: string } | null;
    offside_snapshot?: OffsideSnapshot | null;
    var_review?: VarReviewSummary | null;
    card_detail?: CardDetailSummary | null;
  } | null;
  events?: MatchEventRow[] | null;
  activeEventType?: string | null;
  homeScore?: number | null;
  awayScore?: number | null;
  homeColor?: string;
  awayColor?: string;
  homeSecondaryColor?: string;
  homeAccentColor?: string;
  awaySecondaryColor?: string;
  awayAccentColor?: string;
  homeShortsColor?: string;
  awayShortsColor?: string;
  homeSocksColor?: string;
  awaySocksColor?: string;
  homeKitPattern?: KitPattern;
  awayKitPattern?: KitPattern;
  goalkeeperHome?: string;
  goalkeeperAway?: string;
  homeName?: string;
  awayName?: string;
  homeCrest?: string | null;
  awayCrest?: string | null;
  selectedKey?: string | null;
  onSelect?: (key: string) => void;
  demo?: boolean;
  reconnectToken?: number;
  connectionStatus?: string | null;
  matchPhase?: string | null;
  cameraMode?: PitchCameraMode;
  onCameraModeChange?: (mode: PitchCameraMode) => void;
  showVoronoi?: boolean;
  showHeatmap?: boolean;
  showTactics?: boolean;
  showPassingLanes?: boolean;
  showShotMap?: boolean;
  offsideSnapshot?: OffsideSnapshot | null;
  varReview?: VarReviewSummary | null;
  cardDetail?: CardDetailSummary | null;
  isAutoVarReplay?: boolean;
  tacticalBanner?: string | null;
  /** Recorded-replay archive only: jump local playback back to the start of the incident. */
  onWatchReplay?: (startSeconds: number) => void;
  isInstantReplay?: boolean;
  onExitInstantReplay?: () => void;
  /** Recorded-replay smooth 60fps wall-clock interpolation hints. */
  isPaused?: boolean;
  playbackSpeed?: number;
  durationSeconds?: number;
  clockMinute?: number | null;
  playerNameById?: Record<string, string>;
  /** Classic 2D: keep the pitch off except while an attack, stop, or set piece is on. */
  actionOnly?: boolean;
};

function unitPoint(rawX: unknown, rawY: unknown): { x: number; y: number } {
  const x = Number(rawX ?? 50);
  const y = Number(rawY ?? 50);
  const safeX = Number.isFinite(x) ? x : 50;
  const safeY = Number.isFinite(y) ? y : 50;
  return {
    x: Math.max(0, Math.min(1, safeX > 1.5 ? safeX / 100 : safeX)),
    y: Math.max(0, Math.min(1, safeY > 1.5 ? safeY / 100 : safeY)),
  };
}

type Vec = { x?: number; y?: number } | null | undefined;
function vec(raw: Vec): { x: number; y: number } | null {
  if (!raw || !Number.isFinite(Number(raw.x)) || !Number.isFinite(Number(raw.y))) return null;
  return { x: Number(raw.x), y: Number(raw.y) };
}

function resolvePlayerDisplayName(
  raw: RawPlayer,
  playerId: string,
  shirtNumber: number,
  nameById?: Record<string, string>,
): string {
  const candidates = [
    raw?.player_name,
    raw?.name,
    nameById?.[playerId],
    raw?.label,
  ];
  for (const candidate of candidates) {
    const cleaned = String(candidate || "").trim();
    if (!cleaned) continue;
    const lowered = cleaned.toLowerCase();
    if (lowered === "unnamed" || lowered === "unknown") continue;
    if (/^#?\d+$/.test(cleaned) || (shirtNumber > 0 && cleaned === String(shirtNumber))) continue;
    return cleaned;
  }
  const fallback = String(raw?.player_name || raw?.name || raw?.label || "").trim();
  if (fallback && !/^#?\d+$/.test(fallback) && fallback.toLowerCase() !== "unnamed") return fallback;
  return "";
}

function toPitchPlayer(
  raw: RawPlayer,
  ownerPlayerId?: string | null,
  nameById?: Record<string, string>,
): PitchPlayer {
  const point = unitPoint(raw?.x ?? raw?.position?.x, raw?.y ?? raw?.position?.y);
  const sideName = String(raw?.side || "").toLowerCase();
  const side = raw?.is_home === false || sideName === "away" ? "away" : "home";
  const role = String(raw?.role || raw?.line || "");
  const playerId = String(raw?.player_id || raw?.id || `${side}-${raw?.shirt_number || role}`);
  const shirtNumber = Number(raw?.shirt_number || 0);
  const anchor = raw?.anchor_position ? unitPoint(raw.anchor_position.x, raw.anchor_position.y) : null;
  const speedRatio = Number(raw?.speed_ratio);
  return {
    playerId,
    side,
    x: point.x,
    y: point.y,
    shirtNumber,
    name: resolvePlayerDisplayName(raw, playerId, shirtNumber, nameById),
    role,
    line: raw?.line ? String(raw.line) : undefined,
    state: raw?.state ? String(raw.state) : undefined,
    animationState: String(raw?.animation_state || raw?.state || ""),
    hasBall: Boolean(raw?.has_ball || raw?.has_possession || (ownerPlayerId && ownerPlayerId === playerId)),
    isGoalkeeper: /gk|goal/i.test(role),
    highlighted: Boolean(raw?.highlighted),
    active: raw?.active !== false,
    speedRatio: Number.isFinite(speedRatio) ? speedRatio : null,
    staminaPct: raw?.stamina_pct ?? null,
    anchorX: anchor ? anchor.x : null,
    anchorY: anchor ? anchor.y : null,
    velocity: vec(raw?.velocity),
    facing: vec(raw?.facing),
    skinTone: raw?.skin_tone ?? null,
    hairColor: raw?.hair_color ?? null,
    hairStyle: raw?.hair_style ?? null,
    buildProfile: raw?.build_profile ?? null,
    bootColor: raw?.boot_color ?? null,
    kitPattern: raw?.kit_pattern ?? null,
    primaryColor: raw?.primary_color ?? null,
    secondaryColor: raw?.secondary_color ?? null,
    accentColor: raw?.accent_color ?? null,
    shortsColor: raw?.shorts_color ?? null,
    socksColor: raw?.socks_color ?? null,
  };
}

function toPitchBall(
  raw: (RawPoint & { height?: number; state?: string; owner_player_id?: string | null; velocity?: { x?: number; y?: number; z?: number } }) | null | undefined,
) {
  if (!raw) return null;
  const p = unitPoint(raw.position?.x ?? raw.x, raw.position?.y ?? raw.y);
  const h = Number((raw as any).height ?? (raw as any).z ?? (raw.position as any)?.z);
  return {
    x: p.x,
    y: p.y,
    height: Number.isFinite(h) ? h : null,
    state: raw.state ?? null,
    ownerPlayerId: raw.owner_player_id ?? null,
    velocity: ballPlaneVelocity(raw.velocity),
  };
}

function frameMeta(raw: Record<string, unknown> | null | undefined) {
  const r = (raw || {}) as Record<string, any>;
  const side = (v: unknown) => (v === "home" || v === "away" ? (v as "home" | "away") : null);
  const n = (v: unknown) => (Number.isFinite(Number(v)) && v !== null && v !== "" ? Number(v) : null);
  return {
    phase: r.phase ?? null,
    stage: r.stage ?? null,
    cameraPreset: r.camera_preset ?? null,
    possessionSide: side(r.possession_side),
    possessionPhase: r.possession_phase ?? null,
    transitionState: r.transition_state ?? null,
    dangerZone: r.danger_zone ?? null,
    pressureIndex: n(r.pressure_index),
    eventBanner: r.event_banner ?? null,
    overlayText: r.overlay_text ?? r.overlayText ?? null,
    activeEventId: r.active_event_id ?? r.active_event?.event_id ?? null,
    celebrationTeamId: r.celebration_team_id ?? null,
    primaryPlayerId: r.active_event?.primary_player_id ?? r.primary_player_id ?? null,
    secondaryPlayerId: r.active_event?.secondary_player_id ?? r.secondary_player_id ?? null,
    homeAttacksRight: typeof r.home_attacks_right === "boolean" ? r.home_attacks_right : undefined,
    homeScore: n(r.home_score) ?? undefined,
    awayScore: n(r.away_score) ?? undefined,
    offsideSnapshot: r.offside_snapshot ?? r.offsideSnapshot ?? null,
    varReview: r.var_review ?? r.varReview ?? null,
    cardDetail: r.card_detail ?? r.cardDetail ?? null,
  };
}

function toPitchFrame(raw: RawFrame, nameById?: Record<string, string>): PitchFrame {
  const rawPlayers = Array.isArray(raw.players)
    ? raw.players
    : Array.isArray(raw.pitch_players)
      ? raw.pitch_players
      : [];
  const ballRaw = raw.ball as any;
  const ownerId = ballRaw?.owner_player_id ? String(ballRaw.owner_player_id) : null;
  const players = rawPlayers.map((p) => toPitchPlayer(p, ownerId, nameById));
  const ballPoint = toPitchBall(ballRaw);
  const path = raw.ball?.trajectory;
  const ballTrajectory =
    Array.isArray(path) && path.length > 1
      ? path.map((point) => {
          const pt = unitPoint(point.position?.x ?? point.x, point.position?.y ?? point.y);
          const hz = Number((point as any).height ?? (point as any).z ?? (point.position as any)?.z);
          return Number.isFinite(hz) ? { ...pt, height: hz } : pt;
        })
      : null;
  const eventType =
    String(raw.event_type || raw.active_event?.type || raw.active_event?.event_type || "") || null;
  return {
    ...frameMeta(raw as Record<string, unknown>),
    timeSeconds: Number(raw.time_seconds ?? raw.timeSeconds ?? 0),
    clockMinute: raw.clock_minute ?? raw.clockMinute,
    players,
    ball: ballPoint,
    eventType,
    ballTrajectory,
  };
}

function recordFor(events: MatchEventRow[], playerId: string) {
  let goals = 0;
  let yellow = 0;
  let red = 0;
  let substituted = false;
  for (const event of events) {
    const id = String(event.player_id || event.primary_player_id || "");
    if (id !== playerId) continue;
    const type = String(event.type || event.event_type || "").toLowerCase();
    if (type === "goal" || type === "penalty_goal") goals += 1;
    if (type === "yellow_card") yellow += 1;
    if (type === "red_card") red += 1;
    if (type === "substitution") substituted = true;
  }
  return { goals, yellow, red, substituted };
}

function renderOf(f: PitchFrame, alpha: number, fallbackEvent: string | null): SampledPitchFrame {
  return {
    players: f.players.filter(
      (player) => player.active !== false && String(player.state || "").toLowerCase() !== "sent_off",
    ),
    ball: f.ball,
    ballTrajectory: f.ballTrajectory || null,
    trajectoryAlpha: alpha,
    eventType: f.eventType || fallbackEvent || null,
    phase: f.phase ?? null,
    stage: f.stage ?? null,
    cameraPreset: f.cameraPreset ?? null,
    possessionSide: f.possessionSide ?? null,
    dangerZone: f.dangerZone ?? null,
    primaryPlayerId: f.primaryPlayerId ?? null,
    secondaryPlayerId: f.secondaryPlayerId ?? null,
    homeAttacksRight: f.homeAttacksRight,
    clockMinute: f.clockMinute ?? null,
    homeScore: f.homeScore ?? null,
    awayScore: f.awayScore ?? null,
    eventBanner: f.eventBanner ?? null,
    overlayText: f.overlayText ?? null,
    offsideSnapshot: f.offsideSnapshot ?? null,
    varReview: f.varReview ?? null,
    cardDetail: f.cardDetail ?? null,
  };
}

function CrestMark({ url, name }: { url: string | null; name: string }) {
  const crest = suppliedCrest(url);
  if (crest) return <img src={crest} alt="" className="h-7 w-7 object-contain" />;
  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full border border-white/15 text-[10px] font-black">
      {name.slice(0, 2).toUpperCase()}
    </span>
  );
}

function buildLiveSample(
  rows: RawPlayer[],
  sampleBall: RawPoint | null | undefined,
  sampleTime: number,
  options: {
    snapshotVersion?: number;
    frameId?: string;
    sequence?: number;
    source: "snapshot" | "stream";
    eventType: string | null;
    path?: RawPoint[] | null;
    meta?: Record<string, unknown> | null;
    nameById?: Record<string, string>;
  },
): LivePitchSample {
  const ballRaw = sampleBall as any;
  const ownerId = ballRaw?.owner_player_id ? String(ballRaw.owner_player_id) : null;
  const players = rows.map((p) => toPitchPlayer(p, ownerId, options.nameById));
  const ball = toPitchBall(ballRaw);
  const ballTrajectory =
    Array.isArray(options.path) && options.path.length > 1
      ? options.path.map((item) => unitPoint(item.position?.x ?? item.x, item.position?.y ?? item.y))
      : null;
  return {
    ...frameMeta(options.meta),
    timeSeconds: Number.isFinite(sampleTime) ? Math.max(0, sampleTime) : 0,
    snapshotVersion: options.snapshotVersion,
    frameId: options.frameId,
    sequence: options.sequence,
    source: options.source,
    players,
    ball,
    eventType: options.eventType,
    ballTrajectory,
  };
}

function statusBadgeStyle(status: FeedFreshnessStatus): string {
  switch (status) {
    case "LIVE":
      return "border-emerald-400/35 bg-emerald-500/15 text-emerald-300";
    case "DELAYED":
      return "border-amber-400/35 bg-amber-500/15 text-amber-200";
    case "RECONNECTING":
      return "border-orange-400/40 bg-orange-500/15 text-orange-200";
    case "FINAL":
      return "border-sky-400/35 bg-sky-500/15 text-sky-200";
    case "FEED UNAVAILABLE":
    default:
      return "border-rose-400/35 bg-rose-500/15 text-rose-200";
  }
}

export function Pitch2DView({
  matchId,
  frames,
  timeSeconds = 0,
  snapshotVersion = 0,
  snapshotPlayers,
  snapshotBall,
  socketFrame,
  events,
  activeEventType = null,
  homeScore = null,
  awayScore = null,
  homeColor = "#00e87a",
  awayColor = "#ffb800",
  goalkeeperHome = "#f8fafc",
  goalkeeperAway = "#111827",
  homeName = "Home",
  awayName = "Away",
  homeCrest = null,
  awayCrest = null,
  selectedKey,
  onSelect,
  demo = false,
  reconnectToken = 0,
  connectionStatus = "idle",
  homeSecondaryColor,
  homeAccentColor,
  awaySecondaryColor,
  awayAccentColor,
  homeShortsColor,
  awayShortsColor,
  homeSocksColor,
  awaySocksColor,
  homeKitPattern,
  awayKitPattern,
  matchPhase = null,
  cameraMode,
  onCameraModeChange,
  showVoronoi = false,
  showHeatmap = false,
  showTactics = false,
  showPassingLanes = false,
  showShotMap = false,
  offsideSnapshot = null,
  varReview = null,
  cardDetail = null,
  isAutoVarReplay = false,
  tacticalBanner = null,
  onWatchReplay,
  isInstantReplay = false,
  onExitInstantReplay,
  isPaused = false,
  playbackSpeed = 1,
  durationSeconds,
  clockMinute = null,
  playerNameById,
  actionOnly = false,
}: Pitch2DViewProps) {
  const bufferRef = useRef(new LiveRenderBuffer());
  const lastGoodRef = useRef<SampledPitchFrame | null>(null);
  const lastReconnectRef = useRef(reconnectToken);
  const pendingReconnectReplaceRef = useRef(false);
  const lastStreamKeyRef = useRef<string>("");
  const lastSnapshotKeyRef = useRef<string>("");
  const [liveRevision, setLiveRevision] = useState(0);
  const [freshnessTick, setFreshnessTick] = useState(0);

  const recorded = useMemo(() => (Array.isArray(frames) ? frames : []), [frames]);
  const timedRecorded = useMemo(
    () => recorded.map((frame) => toPitchFrame(frame, playerNameById)),
    [recorded, playerNameById],
  );
  const socketRows = useMemo(
    () =>
      Array.isArray(socketFrame?.players)
        ? socketFrame?.players
        : Array.isArray(socketFrame?.pitch_players)
          ? socketFrame?.pitch_players
          : null,
    [socketFrame],
  );
  const hasLiveFrame = Boolean(socketRows?.length || snapshotPlayers?.length);
  const source = pitchSource({
    matchId,
    hasSnapshot: hasLiveFrame,
    hasFrames: timedRecorded.length > 0,
  });
  const isDemo = demo || source === "demo";

  // Flag pending reconnect replacement without wiping the last valid rendered state.
  useEffect(() => {
    if (reconnectToken !== lastReconnectRef.current) {
      lastReconnectRef.current = reconnectToken;
      if (reconnectToken > 0) {
        pendingReconnectReplaceRef.current = true;
      }
    }
  }, [reconnectToken]);

  // Reset buffer when switching matches.
  useEffect(() => {
    bufferRef.current.clear();
    lastGoodRef.current = null;
    lastStreamKeyRef.current = "";
    lastSnapshotKeyRef.current = "";
    pendingReconnectReplaceRef.current = false;
  }, [matchId]);

  // Ingest live WebSocket frames in a dedicated effect (never during render).
  useEffect(() => {
    if (!socketRows?.length || !socketFrame) return;
    const socketSeconds = Number(socketFrame.time_seconds ?? timeSeconds);
    const frameId = socketFrame.frame_id ? String(socketFrame.frame_id) : undefined;
    const sequence = Number.isFinite(Number(socketFrame.sequence))
      ? Number(socketFrame.sequence)
      : undefined;
    const eventType =
      socketFrame.event_type ||
      socketFrame.active_event?.type ||
      socketFrame.active_event?.event_type ||
      activeEventType ||
      null;
    const dedupeKey = `${frameId ?? ""}:${sequence ?? ""}:${socketSeconds.toFixed(3)}:${socketRows.length}:${eventType ?? ""}`;
    if (dedupeKey === lastStreamKeyRef.current && !pendingReconnectReplaceRef.current) {
      return;
    }
    const sample = buildLiveSample(socketRows, socketFrame.ball, socketSeconds, {
      frameId,
      sequence,
      source: "stream",
      eventType,
      path: socketFrame.ball?.trajectory,
      meta: socketFrame as unknown as Record<string, unknown>,
      nameById: playerNameById,
    });
    const nowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
    if (pendingReconnectReplaceRef.current) {
      if (bufferRef.current.replace(sample, nowMs)) {
        pendingReconnectReplaceRef.current = false;
        lastStreamKeyRef.current = dedupeKey;
        setLiveRevision((rev) => rev + 1);
      }
    } else if (bufferRef.current.push(sample, nowMs)) {
      lastStreamKeyRef.current = dedupeKey;
      setLiveRevision((rev) => rev + 1);
    }
  }, [socketFrame, socketRows, timeSeconds, activeEventType]);

  // Ingest HTTP snapshot frames in a dedicated effect using their own snapshotVersion domain.
  useEffect(() => {
    if (!snapshotPlayers?.length) return;
    // If the live stream is actively ahead of this snapshot and we are not recovering from a reconnect,
    // do not let a slower poll overwrite newer stream positions.
    const latestBufferedTime = bufferRef.current.next?.timeSeconds ?? -1;
    if (
      !pendingReconnectReplaceRef.current &&
      bufferRef.current.next?.source === "stream" &&
      timeSeconds + 0.05 < latestBufferedTime
    ) {
      return;
    }
    const fallbackEvent =
      activeEventType ||
      events?.[events.length - 1]?.type ||
      events?.[events.length - 1]?.event_type ||
      null;
    const firstPlayer = snapshotPlayers[0];
    const firstPos = `${firstPlayer?.x ?? firstPlayer?.position?.x ?? ""}:${firstPlayer?.y ?? firstPlayer?.position?.y ?? ""}`;
    const dedupeKey = `${snapshotVersion}:${timeSeconds.toFixed(2)}:${snapshotPlayers.length}:${firstPos}:${fallbackEvent ?? ""}`;
    if (dedupeKey === lastSnapshotKeyRef.current && !pendingReconnectReplaceRef.current) {
      return;
    }
    const sample = buildLiveSample(snapshotPlayers, snapshotBall, timeSeconds, {
      snapshotVersion: snapshotVersion > 0 ? snapshotVersion : undefined,
      source: "snapshot",
      eventType: fallbackEvent,
      path: null,
      nameById: playerNameById,
    });
    const nowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
    if (pendingReconnectReplaceRef.current || !bufferRef.current.next) {
      if (bufferRef.current.replace(sample, nowMs)) {
        pendingReconnectReplaceRef.current = false;
        lastSnapshotKeyRef.current = dedupeKey;
        setLiveRevision((rev) => rev + 1);
      }
    } else if (bufferRef.current.push(sample, nowMs)) {
      lastSnapshotKeyRef.current = dedupeKey;
      setLiveRevision((rev) => rev + 1);
    }
  }, [snapshotPlayers, snapshotBall, snapshotVersion, timeSeconds, activeEventType, events]);

  // Lightweight 1s freshness check in live mode so stale feeds transition honestly to DELAYED.
  useEffect(() => {
    if (source !== "live") return;
    const id = window.setInterval(() => setFreshnessTick((tick) => tick + 1), 1000);
    return () => window.clearInterval(id);
  }, [source]);

  // Pure recorded-frame interpolation for timeline/replay mode.
  const recordedSample = useMemo(() => {
    if (source === "unavailable" || timedRecorded.length === 0) return null;
    if (timedRecorded.length === 1) {
      const only = timedRecorded[0];
      return renderOf(only, 1, activeEventType);
    }
    const pair = seekTime(timedRecorded, timeSeconds);
    if (!pair.left) return null;
    const right = pair.right || pair.left;
    const blended = interpolate(pair.left, right, pair.t);
    return renderOf(blended, pair.t, activeEventType);
  }, [source, timedRecorded, timeSeconds, activeEventType]);

  // Pure synchronous prop fallback for first render before effects commit.
  const immediateLiveFallback = useMemo(() => {
    if (socketRows?.length && socketFrame) {
      const sample = buildLiveSample(
        socketRows,
        socketFrame.ball,
        Number(socketFrame.time_seconds ?? timeSeconds),
        {
          source: "stream",
          eventType:
            socketFrame.event_type ||
            socketFrame.active_event?.type ||
            socketFrame.active_event?.event_type ||
            activeEventType ||
            null,
          path: socketFrame.ball?.trajectory,
      meta: socketFrame as unknown as Record<string, unknown>,
          nameById: playerNameById,
        },
      );
      return renderOf(sample, 1, activeEventType);
    }
    if (snapshotPlayers?.length) {
      const sample = buildLiveSample(snapshotPlayers, snapshotBall, timeSeconds, {
        snapshotVersion: snapshotVersion > 0 ? snapshotVersion : undefined,
        source: "snapshot",
        eventType:
          activeEventType ||
          events?.[events.length - 1]?.type ||
          events?.[events.length - 1]?.event_type ||
          null,
        nameById: playerNameById,
      });
      return renderOf(sample, 1, activeEventType);
    }
    return null;
  }, [socketRows, socketFrame, snapshotPlayers, snapshotBall, snapshotVersion, timeSeconds, activeEventType, events]);

  const currentRenderData = useMemo(() => {
    void liveRevision;
    const buffered = bufferRef.current.next;
    if (buffered?.players?.length) {
      return renderOf(buffered, 1, activeEventType);
    }
    if (immediateLiveFallback?.players?.length) {
      return immediateLiveFallback;
    }
    if (recordedSample?.players?.length) {
      return recordedSample;
    }
    return lastGoodRef.current;
  }, [liveRevision, immediateLiveFallback, recordedSample, activeEventType]);

  useEffect(() => {
    if (currentRenderData?.players?.length) {
      lastGoodRef.current = currentRenderData;
    }
  }, [currentRenderData]);

  // Continuous monotonic 60fps playhead for recorded replays so OS setInterval jitter
  // from parent HUD timers never pauses, rewinds, or snaps players/ball at 1x/2x/4x speed.
  const playheadRef = useRef({
    seconds: timeSeconds,
    lastPropTime: timeSeconds,
    lastNowMs: null as number | null,
    matchKey: matchId || "",
  });

  useEffect(() => {
    const ph = playheadRef.current;
    const matchChanged = ph.matchKey !== (matchId || "");
    const speed =
      Number.isFinite(Number(playbackSpeed)) && Number(playbackSpeed) > 0 ? Number(playbackSpeed) : 1;
    const propJump = Math.abs(timeSeconds - ph.lastPropTime);
    const explicitSeek =
      propJump > Math.max(1.6, speed * 1.4) || timeSeconds < ph.lastPropTime - 0.15;
    ph.lastPropTime = timeSeconds;
    if (matchChanged || isPaused || explicitSeek) {
      ph.seconds = timeSeconds;
      ph.lastNowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
      ph.matchKey = matchId || "";
    }
  }, [matchId, timeSeconds, isPaused, playbackSpeed]);

  const latestRef = useRef({
    recordedSample,
    timedRecorded,
    isPaused,
    playbackSpeed,
    durationSeconds,
    immediateLiveFallback,
    activeEventType,
  });
  latestRef.current = {
    recordedSample,
    timedRecorded,
    isPaused,
    playbackSpeed,
    durationSeconds,
    immediateLiveFallback,
    activeEventType,
  };

  // Monotonic 60fps wall-clock sampler invoked by OrthographicPitch on every animation frame
  // for BOTH live buffered feeds and recorded timeline replays.
  const sampleFrame = useCallback((nowMs: number) => {
    const state = latestRef.current;
    if (bufferRef.current.next) {
      const sampled = bufferRef.current.advanceWallClock(nowMs);
      if (sampled.frame?.players?.length) {
        return renderOf(sampled.frame, sampled.trajectoryAlpha, state.activeEventType);
      }
    }
    if (state.timedRecorded.length > 1) {
      const ph = playheadRef.current;
      const dtSec =
        ph.lastNowMs === null ? 0 : Math.min(0.05, Math.max(0, (nowMs - ph.lastNowMs) / 1000));
      ph.lastNowMs = nowMs;
      const speed =
        Number.isFinite(Number(state.playbackSpeed)) && Number(state.playbackSpeed) > 0
          ? Number(state.playbackSpeed)
          : 1;
      const minTime = state.timedRecorded[0]?.timeSeconds ?? 0;
      const maxTime =
        typeof state.durationSeconds === "number" && Number.isFinite(state.durationSeconds) && state.durationSeconds > 0
          ? state.durationSeconds
          : state.timedRecorded[state.timedRecorded.length - 1]?.timeSeconds ?? Infinity;
      if (!state.isPaused) {
        // Gentle rate nudge keeps playhead aligned with parent clock without ever pausing or snapping backwards
        const drift = ph.lastPropTime - ph.seconds;
        const rateAdjust =
          Math.abs(drift) > 0.35 && Math.abs(drift) < 3.5
            ? 1 + Math.max(-0.12, Math.min(0.12, drift * 0.08))
            : 1;
        ph.seconds = Math.max(minTime, Math.min(maxTime, ph.seconds + dtSec * speed * rateAdjust));
      }
      const pair = seekTime(state.timedRecorded, ph.seconds);
      if (pair.left) {
        const right = pair.right || pair.left;
        const blended = interpolate(pair.left, right, pair.t);
        if (blended.players.length > 0) {
          return renderOf(blended, pair.t, state.activeEventType);
        }
      }
    }
    if (state.recordedSample?.players?.length) {
      return state.recordedSample;
    }
    if (state.immediateLiveFallback?.players?.length) {
      return state.immediateLiveFallback;
    }
    return lastGoodRef.current;
  }, []);

  const shown = currentRenderData?.players || [];
  const shownBall = currentRenderData?.ball || null;
  const trajectory = currentRenderData?.ballTrajectory || null;
  const shownEvent = currentRenderData?.eventType || null;
  const trajectoryAlpha = currentRenderData?.trajectoryAlpha ?? 1;
  const activeOffsideSnapshot = offsideSnapshot ?? currentRenderData?.offsideSnapshot ?? null;
  const activeVarReview = varReview ?? currentRenderData?.varReview ?? null;
  const activeCardDetail = cardDetail ?? currentRenderData?.cardDetail ?? null;
  const unavailable = source === "unavailable" && !shown.length;
  const activeEventRow = useMemo(() => {
    if (!Array.isArray(events) || events.length === 0) return null;
    const targetEv = String(currentRenderData?.eventType || activeEventType || "").toLowerCase();
    for (let i = events.length - 1; i >= 0; i -= 1) {
      const ev = events[i] as Record<string, any>;
      if (!ev) continue;
      const evType = String(ev.type || ev.event_type || "").toLowerCase();
      const evSec = typeof ev.time_seconds === "number" ? ev.time_seconds : null;
      if (evSec !== null) {
        if (timeSeconds >= evSec - 2 && timeSeconds <= evSec + 4) return ev;
        continue;
      }
      if (targetEv && evType === targetEv) {
        return ev;
      }
    }
    return null;
  }, [events, currentRenderData?.eventType, activeEventType, timeSeconds]);

  const banner = useMemo(() => {
    if (!currentRenderData) return null;
    const activeSummary = activeEventRow
      ? activeEventRow.banner_text || activeEventRow.summary || activeEventRow.description || activeEventRow.text || null
      : null;
    return deriveBroadcastBanner(
      {
        timeSeconds,
        clockMinute: currentRenderData.clockMinute ?? undefined,
        homeScore: currentRenderData.homeScore ?? homeScore ?? undefined,
        awayScore: currentRenderData.awayScore ?? awayScore ?? undefined,
        eventBanner: currentRenderData.eventBanner,
        players: currentRenderData.players,
        ball: currentRenderData.ball,
        eventType: currentRenderData.eventType,
        phase: currentRenderData.phase ?? matchPhase,
        primaryPlayerId: currentRenderData.primaryPlayerId,
        possessionSide: currentRenderData.possessionSide,
      },
      { homeName, awayName, activeEventSummary: activeSummary },
    );
  }, [currentRenderData, activeEventRow, timeSeconds, homeScore, awayScore, matchPhase, homeName, awayName]);

  const feedStatus = useMemo(() => {
    void freshnessTick;
    void liveRevision;
    const nowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
    const effectivePhase = socketFrame?.phase || matchPhase || null;
    const hasRecordedOnly = !hasLiveFrame && timedRecorded.length > 0 && !unavailable;
    const isHttpSnapshotOnly = !socketRows?.length && Boolean(snapshotPlayers?.length);
    const effectiveConnectionStatus =
      (isHttpSnapshotOnly || hasRecordedOnly) && (connectionStatus === "reconnecting" || connectionStatus === "error" || connectionStatus === "idle" || connectionStatus === "disconnected")
        ? "connected"
        : hasLiveFrame && connectionStatus === "idle"
          ? "connected"
          : connectionStatus;
    return resolveFeedPresentationStatus({
      unavailable,
      phase: effectivePhase,
      connectionStatus: effectiveConnectionStatus,
      lastFrameReceivedAtMs: bufferRef.current.lastReceivedAtMs,
      nowMs,
      hasRenderableFrame: shown.length > 0,
      isRecordedReplay: hasRecordedOnly,
    });
  }, [freshnessTick, liveRevision, socketFrame?.phase, matchPhase, hasLiveFrame, timedRecorded.length, unavailable, connectionStatus, shown.length, socketRows?.length, snapshotPlayers?.length]);

  const selected = shown.find((player) => playerIdentityKey(player) === selectedKey) || null;
  const rawPool = useMemo(() => {
    if (socketRows?.length) return socketRows;
    if (snapshotPlayers?.length) return snapshotPlayers;
    if (recorded.length > 0) {
      const latestRec = recorded[recorded.length - 1];
      return latestRec.players || latestRec.pitch_players || [];
    }
    return [];
  }, [socketRows, snapshotPlayers, recorded]);

  const rawSelected = useMemo(() => {
    if (!selectedKey) return null;
    return rawPool.find((raw) => playerIdentityKey(toPitchPlayer(raw)) === selectedKey) || null;
  }, [rawPool, selectedKey]);

  const record = selected ? recordFor(events || [], selected.playerId) : null;
  const shotMarkers = useMemo(
    () => extractShotMarkers(events as ReadonlyArray<Record<string, any>> | null, timedRecorded),
    [events, timedRecorded],
  );

  const headerPalette = useMemo(
    () =>
      resolveDistinctKitPalette({
        homeColor,
        awayColor,
        homeShortsColor,
        awayShortsColor,
        homeSocksColor,
        awaySocksColor,
        goalkeeperHome,
        goalkeeperAway,
      }),
    [homeColor, awayColor, homeShortsColor, awayShortsColor, homeSocksColor, awaySocksColor, goalkeeperHome, goalkeeperAway],
  );
  const scoreHome = currentRenderData?.homeScore ?? homeScore;
  const scoreAway = currentRenderData?.awayScore ?? awayScore;
  const hasScorebug = typeof scoreHome === "number" && typeof scoreAway === "number";
  const displayClockMin = currentRenderData?.clockMinute ?? clockMinute;
  const carrierInFrame = shown.find((p) => p.hasBall) || null;
  const activePossessionSide: "home" | "away" | null =
    carrierInFrame?.side || currentRenderData?.possessionSide || null;
  const homeAttacksRightNow = currentRenderData?.homeAttacksRight !== false;
  const homeArrow = homeAttacksRightNow ? "▶" : "◀";
  const awayArrow = homeAttacksRightNow ? "◀" : "▶";

  const shownTime = timeSeconds;
  const actionWindows = useMemo(
    () => (actionOnly && cameraMode === "2d" ? classicActionWindows(frames, durationSeconds || 300) : []),
    [actionOnly, cameraMode, frames, durationSeconds],
  );
  const pitchLive = !actionOnly || cameraMode !== "2d" || isClassicPitchAction(shownTime, actionWindows);
  return (
    <div data-testid="pitch-2d-view" className="space-y-2">
      {cameraMode === "2d" ? (
        <ClassicMatchBar
          timeSeconds={shownTime}
          minute={typeof displayClockMin === "number" ? displayClockMin : null}
          homeName={homeName}
          awayName={awayName}
          homeScore={hasScorebug ? scoreHome : null}
          awayScore={hasScorebug ? scoreAway : null}
          events={events as Array<Record<string, unknown>> | null}
          feedStatus={feedStatus.status}
          feedAgeSeconds={feedStatus.ageMs != null ? feedStatus.ageMs / 1000 : null}
          demo={isDemo}
          activeEvent={shownEvent}
        />
      ) : null}
      {cameraMode === "2d" ? null : (
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-slate-950/75 px-3 py-1.5">
        <div className="flex items-center gap-2">
          <CrestMark url={homeCrest} name={homeName} />
          <span
            aria-hidden="true"
            className="inline-block h-3 w-3 shrink-0 rounded-full border border-white/50 shadow-sm"
            style={{ backgroundColor: headerPalette.homeColor }}
          />
          <span className="text-xs font-black tracking-wide text-slate-100">{homeName}</span>
          {activePossessionSide && (
            <span
              data-testid="home-attack-state"
              className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] font-black uppercase tracking-wider transition-colors ${
                activePossessionSide === "home"
                  ? "border border-emerald-400/60 bg-emerald-500/20 text-emerald-200 shadow-[0_0_8px_rgba(16,185,129,0.28)]"
                  : "border border-white/10 bg-white/[0.04] text-slate-400"
              }`}
              title={`Home attacks ${homeAttacksRightNow ? "right" : "left"}`}
            >
              {activePossessionSide === "home" ? `ATTACKING ${homeArrow}` : "DEFENDING"}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasScorebug ? (
            <span
              data-testid="pitch-scorebug"
              className="inline-flex items-center gap-1.5 rounded border border-white/15 bg-black/60 px-2.5 py-0.5 font-mono text-xs font-black tracking-wider text-white"
            >
              <span>{scoreHome}</span>
              <span className="text-slate-500">-</span>
              <span>{scoreAway}</span>
              {typeof displayClockMin === "number" && Number.isFinite(displayClockMin) ? (
                <span className="ml-1 border-l border-white/15 pl-1.5 text-[10px] text-emerald-300">
                  {Math.max(0, Math.round(displayClockMin))}&apos;
                </span>
              ) : null}
            </span>
          ) : null}
          {isDemo ? (
            <span
              data-testid="pitch-demo-badge"
              className="rounded border border-amber-400/40 bg-amber-500/15 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest text-amber-300"
            >
              DEMO
            </span>
          ) : null}
          <span
            data-testid="pitch-feed-status"
            data-status={feedStatus.status}
            className={`rounded border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider ${statusBadgeStyle(feedStatus.status)}`}
          >
            {feedStatus.status}
            {feedStatus.status === "DELAYED" && feedStatus.ageMs !== null
              ? ` · ${Math.max(1, Math.round(feedStatus.ageMs / 1000))}s`
              : ""}
          </span>
          {shownEvent ? (
            <span
              data-testid="pitch-active-event"
              className="rounded border border-cyan-400/35 bg-cyan-500/15 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-cyan-200"
            >
              {shownEvent.replace(/_/g, " ")}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {activePossessionSide && (
            <span
              data-testid="away-attack-state"
              className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] font-black uppercase tracking-wider transition-colors ${
                activePossessionSide === "away"
                  ? "border border-sky-400/60 bg-sky-500/20 text-sky-200 shadow-[0_0_8px_rgba(56,189,248,0.28)]"
                  : "border border-white/10 bg-white/[0.04] text-slate-400"
              }`}
              title={`Away attacks ${homeAttacksRightNow ? "left" : "right"}`}
            >
              {activePossessionSide === "away" ? `${awayArrow} ATTACKING` : "DEFENDING"}
            </span>
          )}
          <span className="text-xs font-black tracking-wide text-slate-100">{awayName}</span>
          <span
            aria-hidden="true"
            className="inline-block h-3 w-3 shrink-0 rounded-full border border-white/50 shadow-sm"
            style={{ backgroundColor: headerPalette.awayColor }}
          />
          <CrestMark url={awayCrest} name={awayName} />
        </div>
      </div>
      )}
      <div className="relative" data-testid="classic-pitch-stage">
      <div className={pitchLive ? undefined : "pointer-events-none opacity-0"}>
      <OrthographicPitch
        players={shown}
        ball={shownBall}
        ballTrajectory={trajectory}
        trajectoryAlpha={trajectoryAlpha}
        eventType={shownEvent}
        phase={currentRenderData?.phase}
        stage={currentRenderData?.stage}
        cameraPreset={currentRenderData?.cameraPreset}
        possessionSide={currentRenderData?.possessionSide}
        dangerZone={currentRenderData?.dangerZone}
        primaryPlayerId={currentRenderData?.primaryPlayerId}
        secondaryPlayerId={currentRenderData?.secondaryPlayerId}
        homeAttacksRight={currentRenderData?.homeAttacksRight}
        homeColor={homeColor}
        awayColor={awayColor}
        homeSecondaryColor={homeSecondaryColor}
        homeAccentColor={homeAccentColor}
        awaySecondaryColor={awaySecondaryColor}
        awayAccentColor={awayAccentColor}
        homeShortsColor={homeShortsColor}
        awayShortsColor={awayShortsColor}
        homeSocksColor={homeSocksColor}
        awaySocksColor={awaySocksColor}
        homeKitPattern={homeKitPattern}
        awayKitPattern={awayKitPattern}
        goalkeeperHome={goalkeeperHome}
        goalkeeperAway={goalkeeperAway}
        selectedKey={selectedKey}
        onSelect={onSelect}
        unavailable={unavailable}
        demo={isDemo}
        cameraMode={cameraMode}
        onCameraModeChange={onCameraModeChange}
        showVoronoi={showVoronoi}
        showHeatmap={showHeatmap}
        showTactics={showTactics}
        showPassingLanes={showPassingLanes}
        showShotMap={showShotMap}
        shotMarkers={shotMarkers}
        offsideSnapshot={activeOffsideSnapshot}
        varReview={activeVarReview}
        cardDetail={activeCardDetail}
        clockMinute={currentRenderData?.clockMinute ?? null}
        homeScore={currentRenderData?.homeScore ?? homeScore ?? null}
        awayScore={currentRenderData?.awayScore ?? awayScore ?? null}
        sampleFrame={sampleFrame}
        feedFreshness={feedStatus.status}
      />
      </div>
      {pitchLive ? null : (
        <div
          data-testid="classic-waiting-board"
          className="absolute inset-0 z-20 flex flex-col overflow-hidden rounded-md"
        >
          <div
            className="absolute inset-0"
            style={{
              background:
                "repeating-linear-gradient(90deg, #0c6b2c 0px, #0c6b2c 28px, #128237 28px, #128237 56px)",
            }}
          />
          <div className="relative z-10 flex items-center justify-between gap-3 px-3 pb-1 pt-2">
            <p className="font-mono text-[10px] font-black uppercase tracking-[0.22em] text-emerald-200">
              Waiting for the next moment
            </p>
            <p className="truncate text-[11px] font-black uppercase tracking-wide text-white">
              {homeName}
              {hasScorebug ? `  ${scoreHome} - ${scoreAway}  ` : "  vs  "}
              {awayName}
            </p>
          </div>
          <div className="relative z-10 grid min-h-0 flex-1 grid-cols-2 gap-2 px-2 pb-2" data-testid="classic-waiting-lineups">
            {(["home", "away"] as const).map((side) => {
              const sidePlayers = shown
                .filter((player) => player.side === side && player.active !== false)
                .sort((a, b) => {
                  const rank = (line?: string, role?: string) => {
                    const key = `${line || ""} ${role || ""}`.toLowerCase();
                    if (key.includes("goal") || /\bgk\b/.test(key)) return 0;
                    if (key.includes("def")) return 1;
                    if (key.includes("mid")) return 2;
                    return 3;
                  };
                  const byLine = rank(a.line, a.role) - rank(b.line, b.role);
                  if (byLine !== 0) return byLine;
                  return (a.anchorY ?? a.shirtNumber) - (b.anchorY ?? b.shirtNumber);
                });
              const accent = side === "home" ? headerPalette.homeColor : headerPalette.awayColor;
              const title = side === "home" ? homeName : awayName;
              return (
                <section
                  key={side}
                  data-testid={`classic-waiting-xi-${side}`}
                  className="flex min-h-0 flex-col overflow-hidden rounded-md border border-white/10 bg-[#07111f]/95"
                >
                  <header className="flex items-center gap-2 border-b border-white/10 px-2 py-1">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: accent }} />
                    <span className="truncate text-[11px] font-black uppercase tracking-wide text-white">{title}</span>
                  </header>
                  <div className="grid grid-cols-[16px_minmax(88px,1fr)_44px_28px_14px_14px_16px] gap-1.5 px-2 py-1 font-mono text-[9px] font-black uppercase tracking-wider text-slate-500">
                    <span />
                    <span>Player</span>
                    <span>Stm</span>
                    <span>Rt</span>
                    <span>G</span>
                    <span>A</span>
                    <span>C</span>
                  </div>
                  <ul className="flex min-h-0 flex-1 flex-col justify-evenly overflow-y-auto px-2 pb-1">
                    {sidePlayers.map((player) => {
                      const stat = classicLineupStat(
                        events as Array<Record<string, unknown>> | null,
                        player.playerId,
                        shownTime,
                      );
                      const stamina = typeof player.staminaPct === "number" ? Math.max(0, Math.min(100, player.staminaPct)) : null;
                      const staminaColor = stamina == null ? "#64748b" : stamina < 40 ? "#f43f5e" : stamina < 65 ? "#f59e0b" : "#34d399";
                      return (
                        <li
                          key={player.playerId}
                          data-testid={`classic-waiting-player-${player.playerId}`}
                          className="grid grid-cols-[16px_minmax(88px,1fr)_44px_28px_14px_14px_16px] items-center gap-1.5 text-[12px] text-slate-100"
                        >
                          <span className="font-mono text-[11px] text-slate-400">{player.shirtNumber || ""}</span>
                          <span className="truncate font-semibold">{player.name || "Player"}</span>
                          <span className="h-2 overflow-hidden rounded-full bg-white/10" title={stamina == null ? "Stamina not filed" : `${stamina}%`}>
                            <span className="block h-full rounded-full" style={{ width: `${stamina ?? 0}%`, backgroundColor: staminaColor }} />
                          </span>
                          <span className="font-mono font-black text-white">{stat.rating.toFixed(1)}</span>
                          <span className="font-mono">{stat.goals}</span>
                          <span className="font-mono">{stat.assists}</span>
                          <span className="flex items-center gap-0.5">
                            {stat.yellow > 0 ? <span className="inline-block h-2.5 w-1.5 rounded-[1px] bg-yellow-400" title={`${stat.yellow} yellow`} /> : null}
                            {stat.red > 0 ? <span className="inline-block h-2.5 w-1.5 rounded-[1px] bg-rose-500" title={`${stat.red} red`} /> : null}
                            {stat.yellow === 0 && stat.red === 0 ? <span className="text-slate-600">–</span> : null}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              );
            })}
          </div>
        </div>
      )}
      </div>
      {isAutoVarReplay && (
        <div
          data-testid="auto-var-replay-badge"
          className="flex items-center justify-between gap-2 rounded-lg border border-amber-400/60 bg-amber-500/15 px-3 py-1.5 text-xs text-amber-100"
        >
          <div className="flex items-center gap-2">
            <span className="inline-block size-2 animate-ping rounded-full bg-amber-400" />
            <span className="font-mono text-[11px] font-black uppercase tracking-widest text-amber-300">
              AUTOMATIC VAR / BROADCAST REPLAY
            </span>
          </div>
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-amber-200">
            SHARED TIMELINE
          </span>
        </div>
      )}
      {isInstantReplay && onExitInstantReplay && (
        <div
          data-testid="instant-replay-banner"
          className="flex items-center justify-between gap-2 rounded-lg border border-amber-400/60 bg-amber-500/15 px-3 py-1.5 text-xs text-amber-100"
        >
          <span className="font-mono text-[11px] font-black uppercase tracking-widest text-amber-300">
            INSTANT REPLAY · 0.75x SLOW-MO · LOCAL ARCHIVE
          </span>
          <button
            type="button"
            data-testid="exit-instant-replay-btn"
            onClick={onExitInstantReplay}
            className="rounded border border-amber-300/50 bg-black/40 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-amber-200 hover:bg-amber-400 hover:text-slate-950"
          >
            EXIT REPLAY · RESUME
          </button>
        </div>
      )}
      {activeVarReview && (
        <div
          data-testid="pitch-var-monitor"
          className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-400/55 bg-slate-950/90 px-3 py-2 text-xs text-amber-100"
        >
          <div className="flex items-center gap-2">
            <span className="rounded border border-amber-400/50 bg-amber-500/20 px-1.5 py-0.5 font-mono text-[10px] font-black uppercase tracking-widest text-amber-300">
              VAR {(activeVarReview.category || "REVIEW").replace(/_/g, " ")}
            </span>
            <span className="font-bold text-white">
              {activeVarReview.final_decision || activeVarReview.decision_outcome || activeVarReview.reason || "Check in progress"}
            </span>
          </div>
          {activeVarReview.referee_action && (
            <span className="font-mono text-[10px] uppercase tracking-wider text-amber-200">
              {activeVarReview.referee_action}
            </span>
          )}
        </div>
      )}
      {activeOffsideSnapshot && (
        <div
          data-testid="pitch-offside-banner"
          className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-cyan-400/50 bg-slate-950/90 px-3 py-1.5 text-xs text-cyan-100"
        >
          <span className="font-mono text-[10px] font-black uppercase tracking-widest text-cyan-300">
            LAW 11 OFFSIDE · {activeOffsideSnapshot.is_penalised ? "OFFSIDE" : "ONSIDE"}
          </span>
          <span className="font-mono text-[11px] text-slate-200">
            {activeOffsideSnapshot.attacker_name || "Attacker"} ({activeOffsideSnapshot.attacker_body_part || "torso"}) vs{" "}
            {activeOffsideSnapshot.second_last_defender_name || "2nd Last Defender"} (
            {activeOffsideSnapshot.second_last_defender_body_part || "torso"})
            {typeof activeOffsideSnapshot.margin_meters === "number"
              ? ` · ${activeOffsideSnapshot.margin_meters.toFixed(2)}m`
              : ""}
          </span>
        </div>
      )}
      {activeCardDetail && (
        <div
          data-testid="pitch-card-detail-banner"
          className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-1.5 text-xs ${
            String(activeCardDetail.card_type || "").toLowerCase().includes("red") || activeCardDetail.dismissed
              ? "border-rose-400/60 bg-rose-950/60 text-rose-100"
              : "border-yellow-400/60 bg-yellow-950/40 text-yellow-100"
          }`}
        >
          <span className="font-mono text-[10px] font-black uppercase tracking-widest">
            {activeCardDetail.second_yellow
              ? "SECOND YELLOW -> RED"
              : activeCardDetail.card_type || "DISCIPLINE"}{" "}
            · {activeCardDetail.player_name || "Player"}
          </span>
          {activeCardDetail.reason && (
            <span className="font-semibold text-slate-100">{activeCardDetail.reason}</span>
          )}
        </div>
      )}
      {tacticalBanner && (
        <div
          data-testid="touchline-tactical-toast"
          className="flex items-center justify-between gap-2 rounded-lg border border-emerald-400/60 bg-emerald-500/15 px-3 py-1.5 text-xs text-emerald-100"
        >
          <span className="font-mono text-[10px] font-black uppercase tracking-widest text-emerald-300">
            TOUCHLINE ORDER OBSERVED
          </span>
          <span className="truncate font-bold text-white">{tacticalBanner}</span>
        </div>
      )}
      {pitchLive && (banner || shown.length > 0) ? (() => {
        const carrier = shown.find((p) => p.hasBall) || null;
        const posSide: "home" | "away" =
          carrier?.side ||
          (currentRenderData?.possessionSide === "away" ? "away" : "home");
        const posTeamName = posSide === "away" ? awayName : homeName;
        const ballX = shownBall?.x ?? 0.5;
        const ballY = shownBall?.y ?? 0.5;
        const ballHeight = Number(shownBall?.height ?? 0);
        const ballInFlight = shownBall?.state === "in_flight" || ballHeight > 0.45;
        const wideBall = Math.abs(ballY - 0.5) > 0.16;
        const attacksRight = currentRenderData?.homeAttacksRight !== false;
        const attackingProgress =
          (posSide === "home" && attacksRight) || (posSide === "away" && !attacksRight)
            ? ballX
            : 1 - ballX;
        const offThePitch = ballX < 0.06 || ballX > 0.94;
        const inTheGoal = Math.abs(ballY - 0.5) < 0.08;
        const zonePhrase =
          offThePitch && !inTheGoal
            ? carrier?.role === "GK"
              ? "gathers it wide of the post"
              : "drags it wide of the post"
            : offThePitch
              ? "sees it nestle in the net"
            : ballInFlight && ballHeight > 0.8 && wideBall && attackingProgress > 0.8
            ? "whips the cross into the box"
            : ballInFlight && ballHeight > 0.8
              ? "lofts the pass"
            : ballInFlight && wideBall && attackingProgress > 0.62 && attackingProgress < 0.94
              ? "slides the through ball"
            : ballInFlight && !wideBall && attackingProgress > 0.62 && attackingProgress < 0.82
              ? "lets fly from outside the box"
            : ballInFlight && attackingProgress > 0.82
                ? "strikes at goal"
                : wideBall && attackingProgress > 0.72
                  ? "drives down the wing"
                  : attackingProgress > 0.84
                    ? "is in on goal"
                    : attackingProgress > 0.72
                      ? "probes the final third"
                      : attackingProgress < 0.32
                        ? "builds out from the back"
                        : "works possession through midfield";
        const carrierLabel = carrier
          ? carrier.name && !/^#?\d+$/.test(carrier.name)
            ? carrier.name
            : `#${carrier.shirtNumber || ""}`
          : "";
        const filedCall = String(currentRenderData?.overlayText || "").trim();
        const neutralHeadline =
          String(activeEventRow?.banner_text || activeEventRow?.commentary || currentRenderData?.eventBanner || "").trim() ||
          filedCall ||
          (carrierLabel
            ? `${carrierLabel} ${zonePhrase} for ${posTeamName}...`
            : `${posTeamName} ${zonePhrase}...`);
        const effectiveBanner = banner || {
          kind: shownEvent || "neutral",
          tone: "neutral",
          badge: shownEvent && shownEvent !== "open_play" ? shownEvent.replace(/_/g, " ").toUpperCase() : "PLAY-BY-PLAY",
          headline: neutralHeadline,
          subline: null,
          minuteLabel: typeof displayClockMin === "number" && Number.isFinite(displayClockMin) ? `${Math.max(0, Math.round(displayClockMin))}'` : null,
          scoreline: hasScorebug ? `${scoreHome} - ${scoreAway}` : null,
        };
        const inferredEventKind = (() => {
          const baseKind = String(effectiveBanner.kind || "").toLowerCase();
          if (baseKind && baseKind !== "banner" && baseKind !== "neutral" && baseKind !== "open_play") {
            return baseKind;
          }
          const evKind = String(activeEventRow?.event_type || activeEventRow?.type || "").toLowerCase();
          if (evKind) return evKind;
          const hl = String(effectiveBanner.headline || "");
          if (/\bGOAL\b/i.test(hl) && !/\bGOALKEEPER\b/i.test(hl)) return "goal";
          if (/\bSAVE\b|\bDIVING STOP\b/i.test(hl)) return "save";
          if (/\bRED CARD\b/i.test(hl)) return "red_card";
          if (/\bYELLOW CARD\b/i.test(hl)) return "yellow_card";
          if (/\bSUBSTITUTION\b/i.test(hl)) return "substitution";
          if (/\bVAR\b/i.test(hl)) return "var";
          return baseKind || "neutral";
        })();
        const commentaryPhase = resolveCommentaryPhase({
          kind: inferredEventKind,
          tone: effectiveBanner.tone,
          hasVar: Boolean(activeVarReview),
        });
        const displayBadge =
          effectiveBanner.badge === "MATCH EVENT"
            ? commentaryPhase === "goal"
              ? "GOAL"
              : commentaryPhase === "chance"
                ? inferredEventKind === "save"
                  ? "SAVE"
                  : "BIG CHANCE"
                : commentaryPhase === "sub"
                  ? "SUBSTITUTION"
                  : commentaryPhase === "card_red"
                    ? "RED CARD"
                    : commentaryPhase === "card_yellow"
                      ? "YELLOW CARD"
                      : commentaryPhase === "var"
                        ? "VAR"
                        : effectiveBanner.badge
            : effectiveBanner.badge;
        const evSide = String(activeEventRow?.side || activeEventRow?.team || posSide).toLowerCase();
        const activeClubColor = evSide === "away" ? headerPalette.awayColor : headerPalette.homeColor;
        const rawXg = Number(
          activeEventRow?.xg ??
            activeEventRow?.expected_goals ??
            activeEventRow?.shot_xg ??
            (commentaryPhase === "chance" && shownBall
              ? Math.max(
                  0.06,
                  Math.min(
                    0.78,
                    0.56 - Math.min(0.48, Math.hypot(Math.min(shownBall.x, 1 - shownBall.x), Math.abs(shownBall.y - 0.5)) * 1.45),
                  ),
                )
              : NaN),
        );
        const scorerName =
          commentaryPhase === "goal"
            ? String(activeEventRow?.primary_player_name || activeEventRow?.player_name || "").trim() || null
            : null;
        const assistName =
          commentaryPhase === "goal"
            ? String(activeEventRow?.secondary_player_name || activeEventRow?.assist_player_name || "").trim() || null
            : null;
        return (
          <FMCommentaryStrip
            variant={cameraMode === "2d" ? "classic" : "broadcast"}
            phase={commentaryPhase}
            badge={displayBadge}
            headline={effectiveBanner.headline}
            subline={effectiveBanner.subline}
            minuteLabel={effectiveBanner.minuteLabel}
            scoreline={effectiveBanner.scoreline}
            scorerName={scorerName}
            assistName={assistName}
            shotXg={Number.isFinite(rawXg) && rawXg > 0 ? rawXg : null}
            clubColor={activeClubColor}
            kind={inferredEventKind}
            tone={effectiveBanner.tone}
            onWatchReplay={
              (effectiveBanner.kind === "goal" || effectiveBanner.kind === "save") && onWatchReplay && !isInstantReplay
                ? () => onWatchReplay(Math.max(0, timeSeconds - 6))
                : undefined
            }
          />
        );
      })() : null}
      {selected && record ? (
        <div
          data-testid="selected-player-card"
          className="rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-slate-200"
        >
          <div className="font-black text-white">
            {selected.name || `Player #${selected.shirtNumber}`}
            {selected.name ? ` · #${selected.shirtNumber}` : ""} · {selected.role || "—"} ·{" "}
            <span className="uppercase text-slate-400">{selected.side}</span>
          </div>
          <div className="mt-1 flex flex-wrap gap-3 font-mono text-[11px]">
            <span>Stamina {metricText(rawSelected?.stamina_pct)}</span>
            <span>Goals {record.goals}</span>
            <span>Cards {record.yellow}/{record.red}</span>
            <span>{record.substituted ? "Substituted" : "On pitch"}</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}

