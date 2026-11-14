export const CELL = 64;
export const ATLAS_DIRECTIONS = 8;
export const ATLAS_FRAMES = 4;
export const RIG_ACTIONS = [
  "idle",
  "walk",
  "jog",
  "sprint",
  "turn",
  "accelerate",
  "dribble",
  "pass",
  "shoot",
  "tackle",
  "jump",
  "header",
  "save",
  "dive",
  "celebrate",
] as const;

export type RigAction = (typeof RIG_ACTIONS)[number];

export const ATLAS_COLUMNS = ATLAS_DIRECTIONS * ATLAS_FRAMES;
export const ATLAS_ROWS = RIG_ACTIONS.length;

const THIGH = 15;
const SHIN = 14;
const UPPER_ARM = 9;
const FOREARM = 8;

const SKIN = [214, 166, 122, 255] as const;
const HAIR = [48, 36, 30, 255] as const;
const BOOT = [32, 26, 24, 255] as const;
const BOOT_STUD = [210, 220, 230, 220] as const;
const OUTLINE = [18, 28, 22, 255] as const;
const KIT = [255, 255, 255, 255] as const;
const KIT_SHADE = [218, 226, 236, 255] as const;
const SOCK_BAND = [245, 248, 252, 235] as const;

export type Pose = {
  lean: number;
  headLift: number;
  jump: number;
  torsoTilt: number;
  leftArm: [number, number];
  rightArm: [number, number];
  leftLeg: [number, number];
  rightLeg: [number, number];
};

type Cell = { body: Uint8ClampedArray; kit: Uint8ClampedArray };

const cellCache = new Map<string, Cell>();
let cachedAtlas: { body: Uint8Array; kit: Uint8Array; width: number; height: number } | null = null;
let cachedDigits: { data: Uint8Array; width: number; height: number } | null = null;
const cachedPitchPixels = new Map<string, Uint8Array>();
let cachedBallPixels: Uint8Array | null = null;
let cachedRingPixels: Uint8Array | null = null;

const spriteCanvasCache = new Map<string, HTMLCanvasElement>();
const MAX_SPRITE_CACHE = 768;
const pitchCanvasCache = new Map<string, HTMLCanvasElement>();
let cachedBallCanvas: HTMLCanvasElement | null = null;
let cachedRingCanvas: HTMLCanvasElement | null = null;

export function actionIndex(action: string): number {
  const index = RIG_ACTIONS.indexOf(action as RigAction);
  return index >= 0 ? index : 0;
}

export function cellUv(action: string, direction: number, frame: number) {
  const safeDirection = ((Math.round(direction) % ATLAS_DIRECTIONS) + ATLAS_DIRECTIONS) % ATLAS_DIRECTIONS;
  const safeFrame = ((Math.floor(frame) % ATLAS_FRAMES) + ATLAS_FRAMES) % ATLAS_FRAMES;
  const column = safeDirection * ATLAS_FRAMES + safeFrame;
  const row = actionIndex(action);
  return {
    offsetX: column / ATLAS_COLUMNS,
    offsetY: 1 - (row + 1) / ATLAS_ROWS,
    repeatX: 1 / ATLAS_COLUMNS,
    repeatY: 1 / ATLAS_ROWS,
  };
}

function swing(frame: number): number {
  return Math.sin((frame % ATLAS_FRAMES) * (Math.PI / 2));
}

function pulse(frame: number): number {
  return Math.cos((frame % ATLAS_FRAMES) * (Math.PI / 2));
}

