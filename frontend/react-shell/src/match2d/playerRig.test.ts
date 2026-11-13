import fs from "fs";
import path from "path";

import { compositeCell, footSpread, poseFor, rasterizeCell } from "./playerRig";

function combinedAlpha(body: Uint8ClampedArray, kit: Uint8ClampedArray, x: number, y: number) {
  const index = (y * 64 + x) * 4 + 3;
  return Math.max(body[index], kit[index]);
}

function rowRuns(body: Uint8ClampedArray, kit: Uint8ClampedArray, y: number) {
  const runs: number[] = [];
  let start = -1;
  for (let x = 0; x < 64; x += 1) {
    const filled = combinedAlpha(body, kit, x, y) > 24;
    if (filled && start < 0) start = x;
    if ((!filled || x === 63) && start >= 0) {
      runs.push((filled && x === 63 ? x + 1 : x) - start);
      start = -1;
    }
  }
  return runs;
}

describe("procedural player rig", () => {
  test("a sprint stride is longer than a walk stride and a header lifts the head", () => {
    expect(footSpread(poseFor("sprint", 1))).toBeGreaterThan(footSpread(poseFor("walk", 1)));
    expect(poseFor("header", 0).headLift).toBeGreaterThan(poseFor("idle", 0).headLift);
    expect(poseFor("dive", 0).torsoTilt).toBeGreaterThan(poseFor("save", 0).torsoTilt);
  });

  test("the atlas cell has a torso wider than the head and two separated legs", () => {
    const cell = rasterizeCell("idle", 0, 2);
    let headWidth = 0;
    let torsoWidth = 0;
    let splitLegs = false;
    for (let y = 0; y < 64; y += 1) {
      const runs = rowRuns(cell.body, cell.kit, y);
      const width = runs.reduce((sum, run) => sum + run, 0);
      if (y < 24) headWidth = Math.max(headWidth, width);
      if (y >= 24 && y <= 42) torsoWidth = Math.max(torsoWidth, width);
      if (y > 46 && runs.length >= 2 && runs.every((run) => run >= 2)) splitLegs = true;
    }
    expect(torsoWidth).toBeGreaterThan(headWidth);
    expect(headWidth).toBeGreaterThan(4);
    expect(splitLegs).toBe(true);
  });

  test("the kit mask covers the shirt and leaves the head untouched", () => {
    const cell = rasterizeCell("idle", 0, 2);
    let shirt = 0;
    let headKit = 0;
    for (let y = 0; y < 20; y += 1) {
      for (let x = 0; x < 64; x += 1) headKit = Math.max(headKit, cell.kit[(y * 64 + x) * 4 + 3]);
    }
    for (let y = 26; y < 40; y += 1) {
      for (let x = 20; x < 44; x += 1) shirt = Math.max(shirt, cell.kit[(y * 64 + x) * 4 + 3]);
    }
    expect(shirt).toBeGreaterThan(200);
    expect(headKit).toBe(0);
    const tinted = compositeCell(cell, "#ff0000", 9);
    const shirtIndex = (32 * 64 + 32) * 4;
    expect(tinted[shirtIndex]).toBeGreaterThan(180);
    expect(tinted[shirtIndex + 1]).toBeLessThan(80);
  });
});

describe("canvas fallback", () => {
  test("players are painted by the rig, not drawn as circles", () => {
    const src = fs.readFileSync(path.resolve(__dirname, "./OrthographicPitch.tsx"), "utf8");
    expect(src).toContain("paintRig(");
    expect(src).not.toContain(".arc(");
  });
});
