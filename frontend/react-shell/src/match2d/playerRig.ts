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
const OUTLINE = [18, 28, 22, 255] as const;
const KIT = [255, 255, 255, 255] as const;

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

export function actionIndex(action: string): number {
  const index = RIG_ACTIONS.indexOf(action as RigAction);
  return index >= 0 ? index : 0;
}

export function cellUv(action: string, direction: number, frame: number) {
  const column = (direction % ATLAS_DIRECTIONS) * ATLAS_FRAMES + (frame % ATLAS_FRAMES);
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

export function poseFor(action: RigAction, frame: number): Pose {
  const step = swing(frame);
  const gait = (amp: number, lean: number, arm: number, knee = 0.22): Pose => ({
    lean,
    headLift: 0,
    jump: 0,
    torsoTilt: 0,
    leftArm: [0.35 + step * arm, 0.25],
    rightArm: [0.35 - step * arm, 0.25],
    leftLeg: [-step * amp, Math.abs(step) * knee],
    rightLeg: [step * amp, Math.abs(step) * knee],
  });
  if (action === "idle") return gait(0.08, 0.02, 0.06, 0.05);
  if (action === "walk") return gait(0.48, 0.1, 0.42);
  if (action === "jog") return gait(0.78, 0.2, 0.72);
  if (action === "sprint") return gait(1.12, 0.38, 1.05, 0.18);
  if (action === "dribble") return gait(0.52, 0.14, 0.28, 0.16);
  if (action === "accelerate") return { ...gait(0.96, 0.58, 0.84, 0.16), torsoTilt: 0.15 };
  if (action === "turn") return { ...gait(0.32, 0.08, 0.55), torsoTilt: 0.7 * step };
  if (action === "pass") {
    return {
      lean: 0.12,
      headLift: 1,
      jump: 0,
      torsoTilt: 0.2,
      leftArm: [1.1, 0.2],
      rightArm: [0.4, 0.3],
      leftLeg: [0.3, 0.2],
      rightLeg: [-1.05, 0.15],
    };
  }
  if (action === "shoot") {
    return {
      lean: -0.18,
      headLift: 2,
      jump: 1,
      torsoTilt: -0.15,
      leftArm: [0.8, 0.4],
      rightArm: [1.3, 0.2],
      leftLeg: [0.45, 0.35],
      rightLeg: [-1.35, 0.08],
    };
  }
  if (action === "tackle") {
    return {
      lean: 0.55,
      headLift: 0,
      jump: 0,
      torsoTilt: 0.35,
      leftArm: [0.9, 0.2],
      rightArm: [0.4, 0.2],
      leftLeg: [0.2, 0.4],
      rightLeg: [-1.25, 0.05],
    };
  }
  if (action === "jump") {
    return {
      lean: 0.05,
      headLift: 2,
      jump: 10,
      torsoTilt: 0,
      leftArm: [2.4, 0.2],
      rightArm: [2.2, 0.2],
      leftLeg: [0.4, 0.9],
      rightLeg: [-0.35, 0.85],
    };
  }
  if (action === "header") {
    return {
      lean: 0.08,
      headLift: 12,
      jump: 8,
      torsoTilt: -0.25,
      leftArm: [2.5, 0.15],
      rightArm: [2.35, 0.15],
      leftLeg: [0.25, 0.7],
      rightLeg: [-0.2, 0.65],
    };
  }
  if (action === "save") {
    return {
      lean: 0.1,
      headLift: 4,
      jump: 3,
      torsoTilt: 0.45,
      leftArm: [2.7, 0.05],
      rightArm: [1.2, 0.2],
      leftLeg: [0.15, 0.2],
      rightLeg: [-0.2, 0.25],
    };
  }
  if (action === "dive") {
    return {
      lean: 0.2,
      headLift: 0,
      jump: 2,
      torsoTilt: 1.45,
      leftArm: [2.2, 0.1],
      rightArm: [0.6, 0.15],
      leftLeg: [0.9, 0.1],
      rightLeg: [0.35, 0.15],
    };
  }
  return {
    lean: -0.05,
    headLift: 3,
    jump: 2,
    torsoTilt: 0,
    leftArm: [2.6, 0.1],
    rightArm: [2.45, 0.1],
    leftLeg: [0.15, 0.1],
    rightLeg: [-0.15, 0.1],
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

export function presentationAction(
  base: string,
  motion: { facingDelta: number; speed: number; previousSpeed: number; hasBall: boolean },
): RigAction {
  const known = (RIG_ACTIONS as readonly string[]).includes(base);
  const action = known ? (base as RigAction) : "idle";
  if (action === "pass" || action === "shoot" || action === "tackle" || action === "header" || action === "jump" || action === "save" || action === "dive" || action === "celebrate") {
    return action;
  }
  if (Math.abs(motion.facingDelta) > 0.9) return "turn";
  if (motion.speed - motion.previousSpeed > 0.008 && motion.speed > 0.006) return "accelerate";
  if (motion.hasBall && motion.speed > 0.004) return "dribble";
  if (motion.speed > 0.02) return "sprint";
  if (motion.speed > 0.01) return "jog";
  if (motion.speed > 0.004) return "walk";
  return action === "sprint" || action === "jog" || action === "walk" || action === "dribble" ? action : "idle";
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

function fillDisk(data: Uint8ClampedArray, cx: number, cy: number, rx: number, ry: number, color: readonly [number, number, number, number]) {
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

function capsule(data: Uint8ClampedArray, x0: number, y0: number, x1: number, y1: number, radius: number, color: readonly [number, number, number, number]) {
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
  const key = `${action}:${frame}:${direction}`;
  const cached = cellCache.get(key);
  if (cached) return cached;
  const pose = poseFor(action, frame);
  const body = new Uint8ClampedArray(CELL * CELL * 4);
  const kit = new Uint8ClampedArray(CELL * CELL * 4);
  const side = Math.abs(Math.cos((direction / ATLAS_DIRECTIONS) * Math.PI * 2));
  const xMul = 0.22 + 0.78 * side;
  const stance = 8 * (1 - side);
  const cx = CELL / 2 + pose.lean * 10 * side;
  const hipY = 43 - pose.jump;
  const shoulderY = hipY - 16;
  const headY = shoulderY - 9 - pose.headLift;
  fillDisk(body, cx, 56, 13, 3.2, [0, 0, 0, 72]);
  const arm = (angles: [number, number], originX: number, outline: boolean) => {
    const shoulder = { x: originX, y: shoulderY + 2 };
    const elbow = boneEnd(shoulder.x, shoulder.y, angles[0], UPPER_ARM);
    const hand = boneEnd(elbow.x, elbow.y, angles[0] + angles[1], FOREARM);
    const swayElbow = { x: shoulder.x + (elbow.x - shoulder.x) * xMul, y: elbow.y };
    const swayHand = { x: swayElbow.x + (hand.x - elbow.x) * xMul, y: hand.y };
    if (outline) capsule(body, shoulder.x, shoulder.y, swayHand.x, swayHand.y, 3.3, OUTLINE);
    capsule(body, shoulder.x, shoulder.y, swayElbow.x, swayElbow.y, 2.4, SKIN);
    capsule(body, swayElbow.x, swayElbow.y, swayHand.x, swayHand.y, 2.1, SKIN);
  };
  const leg = (angles: [number, number], originX: number) => {
    const hip = { x: originX, y: hipY };
    const knee = boneEnd(hip.x, hip.y, angles[0], THIGH);
    const foot = boneEnd(knee.x, knee.y, angles[0] + angles[1], SHIN);
    const swayKnee = { x: hip.x + (knee.x - hip.x) * xMul + pose.torsoTilt * 4, y: knee.y };
    const swayFoot = { x: swayKnee.x + (foot.x - knee.x) * xMul, y: foot.y };
    capsule(body, hip.x, hip.y, swayFoot.x, swayFoot.y, 3.4, OUTLINE);
    capsule(kit, hip.x, hip.y + 2, swayKnee.x, swayKnee.y, 2.5, KIT);
    capsule(kit, swayKnee.x, swayKnee.y, swayFoot.x, swayFoot.y - 3, 2.1, KIT);
    capsule(body, swayFoot.x, swayFoot.y - 1, swayFoot.x + Math.sin(angles[0]) * 3, swayFoot.y + 1, 2.3, BOOT);
  };
  const leftHip = cx - stance;
  const rightHip = cx + stance;
  arm(pose.leftArm, leftHip, true);
  leg(pose.leftLeg, leftHip);
  const tilt = pose.torsoTilt * 8;
  fillTaper(body, cx + tilt, shoulderY - 1, hipY + 1, 10, 7.5, OUTLINE);
  fillTaper(kit, cx + tilt, shoulderY, hipY, 8.2, 6.2, KIT);
  fillTaper(kit, cx + tilt * 0.4, hipY - 1, hipY + 7, 7.4, 8.2, KIT);
  arm(pose.rightArm, rightHip, true);
  leg(pose.rightLeg, rightHip);
  fillDisk(body, cx + tilt, headY, 6.2, 7.1, OUTLINE);
  fillDisk(body, cx + tilt, headY, 5.2, 6.1, SKIN);
  fillDisk(body, cx + tilt, headY - 3.2, 5.4, 3.4, HAIR);
  const cell = { body, kit };
  cellCache.set(key, cell);
  return cell;
}

export function buildAtlasPixels() {
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
  return { body, kit, width, height };
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
  return { data, width, height };
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
    merged[index] = tint[0] * cover + merged[index] * (1 - cover);
    merged[index + 1] = tint[1] * cover + merged[index + 1] * (1 - cover);
    merged[index + 2] = tint[2] * cover + merged[index + 2] * (1 - cover);
    merged[index + 3] = Math.max(merged[index + 3], cell.kit[index + 3]);
  }
  stampNumber(merged, shirtNumber);
  return merged;
}

export function paintRig(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  spec: { action: RigAction; frame: number; direction: number; kitColor: string; shirtNumber: number },
) {
  const merged = compositeCell(rasterizeCell(spec.action, spec.frame, spec.direction), spec.kitColor, spec.shirtNumber);
  const canvas = document.createElement("canvas");
  canvas.width = CELL;
  canvas.height = CELL;
  const local = canvas.getContext("2d");
  if (!local) return;
  local.putImageData(new ImageData(merged, CELL, CELL), 0, 0);
  ctx.drawImage(canvas, x - size / 2, y - size, size, size);
}

function hexToRgb(hex: string): [number, number, number] {
  const cleaned = hex.replace("#", "");
  const value = cleaned.length === 3 ? cleaned.split("").map((part) => part + part).join("") : cleaned.padEnd(6, "0");
  return [parseInt(value.slice(0, 2), 16) || 0, parseInt(value.slice(2, 4), 16) || 0, parseInt(value.slice(4, 6), 16) || 0];
}

export function rasterPitch(width = 512, height = 320): Uint8Array {
  const data = new Uint8Array(width * height * 4);
  const centerX = width / 2;
  const centerY = height / 2;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const stripe = Math.floor(x / (width / 12)) % 2;
      const dx = (x - centerX) / width;
      const dy = (y - centerY) / height;
      const worn = Math.exp(-(dx * dx * 10 + dy * dy * 7));
      const boxWear = x < width * 0.22 || x > width * 0.78 ? Math.exp(-((((y - centerY) / height) ** 2) * 8)) * 0.35 : 0;
      const red = 16 + worn * 10;
      const green = (stripe ? 104 : 122) - worn * 16 - boxWear * 20;
      const blue = 52 - worn * 8;
      setPixel(data, width, x, y, red, green, blue, 255);
    }
  }
  const line = (x0: number, y0: number, x1: number, y1: number) => stroke(data, width, height, x0, y0, x1, y1, [236, 242, 236, 230]);
  line(28, 18, width - 28, 18);
  line(28, height - 18, width - 28, height - 18);
  line(28, 18, 28, height - 18);
  line(width - 28, 18, width - 28, height - 18);
  line(centerX, 18, centerX, height - 18);
  strokeCircle(data, width, height, centerX, centerY, 42);
  strokeBox(data, width, height, 28, centerY - 62, 78, 124);
  strokeBox(data, width, height, width - 106, centerY - 62, 78, 124);
  strokeBox(data, width, height, 28, centerY - 28, 32, 56);
  strokeBox(data, width, height, width - 60, centerY - 28, 32, 56);
  drawGoal(data, width, height, 8, centerY, 1);
  drawGoal(data, width, height, width - 8, centerY, -1);
  return data;
}

function drawGoal(data: Uint8Array, width: number, height: number, goalX: number, centerY: number, direction: number) {
  const post = direction > 0 ? goalX : goalX - 22;
  for (let y = centerY - 34; y <= centerY + 34; y += 4) {
    stroke(data, width, height, post, y, post + 22, y, [226, 232, 226, 150]);
  }
  for (let x = 0; x <= 22; x += 4) {
    stroke(data, width, height, post + x, centerY - 34, post + x, centerY + 34, [226, 232, 226, 150]);
  }
  stroke(data, width, height, post, centerY - 36, post, centerY + 36, [248, 250, 252, 255]);
  stroke(data, width, height, post + 22, centerY - 36, post + 22, centerY + 36, [248, 250, 252, 255]);
  stroke(data, width, height, post, centerY - 36, post + 22, centerY - 36, [248, 250, 252, 255]);
}

export function rasterBall(): Uint8Array {
  const size = 48;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const shadow = ((x - 24) / 14) ** 2 + ((y - 40) / 4) ** 2;
      if (shadow <= 1) setPixel(data, size, x, y, 0, 0, 0, 80);
      const dx = x - 24;
      const dy = y - 20;
      const distance = Math.hypot(dx, dy);
      if (distance > 11) continue;
      const light = Math.max(0, 1 - Math.hypot(dx + 4, dy + 4) / 16);
      const shade = 198 + light * 57;
      const panel = Math.abs(Math.sin(Math.atan2(dy, dx) * 3)) < 0.18 || Math.abs(dy) < 1.2;
      const value = panel ? shade * 0.45 : shade;
      setPixel(data, size, x, y, value, value, value, 255);
    }
  }
  return data;
}