export function poseFor(action: RigAction, frame: number): Pose {
  const step = swing(frame);
  const beat = pulse(frame);
  const gait = (amp: number, lean: number, arm: number, knee = 0.22): Pose => ({
    lean,
    headLift: 0,
    jump: Math.abs(step) * (amp > 0.7 ? 1.6 : 0.4),
    torsoTilt: step * 0.04,
    leftArm: [0.35 + step * arm, 0.25 + Math.max(0, step) * 0.12],
    rightArm: [0.35 - step * arm, 0.25 + Math.max(0, -step) * 0.12],
    leftLeg: [-step * amp, Math.abs(step) * knee],
    rightLeg: [step * amp, Math.abs(step) * knee],
  });
  if (action === "idle") return { ...gait(0.08, 0.02, 0.06, 0.05), jump: 0, torsoTilt: 0 };
  if (action === "walk") return gait(0.48, 0.1, 0.42);
  if (action === "jog") return gait(0.78, 0.2, 0.72);
  if (action === "sprint") return gait(1.12, 0.38, 1.05, 0.18);
  if (action === "dribble") return { ...gait(0.56, 0.18, 0.34, 0.22), headLift: -0.6 };
  if (action === "accelerate") return { ...gait(0.96, 0.58, 0.84, 0.16), torsoTilt: 0.15 + step * 0.05 };
  if (action === "turn") return { ...gait(0.36, 0.12, 0.58), torsoTilt: 0.7 * (step || 0.6) };
  if (action === "pass") {
    const swingArc = step * 0.45;
    return {
      lean: 0.12 + swingArc * 0.08,
      headLift: 1,
      jump: Math.max(0, step) * 0.8,
      torsoTilt: 0.2 - swingArc * 0.12,
      leftArm: [1.1 + swingArc * 0.25, 0.2],
      rightArm: [0.4 - swingArc * 0.25, 0.3],
      leftLeg: [0.3 - swingArc * 0.15, 0.2],
      rightLeg: [-1.05 + swingArc * 0.75, 0.15 + Math.max(0, -step) * 0.2],
    };
  }
  if (action === "shoot") {
    const strike = step * 0.5;
    return {
      lean: -0.18 + strike * 0.1,
      headLift: 2,
      jump: 1 + Math.max(0, step) * 1.5,
      torsoTilt: -0.15 - strike * 0.1,
      leftArm: [0.8 + strike * 0.3, 0.4],
      rightArm: [1.3 - strike * 0.3, 0.2],
      leftLeg: [0.45 - strike * 0.2, 0.35],
      rightLeg: [-1.35 + strike * 0.9, 0.08 + Math.max(0, -step) * 0.25],
    };
  }
  if (action === "tackle") {
    const lunge = step * 0.3;
    return {
      lean: 0.55 + lunge * 0.15,
      headLift: 0,
      jump: 0,
      torsoTilt: 0.35 + lunge * 0.1,
      leftArm: [0.9 + lunge * 0.2, 0.2],
      rightArm: [0.4 - lunge * 0.2, 0.2],
      leftLeg: [0.2 - lunge * 0.15, 0.4],
      rightLeg: [-1.25 - Math.abs(lunge) * 0.2, 0.05],
    };
  }
  if (action === "jump") {
    const lift = 10 + Math.abs(step) * 2;
    return {
      lean: 0.05,
      headLift: 2 + Math.max(0, step),
      jump: lift,
      torsoTilt: step * 0.06,
      leftArm: [2.4 + step * 0.15, 0.2],
      rightArm: [2.2 - step * 0.15, 0.2],
      leftLeg: [0.4 + step * 0.1, 0.9],
      rightLeg: [-0.35 - step * 0.1, 0.85],
    };
  }
  if (action === "header") {
    return {
      lean: 0.08 + step * 0.12,
      headLift: 12,
      jump: 8 + Math.abs(step) * 2,
      torsoTilt: -0.25 + step * 0.15,
      leftArm: [2.5 - step * 0.15, 0.15],
      rightArm: [2.35 + step * 0.15, 0.15],
      leftLeg: [0.25 - step * 0.1, 0.7],
      rightLeg: [-0.2 + step * 0.1, 0.65],
    };
  }
  if (action === "save") {
    return {
      lean: 0.1 + step * 0.06,
      headLift: 4,
      jump: 3 + Math.abs(step) * 1.5,
      torsoTilt: 0.45 + step * 0.1,
      leftArm: [2.7 + step * 0.15, 0.05],
      rightArm: [1.2 + Math.abs(step) * 0.4, 0.2],
      leftLeg: [0.15 + step * 0.1, 0.2],
      rightLeg: [-0.2 - step * 0.1, 0.25],
    };
  }
  if (action === "dive") {
    return {
      lean: 0.2 + Math.abs(step) * 0.1,
      headLift: 0,
      jump: 2 + Math.max(0, beat) * 2,
      torsoTilt: 1.45 + Math.abs(step) * 0.12,
      leftArm: [2.2 + step * 0.2, 0.1],
      rightArm: [0.6 + Math.abs(step) * 0.3, 0.15],
      leftLeg: [0.9 + step * 0.15, 0.1],
      rightLeg: [0.35 - step * 0.1, 0.15],
    };
  }
  // celebrate
  return {
    lean: -0.05,
    headLift: 3 + Math.abs(step),
    jump: 2 + Math.abs(step) * 2.5,
    torsoTilt: step * 0.12,
    leftArm: [2.6 + step * 0.2, 0.1],
    rightArm: [2.45 - step * 0.2, 0.1],
    leftLeg: [0.15 + step * 0.35, 0.1 + Math.abs(step) * 0.15],
    rightLeg: [-0.15 - step * 0.35, 0.1 + Math.abs(step) * 0.15],
  };
}

function boneEnd(x: number, y: number, angle: number, length: number) {
  return { x: x + Math.sin(angle) * length, y: y + Math.cos(angle) * length };
}

export function footSpread(pose: Pose): number {
  const leftKnee = boneEnd(0, 0, pose.leftLeg[0], THIGH);
  const rightKnee = boneEnd(0, 0, pose.rightLeg[0], THIGH);
  const leftFoot = boneEnd(leftKnee.x, leftKnee.y, pose.leftLeg[0] + pose.leftLeg[1], SHIN);
  const rightFoot = boneEnd(rightKnee.x, rightKnee.y, pose.rightLeg[0] + pose.rightLeg[1], SHIN);
  return Math.hypot(leftFoot.x - rightFoot.x, leftFoot.y - rightFoot.y);
}

const PRIORITY_ACTIONS = new Set<RigAction>([
  "pass",
  "shoot",
  "tackle",
  "header",
  "jump",
  "save",
  "dive",
  "celebrate",
]);

export function presentationAction(
  base: string,
  motion: { facingDelta: number; speed: number; previousSpeed: number; hasBall: boolean },
): RigAction {
  const known = (RIG_ACTIONS as readonly string[]).includes(base);
  const action = known ? (base as RigAction) : "idle";
  if (PRIORITY_ACTIONS.has(action)) {
    return action;
  }
  if (Math.abs(motion.facingDelta) > 0.9 && motion.speed > 0.002) return "turn";
  if (motion.speed - motion.previousSpeed > 0.008 && motion.speed > 0.006) return "accelerate";
  if (motion.hasBall && motion.speed > 0.0035) return "dribble";
  if (motion.speed > 0.02) return "sprint";
  if (motion.speed > 0.01) return "jog";
  if (motion.speed > 0.0035) return "walk";
  return action === "sprint" || action === "jog" || action === "walk" || action === "dribble" ? action : "idle";
}

