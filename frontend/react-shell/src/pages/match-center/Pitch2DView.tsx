import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { OrthographicPitch, type PitchCameraMode } from "@/match2d/OrthographicPitch";
import {
  interpolate,
  LiveRenderBuffer,
  metricText,
  pitchSource,
  playerIdentityKey,
  resolveFeedPresentationStatus,
  seekTime,
  suppliedCrest,
  type FeedFreshnessStatus,
  type LivePitchSample,
  type PitchFrame,
  type PitchPlayer,
} from "@/match2d/matchStateAdapter";

type RawPoint = { x?: number; y?: number; position?: { x?: number; y?: number } };
type RawPlayer = {
  player_id?: string;
  id?: string;
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
};
type MatchEventRow = {
  type?: string;
  event_type?: string;
  player_id?: string;
  primary_player_id?: string;
  minute?: number;
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
  } | null;
  events?: MatchEventRow[] | null;
  activeEventType?: string | null;
  homeColor?: string;
  awayColor?: string;
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
  connectionStatus?: "idle" | "connecting" | "connected" | "reconnecting" | "Closed" | "unavailable";
  matchPhase?: string | null;
  paused?: boolean;
  playbackSpeed?: number;
  cameraMode?: PitchCameraMode;
  onCameraModeChange?: (mode: PitchCameraMode) => void;
  showVoronoi?: boolean;
  showHeatmap?: boolean;
  showTactics?: boolean;
  showPassingLanes?: boolean;
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

function toPitchPlayer(raw: RawPlayer): PitchPlayer {
  const point = unitPoint(raw?.x ?? raw?.position?.x, raw?.y ?? raw?.position?.y);
  const sideName = String(raw?.side || "").toLowerCase();
  const side = raw?.is_home === false || sideName === "away" ? "away" : "home";
  const role = String(raw?.role || raw?.line || "");
  return {
    playerId: String(raw?.player_id || raw?.id || `${side}-${raw?.shirt_number || role}`),
    side,
    x: point.x,
    y: point.y,
    shirtNumber: Number(raw?.shirt_number || 0),
    name: String(raw?.name || raw?.label || ""),
    role,
    animationState: String(raw?.animation_state || raw?.state || ""),
    hasBall: Boolean(raw?.has_ball || raw?.has_possession),
    isGoalkeeper: /gk|goal/i.test(role),
  };
}