export function rasterRing(): Uint8Array {
  const size = 64;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const distance = Math.hypot(x - 32, y - 32);
      if (distance > 22 && distance < 28) setPixel(data, size, x, y, 255, 255, 255, 210);
    }
  }
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

function stroke(data: Uint8Array, width: number, height: number, x0: number, y0: number, x1: number, y1: number, color: [number, number, number, number]) {
  const steps = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0)));
  for (let step = 0; step <= steps; step += 1) {
    const t = step / steps;
    setPixel(data, width, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, color[0], color[1], color[2], color[3]);
  }
}

function strokeBox(data: Uint8Array, width: number, height: number, x: number, y: number, w: number, h: number) {
  stroke(data, width, height, x, y, x + w, y, [236, 242, 236, 230]);
  stroke(data, width, height, x, y + h, x + w, y + h, [236, 242, 236, 230]);
  stroke(data, width, height, x, y, x, y + h, [236, 242, 236, 230]);
  stroke(data, width, height, x + w, y, x + w, y + h, [236, 242, 236, 230]);
}

function strokeCircle(data: Uint8Array, width: number, height: number, cx: number, cy: number, radius: number) {
  const steps = 96;
  for (let step = 0; step <= steps; step += 1) {
    const angle = (step / steps) * Math.PI * 2;
    setPixel(data, width, cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius, 236, 242, 236, 230);
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