export type TrackedPlayerMotion = {
  sampleX: number;
  sampleY: number;
  sampleTimeMs: number;
  lastUpdateMs: number;
  vx: number;
  vy: number;
  speed: number;
  previousSpeed: number;
  acceleration: number;
  facing: number;
  facingDelta: number;
  direction: number;
  action: RigAction;
  actionChangedAtMs: number;
  gaitPhase: number;
  frame: number;
};

function normalizeAngle(angle: number): number {
  let wrapped = angle;
  while (wrapped > Math.PI) wrapped -= Math.PI * 2;
  while (wrapped < -Math.PI) wrapped += Math.PI * 2;
  return wrapped;
}

/**
 * Tracks per-player velocity, facing direction, and animation state across network updates.
 * Velocity is derived from elapsed time between meaningful position changes so higher-frequency
 * WebGL render frames never collapse speed to zero between network samples.
 */
export class PlayerMotionTracker {
  private states = new Map<string, TrackedPlayerMotion>();
  private readonly holdWindowMs: number;
  private readonly actionHysteresisMs: number;

  constructor(options?: { holdWindowMs?: number; actionHysteresisMs?: number }) {
    this.holdWindowMs = options?.holdWindowMs ?? 380;
    this.actionHysteresisMs = options?.actionHysteresisMs ?? 120;
  }

  update(
    compositeKey: string,
    x: number,
    y: number,
    nowMs: number,
    context: {
      baseAction: string;
      hasBall: boolean;
      side?: "home" | "away";
      velocityHint?: { x: number; y: number } | null;
      facingHint?: { x: number; y: number } | null;
    },
  ): TrackedPlayerMotion {
    const existing = this.states.get(compositeKey);
    if (!existing) {
      const defaultFacing =
        context.facingHint && Math.hypot(context.facingHint.x, context.facingHint.y) > 0.01
          ? Math.atan2(-context.facingHint.y, context.facingHint.x)
          : context.side === "away"
            ? Math.PI
            : 0;
      const hintSpeed =
        context.velocityHint && Math.hypot(context.velocityHint.x, context.velocityHint.y) > 0.001
          ? Math.min(0.08, Math.hypot(context.velocityHint.x, context.velocityHint.y) * 0.015)
          : 0;
      const initialAction = presentationAction(context.baseAction, {
        facingDelta: 0,
        speed: hintSpeed,
        previousSpeed: hintSpeed,
        hasBall: context.hasBall,
      });
      const direction = ((Math.round((defaultFacing / (Math.PI * 2)) * ATLAS_DIRECTIONS) % ATLAS_DIRECTIONS) + ATLAS_DIRECTIONS) % ATLAS_DIRECTIONS;
      const created: TrackedPlayerMotion = {
        sampleX: x,
        sampleY: y,
        sampleTimeMs: nowMs,
        lastUpdateMs: nowMs,
        vx: context.velocityHint?.x ?? 0,
        vy: context.velocityHint?.y ?? 0,
        speed: hintSpeed,
        previousSpeed: hintSpeed,
        acceleration: 0,
        facing: defaultFacing,
        facingDelta: 0,
        direction,
        action: initialAction,
        actionChangedAtMs: nowMs,
        gaitPhase: 0,
        frame: Math.floor(nowMs / 120) % ATLAS_FRAMES,
      };
      this.states.set(compositeKey, created);
      return created;
    }

    const dtFrameSec = Math.max(0, Math.min(0.25, (nowMs - existing.lastUpdateMs) / 1000));
    existing.lastUpdateMs = nowMs;

    const dx = x - existing.sampleX;
    const dy = existing.sampleY - y;
    const distance = Math.hypot(dx, dy);
    const dtSampleSec = Math.max(0.016, (nowMs - existing.sampleTimeMs) / 1000);

    if (distance > 0.00035) {
      const rawVx = dx / dtSampleSec;
      const rawVy = (y - existing.sampleY) / dtSampleSec;
      existing.vx = existing.vx * 0.3 + rawVx * 0.7;
      existing.vy = existing.vy * 0.3 + rawVy * 0.7;

      const measuredSpeed = Math.min(0.08, (distance / dtSampleSec) * 0.1);
      existing.previousSpeed = existing.speed;
      existing.speed = existing.speed > 0.001 ? existing.speed * 0.35 + measuredSpeed * 0.65 : measuredSpeed;
      existing.acceleration = (existing.speed - existing.previousSpeed) / dtSampleSec;

      if (distance > 0.0007) {
        const targetFacing = Math.atan2(dy, dx);
        const delta = normalizeAngle(targetFacing - existing.facing);
        const turnRate = Math.min(1, dtSampleSec * 12);
        existing.facing = normalizeAngle(existing.facing + delta * turnRate);
        existing.facingDelta = delta;
      } else {
        existing.facingDelta *= 0.75;
      }

      existing.sampleX = x;
      existing.sampleY = y;
      existing.sampleTimeMs = nowMs;
    } else {
      const timeSinceSampleMs = Math.max(0, nowMs - existing.sampleTimeMs);
      if (timeSinceSampleMs <= this.holdWindowMs) {
        // Between network updates: preserve velocity, speed, and facing direction.
        existing.facingDelta *= Math.pow(0.85, Math.max(1, dtFrameSec * 60));
      } else {
        // Genuinely stationary beyond the network sample interval: decelerate smoothly.
        existing.previousSpeed = existing.speed;
        const decay = Math.exp(-Math.max(0.016, dtFrameSec) * 7);
        existing.speed *= decay;
        existing.vx *= decay;
        existing.vy *= decay;
        existing.facingDelta *= 0.5;
        if (existing.speed < 0.0015) {
          existing.speed = 0;
          existing.vx = 0;
          existing.vy = 0;
          existing.acceleration = 0;
          existing.facingDelta = 0;
        }
      }
    }

    const candidateAction = presentationAction(context.baseAction, {
      facingDelta: existing.facingDelta,
      speed: existing.speed,
      previousSpeed: existing.previousSpeed,
      hasBall: context.hasBall,
    });

    const isPriority = PRIORITY_ACTIONS.has(candidateAction);
    const wasPriority = PRIORITY_ACTIONS.has(existing.action);
    const elapsedInAction = nowMs - existing.actionChangedAtMs;
    const startingMove = existing.action === "idle" && existing.speed > 0.0038;
    const stoppingMove = candidateAction === "idle" && existing.speed === 0 && nowMs - existing.sampleTimeMs > this.holdWindowMs;

    if (
      candidateAction !== existing.action &&
      (isPriority || wasPriority || startingMove || stoppingMove || elapsedInAction >= this.actionHysteresisMs)
    ) {
      existing.action = candidateAction;
      existing.actionChangedAtMs = nowMs;
    }

    existing.direction =
      ((Math.round((existing.facing / (Math.PI * 2)) * ATLAS_DIRECTIONS) % ATLAS_DIRECTIONS) + ATLAS_DIRECTIONS) %
      ATLAS_DIRECTIONS;

    const cycleHz =
      existing.action === "sprint" || existing.action === "accelerate"
        ? 9.5
        : existing.action === "jog" || existing.action === "dribble"
          ? 7.2
          : existing.action === "walk" || existing.action === "turn"
            ? 5.2
            : 3.5;
    existing.gaitPhase = (existing.gaitPhase + Math.max(0.008, dtFrameSec) * cycleHz) % ATLAS_FRAMES;
    existing.frame = Math.floor(existing.gaitPhase) % ATLAS_FRAMES;

    return existing;
  }

