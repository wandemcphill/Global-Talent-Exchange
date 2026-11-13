import React, { useRef } from "react";

import { OrthographicPitch } from "@/match2d/OrthographicPitch";
import {
  metricText,
  pitchSource,
  seekTime,
  suppliedCrest,
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
  side?: string;
  is_home?: boolean;
  x?: number;
  y?: number;
  position?: { x?: number; y?: number };
  has_ball?: boolean;
  has_possession?: boolean;
  animation_state?: string;
  state?: string;
  stamina_pct?: number | null;
};
type RawFrame = {
  time_seconds?: number;
  timeSeconds?: number;
  players?: RawPlayer[];
  ball?: RawPoint & { owner_player_id?: string; trajectory?: RawPoint[] };
  event_type?: string;
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
  snapshotPlayers?: RawPlayer[] | null;
  snapshotBall?: RawPoint | null;
  socketFrame?: {
    time_seconds?: number;
    players?: RawPlayer[];
    pitch_players?: RawPlayer[];
    ball?: (RawPoint & { owner_player_id?: string | null; trajectory?: RawPoint[] }) | null;
    event_type?: string;
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
};

function unitPoint(rawX: unknown, rawY: unknown): { x: number; y: number } {
  const x = Number(rawX ?? 50);
  const y = Number(rawY ?? 50);
  return { x: x > 1.5 ? x / 100 : x, y: y > 1.5 ? y / 100 : y };
}

function toPitchPlayer(raw: RawPlayer): PitchPlayer {
  const point = unitPoint(raw?.x ?? raw?.position?.x, raw?.y ?? raw?.position?.y);
  const sideName = String(raw?.side || "").toLowerCase();
  const side = raw?.is_home === false || sideName === "away" ? "away" : "home";
  const role = String(raw?.role || "");
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

function blendPlayers(left: PitchPlayer[], right: PitchPlayer[], t: number): PitchPlayer[] {
  const next = new Map(right.map((player) => [player.playerId, player]));
  return left.map((player) => {
    const target = next.get(player.playerId);
    if (!target) return player;
    return { ...target, x: player.x + (target.x - player.x) * t, y: player.y + (target.y - player.y) * t };
  });
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

export function Pitch2DView({
  matchId,
  frames,
  timeSeconds = 0,
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
}: Pitch2DViewProps) {
  const lastGood = useRef<{ players: PitchPlayer[]; ball: { x: number; y: number } | null; eventType: string | null } | null>(null);
  const recorded = Array.isArray(frames) ? frames : [];
  const source = pitchSource({
    matchId,
    hasSnapshot: Boolean(snapshotPlayers?.length),
    hasFrames: recorded.length > 0,
  });
  const socketSeconds = Number(socketFrame?.time_seconds ?? -1);
  const socketRows = Array.isArray(socketFrame?.players)
    ? socketFrame?.players
    : Array.isArray(socketFrame?.pitch_players)
      ? socketFrame?.pitch_players
      : null;

  let players: PitchPlayer[] = [];
  let ball: { x: number; y: number } | null = null;
  let trajectory: { x: number; y: number }[] | null = null;
  let eventType: string | null = null;

  if (socketRows?.length && socketSeconds + 0.01 >= timeSeconds) {
    players = socketRows.map(toPitchPlayer);
    ball = socketFrame?.ball ? unitPoint(socketFrame.ball.position?.x ?? socketFrame.ball.x, socketFrame.ball.position?.y ?? socketFrame.ball.y) : null;
    eventType = socketFrame?.event_type || null;
  } else if (snapshotPlayers?.length) {
    players = snapshotPlayers.map(toPitchPlayer);
    ball = snapshotBall ? unitPoint(snapshotBall.position?.x ?? snapshotBall.x, snapshotBall.position?.y ?? snapshotBall.y) : null;
    eventType = activeEventType || events?.[events.length - 1]?.type || events?.[events.length - 1]?.event_type || null;
  } else if (source !== "unavailable" && recorded.length > 1) {
    const timed = recorded.map((frame) => ({ ...frame, timeSeconds: Number(frame.time_seconds ?? frame.timeSeconds ?? 0) }));
    const pair = seekTime(timed, timeSeconds);
    if (pair.left) {
      const leftPlayers = (pair.left.players || []).map(toPitchPlayer);
      const rightPlayers = (pair.right?.players || pair.left.players || []).map(toPitchPlayer);
      players = blendPlayers(leftPlayers, rightPlayers, pair.t);
      const leftBall = unitPoint(pair.left.ball?.position?.x ?? pair.left.ball?.x, pair.left.ball?.position?.y ?? pair.left.ball?.y);
      const rightBall = unitPoint(
        pair.right?.ball?.position?.x ?? pair.right?.ball?.x ?? leftBall.x,
        pair.right?.ball?.position?.y ?? pair.right?.ball?.y ?? leftBall.y,
      );
      ball = { x: leftBall.x + (rightBall.x - leftBall.x) * pair.t, y: leftBall.y + (rightBall.y - leftBall.y) * pair.t };
      const path = pair.right?.ball?.trajectory || pair.left.ball?.trajectory;
      if (Array.isArray(path) && path.length > 1) {
        trajectory = path.map((point) => unitPoint(point.position?.x ?? point.x, point.position?.y ?? point.y));
      }
      eventType = String(pair.right?.event_type || pair.left.event_type || "") || null;
    }
  }

  if (players.length) lastGood.current = { players, ball, eventType };
  const shown = players.length ? players : lastGood.current?.players || [];
  const shownBall = players.length ? ball : lastGood.current?.ball || null;
  const shownEvent = players.length ? eventType : lastGood.current?.eventType || null;
  const unavailable = source === "unavailable";
  const selected = shown.find((player) => `${player.side}:${player.playerId}` === selectedKey) || null;
  const rawSelected = (snapshotPlayers || []).find((player) => {
    const side = player.is_home === false || String(player.side || "").toLowerCase() === "away" ? "away" : "home";
    const id = String(player.player_id || player.id || "");
    return `${side}:${id}` === selectedKey;
  });
  const record = selected ? recordFor(events || [], selected.playerId) : null;

  return (
    <div data-testid="pitch-2d-view" className="space-y-2">
      <div className="flex items-center justify-between">
        <CrestMark url={homeCrest} name={homeName} />
        {source === "demo" ? <span className="text-[10px] font-black uppercase tracking-widest text-amber-300">DEMO</span> : null}
        <CrestMark url={awayCrest} name={awayName} />
      </div>
      <OrthographicPitch
        players={shown}
        ball={shownBall}
        ballTrajectory={trajectory}
        eventType={shownEvent}
        homeColor={homeColor}
        awayColor={awayColor}
        goalkeeperHome={goalkeeperHome}
        goalkeeperAway={goalkeeperAway}
        selectedKey={selectedKey}
        onSelect={onSelect}
        unavailable={unavailable}
        demo={source === "demo"}
      />
      {selected && record ? (
        <div className="rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-slate-200">
          <div className="font-black text-white">
            {selected.name} · #{selected.shirtNumber} · {selected.role || "—"}
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
