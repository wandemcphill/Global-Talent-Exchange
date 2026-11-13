import type { RigAction } from "./playerRig";

export type PitchSide = "home" | "away";

export type PitchPlayer = {
  playerId: string;
  side: PitchSide;
  x: number;
  y: number;
  shirtNumber: number;
  name: string;
  role?: string;
  animationState?: string;
  hasBall?: boolean;
  isGoalkeeper?: boolean;
};

export type PitchBall = { x: number; y: number };

export type PitchFrame = {
  timeSeconds: number;
  clockMinute?: number;
  players: PitchPlayer[];
  ball: PitchBall | null;
  eventType?: string | null;
};

export type SnapshotCursor = { snapshotVersion: number };

export type PlayerAction = RigAction;

export function seekTime<T extends { timeSeconds: number }>(frames: T[], timeSeconds: number) {
  if (!frames.length) {
    return { left: null, right: null, t: 0 };
  }
  const time = Number.isFinite(timeSeconds) ? timeSeconds : frames[0].timeSeconds;
  let index = 0;
  while (index < frames.length - 1 && frames[index + 1].timeSeconds <= time) index += 1;
  const left = frames[index];
  const right = frames[Math.min(index + 1, frames.length - 1)];
  if (left.timeSeconds === time || right === left || time >= right.timeSeconds) {
    return { left, right: left, t: 1 };
  }
  const span = right.timeSeconds - left.timeSeconds;
  const t = span <= 0.001 ? 1 : Math.min(1, Math.max(0, (time - left.timeSeconds) / span));
  return { left, right, t };
}

export function acceptSnapshot<T extends SnapshotCursor>(previous: T | null, next: T | null): T | null {
  if (!next) return previous;
  if (previous && next.snapshotVersion < previous.snapshotVersion) return previous;
  return next;
}

export function interpolate(from: PitchFrame, to: PitchFrame, alpha: number): PitchFrame {
  const t = Math.min(1, Math.max(0, alpha));
  const nextById = new Map(to.players.map((player) => [player.playerId, player]));
  const players = from.players.map((player) => {
    const target = nextById.get(player.playerId);
    if (!target) return player;
    return {
      ...target,
      x: player.x + (target.x - player.x) * t,
      y: player.y + (target.y - player.y) * t,
    };
  });
  const ball =
    from.ball && to.ball
      ? { x: from.ball.x + (to.ball.x - from.ball.x) * t, y: from.ball.y + (to.ball.y - from.ball.y) * t }
      : to.ball || from.ball;
  return {
    timeSeconds: from.timeSeconds + (to.timeSeconds - from.timeSeconds) * t,
    clockMinute: to.clockMinute,
    players,
    ball,
    eventType: t < 0.5 ? from.eventType : to.eventType,
  };
}

export function animationFor(
  player: { animationState?: string; hasBall?: boolean; role?: string },
  eventType?: string | null,
): PlayerAction {
  const event = String(eventType || "").toLowerCase();
  const state = String(player.animationState || "").toLowerCase();
  const keeper = String(player.role || "").toLowerCase().includes("gk") || String(player.role || "").toLowerCase().includes("goal");
  if (event === "goal" && player.hasBall) return "celebrate";
  if ((event === "save" || event === "shot") && keeper) return event === "save" ? "save" : "dive";
  if (event === "goal" || event === "shot" || event === "miss") return keeper ? "dive" : "shoot";
  if (event === "pass" || event === "attack") return player.hasBall ? "pass" : "jog";
  if (event === "foul" || event === "tackle") return "tackle";
  if (event === "substitution") return "idle";
  if (state.includes("header")) return "header";
  if (state.includes("sprint")) return "sprint";
  if (state.includes("walk")) return "walk";
  if (state.includes("dribble")) return "dribble";
  if (state.includes("jump")) return "jump";
  if (state.includes("turn")) return "turn";
  if (state.includes("accel")) return "accelerate";
  if (state.includes("run") || state.includes("jog")) return "jog";
  if (state.includes("shoot")) return "shoot";
  if (state.includes("pass")) return "pass";
  if (state.includes("press") || state.includes("tackle")) return "tackle";
  if (state.includes("save")) return "save";
  if (state.includes("celebrat")) return "celebrate";
  if (state.includes("dive")) return "dive";
  if (player.hasBall) return "dribble";
  return "idle";
}

export function metricText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export function suppliedCrest(url: unknown): string | null {
  if (typeof url !== "string") return null;
  const trimmed = url.trim();
  return trimmed ? trimmed : null;
}

export function effectFor(eventType?: string | null): string | null {
  const event = String(eventType || "").toLowerCase();
  if (event === "goal") return "goal";
  if (event === "shot" || event === "miss") return "shot";
  if (event === "pass" || event === "attack") return "pass";
  if (event === "save") return "save";
  if (event === "yellow_card" || event === "red_card") return "card";
  if (event === "substitution") return "substitution";
  return null;
}

export function pitchSource(input: { matchId?: string; hasSnapshot: boolean; hasFrames: boolean }): "live" | "demo" | "unavailable" {
  if (input.matchId === "u2a-006-showcase") return "demo";
  if (input.hasSnapshot || input.hasFrames) return "live";
  return "unavailable";
}

export function sceneObjectCount(playerCount: number, effect: boolean): number {
  return 1 + playerCount + 1 + (effect ? 1 : 0);
}