  get(compositeKey: string): TrackedPlayerMotion | undefined {
    return this.states.get(compositeKey);
  }

  prune(activeKeys: Set<string>): void {
    this.states.forEach((_, key) => {
      if (!activeKeys.has(key)) {
        this.states.delete(key);
      }
    });
  }

  clear(): void {
    this.states.clear();
  }
}

function plot(data: Uint8ClampedArray, x: number, y: number, color: readonly [number, number, number, number]) {
  const ix = x | 0;
  const iy = y | 0;
  if (ix < 0 || iy < 0 || ix >= CELL || iy >= CELL || color[3] <= 0) return;
  const index = (iy * CELL + ix) * 4;
  const src = color[3] / 255;
  const dst = data[index + 3] / 255;
  const out = src + dst * (1 - src);
  if (out <= 0) return;
  data[index] = (color[0] * src + data[index] * dst * (1 - src)) / out;
  data[index + 1] = (color[1] * src + data[index + 1] * dst * (1 - src)) / out;
  data[index + 2] = (color[2] * src + data[index + 2] * dst * (1 - src)) / out;
  data[index + 3] = Math.min(255, out * 255);
}

function fillDisk(
  data: Uint8ClampedArray,
  cx: number,
  cy: number,
  rx: number,
  ry: number,
  color: readonly [number, number, number, number],
) {
  const left = Math.floor(cx - rx - 1);
  const right = Math.ceil(cx + rx + 1);
  const top = Math.floor(cy - ry - 1);
  const bottom = Math.ceil(cy + ry + 1);
  for (let y = top; y <= bottom; y += 1) {
    for (let x = left; x <= right; x += 1) {
      const nx = (x - cx) / rx;
      const ny = (y - cy) / ry;
      if (nx * nx + ny * ny <= 1) plot(data, x, y, color);
    }
  }
}

function capsule(
  data: Uint8ClampedArray,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  radius: number,
  color: readonly [number, number, number, number],
) {
  const length = Math.hypot(x1 - x0, y1 - y0);
  const steps = Math.max(1, Math.ceil(length));
  for (let step = 0; step <= steps; step += 1) {
    const t = step / steps;
    fillDisk(data, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, radius, radius, color);
  }
}

function fillTaper(
  data: Uint8ClampedArray,
  cx: number,
  top: number,
  bottom: number,
  topHalf: number,
  bottomHalf: number,
  color: readonly [number, number, number, number],
) {
  const start = Math.floor(Math.min(top, bottom));
  const end = Math.ceil(Math.max(top, bottom));
  const span = bottom - top || 1;
  for (let y = start; y <= end; y += 1) {
    const t = (y - top) / span;
    const half = topHalf + (bottomHalf - topHalf) * t;
    for (let x = Math.floor(cx - half); x <= Math.ceil(cx + half); x += 1) plot(data, x, y, color);
  }
}

