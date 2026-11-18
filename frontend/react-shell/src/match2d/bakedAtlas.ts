export type BakedManifest = {
  cell: number;
  directions: number;
  frames: number;
  actions: string[];
  anchors: Record<string, Array<Array<{ x: number; y: number }>>>;
};

export const BAKED_ATLAS = {
  body: "/models/footballer/atlas/body.png",
  kit: "/models/footballer/atlas/kit.png",
  parts: "/models/footballer/atlas/parts.png",
  manifest: "/models/footballer/atlas/manifest.json",
};

const ALIAS: Record<string, string> = {
  run: "sprint",
  accelerate: "sprint",
  decelerate: "jog",
  turn: "jog",
  through_pass: "pass",
  long_pass: "pass",
  cross: "pass",
  standing_tackle: "tackle",
  jump: "header",
  save: "dive",
  catch: "dive",
  parry: "dive",
  block: "tackle",
  feint: "dribble",
  intercept: "tackle",
};

export function bakedAction(action: string, manifest: BakedManifest): string {
  if (manifest.actions.includes(action)) return action;
  const alias = ALIAS[action];
  if (alias && manifest.actions.includes(alias)) return alias;
  return manifest.actions.includes("idle") ? "idle" : manifest.actions[0];
}

export function bakedUv(manifest: BakedManifest, action: string, direction: number, phase: number) {
  const name = bakedAction(action, manifest);
  const row = Math.max(0, manifest.actions.indexOf(name));
  const columns = manifest.directions * manifest.frames;
  const safeDir = ((Math.round(direction) % manifest.directions) + manifest.directions) % manifest.directions;
  const wrapped = ((phase % 4) + 4) % 4;
  const safeFrame = Math.min(manifest.frames - 1, Math.floor((wrapped / 4) * manifest.frames));
  const column = safeDir * manifest.frames + safeFrame;
  return {
    offsetX: column / columns,
    offsetY: 1 - (row + 1) / manifest.actions.length,
    repeatX: 1 / columns,
    repeatY: 1 / manifest.actions.length,
    anchor: manifest.anchors[name]?.[safeFrame]?.[safeDir] || { x: 0.62, y: 0.2 },
  };
}