function toPitchFrame(raw: RawFrame): PitchFrame {
  const rawPlayers = Array.isArray(raw.players)
    ? raw.players
    : Array.isArray(raw.pitch_players)
      ? raw.pitch_players
      : [];
  const players = rawPlayers.map(toPitchPlayer);
  const ballPoint = raw.ball
    ? unitPoint(raw.ball.position?.x ?? raw.ball.x, raw.ball.position?.y ?? raw.ball.y)
    : null;
  const path = raw.ball?.trajectory;
  const ballTrajectory =
    Array.isArray(path) && path.length > 1
      ? path.map((point) => unitPoint(point.position?.x ?? point.x, point.position?.y ?? point.y))
      : null;
  const eventType =
    String(raw.event_type || raw.active_event?.type || raw.active_event?.event_type || "") || null;
  return {
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
  },
): LivePitchSample {
  const players = rows.map(toPitchPlayer);
  const ball = sampleBall
    ? unitPoint(sampleBall.position?.x ?? sampleBall.x, sampleBall.position?.y ?? sampleBall.y)
    : null;
  const ballTrajectory =
    Array.isArray(options.path) && options.path.length > 1
      ? options.path.map((item) => unitPoint(item.position?.x ?? item.x, item.position?.y ?? item.y))
      : null;
  return {
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
  matchPhase = null,
  paused = false,
  playbackSpeed = 1,
  cameraMode,
  onCameraModeChange,
  showVoronoi = false,
  showHeatmap = false,
  showTactics = false,
  showPassingLanes = false,
}: Pitch2DViewProps) {
  const bufferRef = useRef(new LiveRenderBuffer());
  const lastGoodRef = useRef<{
    players: PitchPlayer[];
    ball: { x: number; y: number } | null;
    ballTrajectory: { x: number; y: number }[] | null;
    eventType: string | null;
    trajectoryAlpha: number;
  } | null>(null);
  const lastReconnectRef = useRef(reconnectToken);
  const pendingReconnectReplaceRef = useRef(false);
  const lastStreamKeyRef = useRef<string>("");
  const lastSnapshotKeyRef = useRef<string>("");
  const [liveRevision, setLiveRevision] = useState(0);
  const [freshnessTick, setFreshnessTick] = useState(0);

  const recorded = useMemo(() => (Array.isArray(frames) ? frames : []), [frames]);
  const timedRecorded = useMemo(() => recorded.map(toPitchFrame), [recorded]);
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
      return {
        players: only.players,
        ball: only.ball,
        ballTrajectory: only.ballTrajectory || null,
        eventType: only.eventType || activeEventType || null,
        trajectoryAlpha: 1,
      };
    }
    const pair = seekTime(timedRecorded, timeSeconds);
    if (!pair.left) return null;
    const right = pair.right || pair.left;
    const blended = interpolate(pair.left, right, pair.t);
    return {
      players: blended.players,
      ball: blended.ball,
      ballTrajectory: blended.ballTrajectory || null,
      eventType: blended.eventType || activeEventType || null,
      trajectoryAlpha: pair.t,
    };
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
        },
      );
      return {
        players: sample.players,
        ball: sample.ball,
        ballTrajectory: sample.ballTrajectory || null,
        eventType: sample.eventType || null,
        trajectoryAlpha: 1,
      };
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
      });
      return {
        players: sample.players,
        ball: sample.ball,
        ballTrajectory: sample.ballTrajectory || null,
        eventType: sample.eventType || null,
        trajectoryAlpha: 1,
      };
    }
    return null;
  }, [socketRows, socketFrame, snapshotPlayers, snapshotBall, snapshotVersion, timeSeconds, activeEventType, events]);

  const currentRenderData = useMemo(() => {
    void liveRevision;
    const buffered = bufferRef.current.next;
    if (buffered?.players?.length) {
      return {
        players: buffered.players,
        ball: buffered.ball,
        ballTrajectory: buffered.ballTrajectory || null,
        eventType: buffered.eventType || activeEventType || null,
        trajectoryAlpha: 1,
      };
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

  const latestRef = useRef({
    paused,
    playbackSpeed,
    recordedSample,
    immediateLiveFallback,
    activeEventType,
  });
  latestRef.current = {
    paused,
    playbackSpeed,
    recordedSample,
    immediateLiveFallback,
    activeEventType,
  };

  // Monotonic wall-clock sampler invoked by OrthographicPitch on every 60fps animation frame.
  const sampleFrame = useCallback((nowMs: number) => {
    const state = latestRef.current;
    if (bufferRef.current.next) {
      const sampled = bufferRef.current.advanceWallClock(nowMs, {
        paused: state.paused,
        speed: state.playbackSpeed,
      });
      if (sampled.frame?.players?.length) {
        return {
          players: sampled.frame.players,
          ball: sampled.frame.ball,
          ballTrajectory: sampled.frame.ballTrajectory || null,
          trajectoryAlpha: sampled.trajectoryAlpha,
          eventType: sampled.frame.eventType || state.activeEventType || null,
        };
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
  const unavailable = source === "unavailable" && !shown.length;

  const feedStatus = useMemo(() => {
    void freshnessTick;
    void liveRevision;
    const nowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
    const effectivePhase = socketFrame?.phase || matchPhase || null;
    const hasRecordedOnly = !hasLiveFrame && timedRecorded.length > 0 && !unavailable;
    if (hasRecordedOnly && !effectivePhase) {
      return { status: "LIVE" as FeedFreshnessStatus, ageMs: null };
    }
    return resolveFeedPresentationStatus({
      unavailable,
      phase: effectivePhase,
      connectionStatus: hasLiveFrame && connectionStatus === "idle" ? "connected" : connectionStatus,
      lastFrameReceivedAtMs: bufferRef.current.lastReceivedAtMs,
      nowMs,
      hasRenderableFrame: shown.length > 0,
    });
  }, [freshnessTick, liveRevision, socketFrame?.phase, matchPhase, hasLiveFrame, timedRecorded.length, unavailable, connectionStatus, shown.length]);

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

  return (
    <div data-testid="pitch-2d-view" className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <CrestMark url={homeCrest} name={homeName} />
          <span className="text-xs font-bold text-slate-200">{homeName}</span>
        </div>
        <div className="flex items-center gap-2">
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
          <span className="text-xs font-bold text-slate-200">{awayName}</span>
          <CrestMark url={awayCrest} name={awayName} />
        </div>
      </div>
      <OrthographicPitch
        players={shown}
        ball={shownBall}
        ballTrajectory={trajectory}
        trajectoryAlpha={trajectoryAlpha}
        eventType={shownEvent}
        homeColor={homeColor}
        awayColor={awayColor}
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
        sampleFrame={sampleFrame}
        feedFreshness={feedStatus.status}
      />
      {selected && record ? (
        <div
          data-testid="selected-player-card"
          className="rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-slate-200"
        >
          <div className="font-black text-white">
            {selected.name} · #{selected.shirtNumber} · {selected.role || "—"} ·{" "}
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