export function rasterizeCell(action: RigAction, frame: number, direction: number): Cell {
  const safeDirection = ((Math.round(direction) % ATLAS_DIRECTIONS) + ATLAS_DIRECTIONS) % ATLAS_DIRECTIONS;
  const safeFrame = ((Math.floor(frame) % ATLAS_FRAMES) + ATLAS_FRAMES) % ATLAS_FRAMES;
  const key = `${action}:${safeFrame}:${safeDirection}`;
  const cached = cellCache.get(key);
  if (cached) return cached;
  const pose = poseFor(action, safeFrame);
  const body = new Uint8ClampedArray(CELL * CELL * 4);
  const kit = new Uint8ClampedArray(CELL * CELL * 4);
  const dirAngle = (safeDirection / ATLAS_DIRECTIONS) * Math.PI * 2;
  const cosDir = Math.cos(dirAngle);
  const sinDir = Math.sin(dirAngle);
  const side = Math.abs(cosDir);
  const xMul = 0.22 + 0.78 * side;
  const stance = 8 * (1 - side);
  const cx = CELL / 2 + pose.lean * 10 * (cosDir >= 0 ? side : -side);
  const hipY = 43 - pose.jump;
  const shoulderY = hipY - 16;
  const headY = shoulderY - 9 - pose.headLift;

  // Ground contact shadow + subtle directional chevron
  fillDisk(body, cx, 56, 13.5, 3.4, [0, 0, 0, 88]);
  fillDisk(body, cx + cosDir * 6, 56 - sinDir * 1.6, 3.2, 1.4, [255, 255, 255, 64]);

  const isKeeperAction = action === "save" || action === "dive";
  const arm = (angles: [number, number], originX: number, outline: boolean) => {
    const shoulder = { x: originX, y: shoulderY + 2 };
    const elbow = boneEnd(shoulder.x, shoulder.y, angles[0], UPPER_ARM);
    const hand = boneEnd(elbow.x, elbow.y, angles[0] + angles[1], FOREARM);
    const swayElbow = { x: shoulder.x + (elbow.x - shoulder.x) * xMul, y: elbow.y };
    const swayHand = { x: swayElbow.x + (hand.x - elbow.x) * xMul, y: hand.y };
    if (outline) capsule(body, shoulder.x, shoulder.y, swayHand.x, swayHand.y, 3.3, OUTLINE);
    // Short sleeve kit cap
    capsule(kit, shoulder.x, shoulder.y, (shoulder.x + swayElbow.x) * 0.5, (shoulder.y + swayElbow.y) * 0.5, 2.6, KIT);
    capsule(body, (shoulder.x + swayElbow.x) * 0.5, (shoulder.y + swayElbow.y) * 0.5, swayElbow.x, swayElbow.y, 2.4, SKIN);
    capsule(body, swayElbow.x, swayElbow.y, swayHand.x, swayHand.y, 2.1, SKIN);
    if (isKeeperAction) {
      fillDisk(body, swayHand.x, swayHand.y, 2.9, 2.9, [248, 250, 252, 255]);
    }
  };
  const leg = (angles: [number, number], originX: number) => {
    const hip = { x: originX, y: hipY };
    const knee = boneEnd(hip.x, hip.y, angles[0], THIGH);
    const foot = boneEnd(knee.x, knee.y, angles[0] + angles[1], SHIN);
    const swayKnee = { x: hip.x + (knee.x - hip.x) * xMul + pose.torsoTilt * 4, y: knee.y };
    const swayFoot = { x: swayKnee.x + (foot.x - knee.x) * xMul, y: foot.y };
    capsule(body, hip.x, hip.y, swayFoot.x, swayFoot.y, 3.4, OUTLINE);
    capsule(kit, hip.x, hip.y + 2, swayKnee.x, swayKnee.y, 2.5, KIT);
    capsule(kit, swayKnee.x, swayKnee.y, swayFoot.x, swayFoot.y - 3, 2.1, KIT_SHADE);
    fillDisk(body, swayFoot.x, swayFoot.y - 3.5, 2.1, 1.1, SOCK_BAND);
    const toeOffset = Math.sin(angles[0]) * 3 + cosDir * 1.2;
    capsule(body, swayFoot.x, swayFoot.y - 1, swayFoot.x + toeOffset, swayFoot.y + 1, 2.3, BOOT);
    plot(body, swayFoot.x + toeOffset * 0.6, swayFoot.y + 1.5, BOOT_STUD);
  };
  const leftHip = cx - stance;
  const rightHip = cx + stance;
  arm(pose.leftArm, leftHip, true);
  leg(pose.leftLeg, leftHip);
  const tilt = pose.torsoTilt * 8;
  fillTaper(body, cx + tilt, shoulderY - 1, hipY + 1, 10.2, 7.6, OUTLINE);
  fillTaper(kit, cx + tilt, shoulderY, hipY, 8.4, 6.4, KIT);
  // Subtle collar detail on jersey
  fillDisk(body, cx + tilt + cosDir * 1.4, shoulderY + 1.2, 3.2, 1.5, OUTLINE);
  fillTaper(kit, cx + tilt * 0.4, hipY - 1, hipY + 7, 7.5, 8.3, KIT_SHADE);
  arm(pose.rightArm, rightHip, true);
  leg(pose.rightLeg, rightHip);
  fillDisk(body, cx + tilt, headY, 6.2, 7.1, OUTLINE);
  fillDisk(body, cx + tilt + cosDir * 0.9, headY, 5.2, 6.1, SKIN);
  fillDisk(body, cx + tilt - cosDir * 0.8, headY - 3.2 - sinDir * 0.6, 5.4, 3.5, HAIR);
  const cell = { body, kit };
  cellCache.set(key, cell);
  return cell;
}

export function buildAtlasPixels() {
  if (cachedAtlas) return cachedAtlas;
  const width = ATLAS_COLUMNS * CELL;
  const height = ATLAS_ROWS * CELL;
  const body = new Uint8Array(width * height * 4);
  const kit = new Uint8Array(width * height * 4);
  RIG_ACTIONS.forEach((action, row) => {
    for (let direction = 0; direction < ATLAS_DIRECTIONS; direction += 1) {
      for (let frame = 0; frame < ATLAS_FRAMES; frame += 1) {
        const cell = rasterizeCell(action, frame, direction);
        const originX = (direction * ATLAS_FRAMES + frame) * CELL;
        const originY = row * CELL;
        blit(body, width, cell.body, originX, originY);
        blit(kit, width, cell.kit, originX, originY);
      }
    }
  });
  cachedAtlas = { body, kit, width, height };
  return cachedAtlas;
}

function blit(target: Uint8Array, width: number, source: Uint8ClampedArray, originX: number, originY: number) {
  for (let y = 0; y < CELL; y += 1) {
    const dest = ((originY + y) * width + originX) * 4;
    target.set(source.subarray(y * CELL * 4, (y + 1) * CELL * 4), dest);
  }
}

const DIGIT_ROWS = [
  ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
  ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
  ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
  ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
  ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
  ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
  ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
  ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
  ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
  ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
];

export function buildDigitPixels() {
  if (cachedDigits) return cachedDigits;
  const width = 10 * 5;
  const height = 7;
  const data = new Uint8Array(width * height * 4);
  DIGIT_ROWS.forEach((rows, digit) => {
    rows.forEach((row, y) => {
      for (let x = 0; x < 5; x += 1) {
        if (row[x] !== "1") continue;
        const index = (y * width + digit * 5 + x) * 4;
        data[index] = 255;
        data[index + 1] = 255;
        data[index + 2] = 255;
        data[index + 3] = 255;
      }
    });
  });
  cachedDigits = { data, width, height };
  return cachedDigits;
}

function stampNumber(target: Uint8ClampedArray, shirtNumber: number) {
  const digits = String(Math.max(0, Math.min(99, Math.floor(shirtNumber)))).padStart(shirtNumber >= 10 ? 2 : 1, "0");
  const scale = 1;
  const totalWidth = digits.length * 5 * scale + (digits.length - 1);
  let cursor = Math.round(CELL / 2 - totalWidth / 2);
  const top = 28;
  for (const char of digits) {
    const rows = DIGIT_ROWS[Number(char)] || DIGIT_ROWS[0];
    rows.forEach((row, y) => {
      for (let x = 0; x < 5; x += 1) {
        if (row[x] !== "1") continue;
        plot(target, cursor + x * scale, top + y * scale, [248, 250, 252, 255]);
      }
    });
    cursor += 6;
  }
}

export function compositeCell(cell: Cell, kitColor: string, shirtNumber: number): Uint8ClampedArray {
  const merged = new Uint8ClampedArray(cell.body);
  const tint = hexToRgb(kitColor);
  for (let index = 0; index < cell.kit.length; index += 4) {
    const cover = cell.kit[index + 3] / 255;
    if (cover <= 0) continue;
    const shade = cell.kit[index] / 255;
    merged[index] = tint[0] * shade * cover + merged[index] * (1 - cover);
    merged[index + 1] = tint[1] * shade * cover + merged[index + 1] * (1 - cover);
    merged[index + 2] = tint[2] * shade * cover + merged[index + 2] * (1 - cover);
    merged[index + 3] = Math.max(merged[index + 3], cell.kit[index + 3]);
  }
  stampNumber(merged, shirtNumber);
  return merged;
}

function getCachedSpriteCanvas(spec: {
  action: RigAction;
  frame: number;
  direction: number;
  kitColor: string;
  shirtNumber: number;
}): HTMLCanvasElement | null {
  const safeDirection = ((Math.round(spec.direction) % ATLAS_DIRECTIONS) + ATLAS_DIRECTIONS) % ATLAS_DIRECTIONS;
  const safeFrame = ((Math.floor(spec.frame) % ATLAS_FRAMES) + ATLAS_FRAMES) % ATLAS_FRAMES;
  const safeShirt = Math.max(0, Math.min(99, Math.floor(spec.shirtNumber || 0)));
  const cacheKey = `${spec.action}:${safeFrame}:${safeDirection}:${spec.kitColor}:${safeShirt}`;
  const existing = spriteCanvasCache.get(cacheKey);
  if (existing) return existing;

  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = CELL;
  canvas.height = CELL;
  let local: CanvasRenderingContext2D | null = null;
  try {
    local = canvas.getContext("2d");
  } catch {
    local = null;
  }
  if (!local) return null;

  const merged = compositeCell(rasterizeCell(spec.action, safeFrame, safeDirection), spec.kitColor, safeShirt);
  if (typeof ImageData !== "undefined") {
    local.putImageData(new ImageData(new Uint8ClampedArray(merged), CELL, CELL), 0, 0);
  }
  if (spriteCanvasCache.size >= MAX_SPRITE_CACHE) {
    const oldest = spriteCanvasCache.keys().next().value;
    if (oldest) spriteCanvasCache.delete(oldest);
  }
  spriteCanvasCache.set(cacheKey, canvas);
  return canvas;
}

export function paintRig(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  spec: { action: RigAction; frame: number; direction: number; kitColor: string; shirtNumber: number },
) {
  const cached = getCachedSpriteCanvas(spec);
  if (!cached) return;
  ctx.drawImage(cached, x - size / 2, y - size * 0.85, size, size);
}

export function getCachedPitchBitmap(width = 512, height = 320): HTMLCanvasElement | null {
  const key = `${width}x${height}`;
  const cached = pitchCanvasCache.get(key);
  if (cached) return cached;
  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  let ctx: CanvasRenderingContext2D | null = null;
  try {
    ctx = canvas.getContext("2d");
  } catch {
    ctx = null;
  }
  if (!ctx) return null;
  const pixels = rasterPitch(width, height);
  if (typeof ImageData !== "undefined") {
    ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels), width, height), 0, 0);
  }
  pitchCanvasCache.set(key, canvas);
  return canvas;
}

export function getCachedBallBitmap(): HTMLCanvasElement | null {
  if (cachedBallCanvas) return cachedBallCanvas;
  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = 48;
  canvas.height = 48;
  let ctx: CanvasRenderingContext2D | null = null;
  try {
    ctx = canvas.getContext("2d");
  } catch {
    ctx = null;
  }
  if (!ctx) return null;
  const pixels = rasterBall();
  if (typeof ImageData !== "undefined") {
    ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels), 48, 48), 0, 0);
  }
  cachedBallCanvas = canvas;
  return canvas;
}

export function getCachedRingBitmap(): HTMLCanvasElement | null {
  if (cachedRingCanvas) return cachedRingCanvas;
  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  let ctx: CanvasRenderingContext2D | null = null;
  try {
    ctx = canvas.getContext("2d");
  } catch {
    ctx = null;
  }
  if (!ctx) return null;
  const pixels = rasterRing();
  if (typeof ImageData !== "undefined") {
    ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels), 64, 64), 0, 0);
  }
  cachedRingCanvas = canvas;
  return canvas;
}

function hexToRgb(hex: string): [number, number, number] {
  const cleaned = String(hex || "#ffffff").replace("#", "");
  const value = cleaned.length === 3 ? cleaned.split("").map((part) => part + part).join("") : cleaned.padEnd(6, "0");
  return [
    parseInt(value.slice(0, 2), 16) || 0,
    parseInt(value.slice(2, 4), 16) || 0,
    parseInt(value.slice(4, 6), 16) || 0,
  ];
}

export function rasterPitch(width = 512, height = 320): Uint8Array {
  const key = `${width}x${height}`;
  const existing = cachedPitchPixels.get(key);
  if (existing) return existing;

  const data = new Uint8Array(width * height * 4);
  const centerX = width / 2;
  const centerY = height / 2;
  const leftLine = 28;
  const rightLine = width - 28;
  const topLine = 18;
  const bottomLine = height - 18;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const inPlay = x >= leftLine && x <= rightLine && y >= topLine && y <= bottomLine;
      const vStripe = Math.floor(x / (width / 16)) % 2;
      const hBand = Math.floor(y / (height / 10)) % 2;
      const dx = (x - centerX) / width;
      const dy = (y - centerY) / height;
      const vignette = Math.min(1, (dx * dx * 2.4 + dy * dy * 2.6));
      const worn = Math.exp(-(dx * dx * 10 + dy * dy * 7));
      const boxWear =
        x < width * 0.22 || x > width * 0.78 ? Math.exp(-((((y - centerY) / height) ** 2) * 8)) * 0.28 : 0;

      if (!inPlay) {
        // Dark stadium perimeter surround
        const r = Math.max(8, Math.round(12 - vignette * 4));
        const g = Math.max(24, Math.round(46 - vignette * 12));
        const b = Math.max(16, Math.round(28 - vignette * 8));
        setPixel(data, width, x, y, r, g, b, 255);
      } else {
        const turfCut = (vStripe ? 14 : 0) + (hBand ? 4 : 0);
        const red = Math.round(16 + worn * 8 + (vStripe ? 3 : 0));
        const green = Math.round(96 + turfCut - worn * 12 - boxWear * 16 - vignette * 10);
        const blue = Math.round(48 + (vStripe ? 4 : 0) - worn * 6 - vignette * 6);
        setPixel(data, width, x, y, red, green, blue, 255);
      }
    }
  }

  const lineColor: [number, number, number, number] = [240, 248, 242, 238];
  const subLineColor: [number, number, number, number] = [240, 248, 242, 70];
  const line = (x0: number, y0: number, x1: number, y1: number) => {
    stroke(data, width, height, x0, y0, x1, y1, lineColor);
    stroke(data, width, height, x0, y0 + 0.6, x1, y1 + 0.6, subLineColor);
  };

  // Outer touchlines & goal lines
  line(leftLine, topLine, rightLine, topLine);
  line(leftLine, bottomLine, rightLine, bottomLine);
  line(leftLine, topLine, leftLine, bottomLine);
  line(rightLine, topLine, rightLine, bottomLine);
  // Halfway line & center circle + spot
  line(centerX, topLine, centerX, bottomLine);
  strokeCircle(data, width, height, centerX, centerY, 42);
  fillSpot(data, width, height, centerX, centerY, 2.6, lineColor);

  // Penalty boxes & 6-yard goal areas
  strokeBox(data, width, height, leftLine, centerY - 62, 78, 124);
  strokeBox(data, width, height, rightLine - 78, centerY - 62, 78, 124);
  strokeBox(data, width, height, leftLine, centerY - 28, 32, 56);
  strokeBox(data, width, height, rightLine - 32, centerY - 28, 32, 56);

  // Penalty spots & penalty arcs ("D")
  const homeSpotX = leftLine + 52;
  const awaySpotX = rightLine - 52;
  fillSpot(data, width, height, homeSpotX, centerY, 2.2, lineColor);
  fillSpot(data, width, height, awaySpotX, centerY, 2.2, lineColor);
  strokeArc(data, width, height, homeSpotX, centerY, 36, -0.92, 0.92, lineColor);
  strokeArc(data, width, height, awaySpotX, centerY, 36, Math.PI - 0.92, Math.PI + 0.92, lineColor);

  // Corner arcs
  strokeArc(data, width, height, leftLine, topLine, 8, 0, Math.PI / 2, lineColor);
  strokeArc(data, width, height, leftLine, bottomLine, 8, -Math.PI / 2, 0, lineColor);
  strokeArc(data, width, height, rightLine, topLine, 8, Math.PI / 2, Math.PI, lineColor);
  strokeArc(data, width, height, rightLine, bottomLine, 8, Math.PI, (Math.PI * 3) / 2, lineColor);

  // Goals
  drawGoal(data, width, height, 8, centerY, 1);
  drawGoal(data, width, height, width - 8, centerY, -1);

  cachedPitchPixels.set(key, data);
  return data;
}

function drawGoal(data: Uint8Array, width: number, height: number, goalX: number, centerY: number, direction: number) {
  const post = direction > 0 ? goalX : goalX - 20;
  for (let y = centerY - 24; y <= centerY + 24; y += 3) {
    stroke(data, width, height, post, y, post + 20, y, [216, 232, 224, 145]);
  }
  for (let x = 0; x <= 20; x += 3) {
    stroke(data, width, height, post + x, centerY - 24, post + x, centerY + 24, [216, 232, 224, 145]);
  }
  stroke(data, width, height, post, centerY - 25, post, centerY + 25, [248, 250, 252, 255]);
  stroke(data, width, height, post + 20, centerY - 25, post + 20, centerY + 25, [248, 250, 252, 255]);
  stroke(data, width, height, post, centerY - 25, post + 20, centerY - 25, [248, 250, 252, 255]);
  stroke(data, width, height, post, centerY + 25, post + 20, centerY + 25, [248, 250, 252, 255]);
}

export function rasterBall(): Uint8Array {
  if (cachedBallPixels) return cachedBallPixels;
  const size = 48;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const shadow = ((x - 24) / 14) ** 2 + ((y - 39) / 4.2) ** 2;
      if (shadow <= 1) setPixel(data, size, x, y, 0, 0, 0, 95);
      const dx = x - 24;
      const dy = y - 20;
      const distance = Math.hypot(dx, dy);
      if (distance > 12) continue;
      if (distance > 10.6) {
        setPixel(data, size, x, y, 15, 23, 42, 255);
        continue;
      }
      const light = Math.max(0, 1 - Math.hypot(dx + 4, dy + 4) / 16);
      const shade = 204 + light * 51;
      const panel = Math.abs(Math.sin(Math.atan2(dy, dx) * 3)) < 0.18 || Math.abs(dy) < 1.2;
      const value = panel ? shade * 0.38 : shade;
      setPixel(data, size, x, y, value, value, value, 255);
    }
  }
  cachedBallPixels = data;
  return data;
}

export function rasterRing(): Uint8Array {
  if (cachedRingPixels) return cachedRingPixels;
  const size = 64;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const dx = x - 32;
      const dy = y - 32;
      const distance = Math.hypot(dx, dy);
      if (distance > 22 && distance < 28) {
        setPixel(data, size, x, y, 255, 255, 255, 225);
      } else if (distance >= 18 && distance <= 20) {
        setPixel(data, size, x, y, 0, 232, 122, 175);
      }
    }
  }
  cachedRingPixels = data;
  return data;
}

function setPixel(data: Uint8Array, width: number, x: number, y: number, r: number, g: number, b: number, a: number) {
  const ix = x | 0;
  const iy = y | 0;
  if (ix < 0 || iy < 0 || a <= 0) return;
  const height = data.length / 4 / width;
  if (iy >= height || ix >= width) return;
  const index = (iy * width + ix) * 4;
  data[index] = r;
  data[index + 1] = g;
  data[index + 2] = b;
  data[index + 3] = a;
}

function fillSpot(
  data: Uint8Array,
  width: number,
  height: number,
  cx: number,
  cy: number,
  radius: number,
  color: [number, number, number, number],
) {
  for (let y = Math.floor(cy - radius - 1); y <= Math.ceil(cy + radius + 1); y += 1) {
    for (let x = Math.floor(cx - radius - 1); x <= Math.ceil(cx + radius + 1); x += 1) {
      if (Math.hypot(x - cx, y - cy) <= radius && x >= 0 && x < width && y >= 0 && y < height) {
        setPixel(data, width, x, y, color[0], color[1], color[2], color[3]);
      }
    }
  }
}

function stroke(
  data: Uint8Array,
  width: number,
  height: number,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  color: [number, number, number, number],
) {
  const steps = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0)));
  for (let step = 0; step <= steps; step += 1) {
    const t = step / steps;
    setPixel(data, width, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, color[0], color[1], color[2], color[3]);
  }
}

function strokeBox(data: Uint8Array, width: number, height: number, x: number, y: number, w: number, h: number) {
  stroke(data, width, height, x, y, x + w, y, [240, 248, 242, 238]);
  stroke(data, width, height, x, y + h, x + w, y + h, [240, 248, 242, 238]);
  stroke(data, width, height, x, y, x, y + h, [240, 248, 242, 238]);
  stroke(data, width, height, x + w, y, x + w, y + h, [240, 248, 242, 238]);
}

function strokeCircle(data: Uint8Array, width: number, height: number, cx: number, cy: number, radius: number) {
  const steps = 120;
  for (let step = 0; step <= steps; step += 1) {
    const angle = (step / steps) * Math.PI * 2;
    setPixel(data, width, cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius, 240, 248, 242, 238);
  }
}

function strokeArc(
  data: Uint8Array,
  width: number,
  height: number,
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number,
  color: [number, number, number, number],
) {
  const steps = 64;
  for (let step = 0; step <= steps; step += 1) {
    const angle = startAngle + ((endAngle - startAngle) * step) / steps;
    setPixel(data, width, cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius, color[0], color[1], color[2], color[3]);
  }
}

export function sampleTrajectory(points: { x: number; y: number }[], alpha: number): { x: number; y: number } | null {
  if (!points.length) return null;
  if (points.length === 1) return points[0];
  const t = Math.min(1, Math.max(0, alpha));
  const scaled = t * (points.length - 1);
  const index = Math.min(points.length - 2, Math.floor(scaled));
  const rest = scaled - index;
  return {
    x: points[index].x + (points[index + 1].x - points[index].x) * rest,
    y: points[index].y + (points[index + 1].y - points[index].y) * rest,
  };
}
