/**
 * Paints an 8-direction, 8-frame atlas of the GT Mixamo kit
 * so the 2D and 2.5D pitch uses the same body as WebGL.
 */
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

globalThis.window = globalThis;
globalThis.self = globalThis;
globalThis.document = {
  createElementNS: () => ({ style: {} }),
  createElement: () => ({ style: {}, getContext: () => null }),
};
class NodeFileReader {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((ab) => {
      this.result = ab;
      if (this.onloadend) this.onloadend();
    });
  }
}
globalThis.FileReader = NodeFileReader;

const CELL = 64;
const DIRECTIONS = 8;
const FRAMES = 8;
const shell = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(shell, "public/models/footballer/atlas");

const ACTIONS = [
  { id: "idle", clip: "Breathing_Idle" },
  { id: "walk", clip: "Walking_Forwards" },
  { id: "jog", clip: "Soccer_Jog_Forward" },
  { id: "sprint", clip: "Running_Forwards" },
  { id: "dribble", clip: "Forward_Jog_Dribbling_Soccer_Ball" },
  { id: "dribble_run", clip: "Gtex_Dribble_Run" },
  { id: "pass", clip: "Soccer_Pass_From_Idle_Pose" },
  { id: "shoot", clip: "Gtex_Strike" },
  { id: "tackle", clip: "Gtex_Standing_Tackle" },
  { id: "slide_tackle", clip: "Soccer_Slide_Tackle" },
  { id: "header", clip: "Idle_Soccer_Header" },
  { id: "celebrate", clip: "Kicking_Up_A_Soccer_Ball" },
  { id: "frustrated", clip: "Gtex_Slump" },
  { id: "control", clip: "Soccer_Idle_Chest_Receive" },
  { id: "dive", clip: "Goalkeeper_Left_Diving_Save" },
];

const PART = { shirt: 1, shorts: 2, socks: 3, skin: 4, hair: 5, boots: 6, gloves: 7 };

function parseGltf(filePath) {
  const loader = new GLTFLoader();
  const buf = fs.readFileSync(filePath);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  return new Promise((resolve, reject) => loader.parse(ab, path.dirname(filePath) + "/", resolve, reject));
}

function retarget(clip, root) {
  const bones = new Map();
  root.traverse((obj) => {
    if (obj.name) bones.set(obj.name.replace(/[^a-z0-9]/gi, "").toLowerCase(), obj);
  });
  const tracks = [];
  for (const track of clip.tracks) {
    const dot = track.name.lastIndexOf(".");
    if (dot <= 0) continue;
    const key = track.name.slice(0, dot).replace(/[^a-z0-9]/gi, "").toLowerCase();
    if (track.name.endsWith(".scale") || track.name.endsWith(".position") || key.endsWith("hips")) continue;
    const bone = bones.get(key);
    if (!bone) continue;
    const prop = track.name.slice(dot + 1);
    if (prop !== "quaternion") continue;

    // Mixamo kit and Mixamo clips share the exact same local bone coordinate space for all non-hip bones.
    // Applying the clip quaternion directly preserves natural arms-down / running / kicking poses without T-posing.
    const next = track.clone();
    next.name = `${bone.name}.${prop}`;
    tracks.push(next);
  }
  return new THREE.AnimationClip(clip.name, clip.duration, tracks);
}

function png(width, height, rgba) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    const row = y * (width * 4 + 1);
    raw[row] = 0;
    Buffer.from(rgba.buffer, rgba.byteOffset + y * width * 4, width * 4).copy(raw, row + 1);
  }
  const idat = zlib.deflateSync(raw, { level: 9 });
  const chunk = (type, data) => {
    const out = Buffer.alloc(12 + data.length);
    out.writeUInt32BE(data.length, 0);
    out.write(type, 4, 4, "ascii");
    data.copy(out, 8);
    const crc = zlib.crc32(out.subarray(4, 8 + data.length));
    out.writeUInt32BE(crc >>> 0, 8 + data.length);
    return out;
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", ihdr),
    chunk("IDAT", idat),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

function skin(mesh) {
  mesh.skeleton.update();
  const pos = mesh.geometry.attributes.position;
  const out = new Float32Array(pos.count * 3);
  const target = new THREE.Vector3();
  for (let i = 0; i < pos.count; i += 1) {
    target.fromBufferAttribute(pos, i);
    mesh.applyBoneTransform(i, target);
    mesh.localToWorld(target);
    out[i * 3] = target.x;
    out[i * 3 + 1] = target.y;
    out[i * 3 + 2] = target.z;
  }
  return out;
}

function meshMaterialName(mesh) {
  const mat = Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
  return String(mat?.name || mesh.name || "").toUpperCase();
}

function partForMesh(matName, y) {
  if (matName.includes("HEAD")) return y > 1.56 ? PART.hair : PART.skin;
  if (matName.includes("TSHIRT") || matName.includes("SHIRT")) return PART.shirt;
  if (matName.includes("SHORT")) return PART.shorts;
  if (matName.includes("HAND")) return PART.skin;
  if (matName.includes("LEG")) {
    if (y > 0.44) return PART.skin;
    if (y > 0.13) return PART.socks;
    return PART.boots;
  }
  if (y > 1.56) return PART.hair;
  if (y > 1.40) return PART.skin;
  if (y > 0.90) return PART.shirt;
  if (y > 0.54) return PART.shorts;
  if (y > 0.13) return PART.socks;
  return PART.boots;
}

function classifyRestParts(restPoints, geometry, matName, restFit) {
  const index = geometry.index;
  const triCount = Math.floor(index.count / 3);
  const triParts = new Uint8Array(triCount);
  for (let ti = 0; ti < triCount; ti += 1) {
    const ia = index.getX(ti * 3);
    const ib = index.getX(ti * 3 + 1);
    const ic = index.getX(ti * 3 + 2);
    const midY = (((restPoints[ia * 3 + 1] + restPoints[ib * 3 + 1] + restPoints[ic * 3 + 1]) / 3) - restFit.ground) * restFit.scale;
    triParts[ti] = partForMesh(matName, midY);
  }
  return triParts;
}

// 3/4 elevated broadcast TV pitch angle (~20 deg downward look)
const TILT_RAD = (20 * Math.PI) / 180;
const COS_TILT = Math.cos(TILT_RAD);
const SIN_TILT = Math.sin(TILT_RAD);
const HALF_FRAME_W = 0.68;
const FRAME_TOP = 1.92;
const FRAME_H = 2.08;

function raster(points, geometry, triParts, zbuf, body, kit, parts, originX, originY, atlasW, yaw) {
  const index = geometry.index;
  const groups = geometry.groups.length ? geometry.groups : [{ start: 0, count: index.count, materialIndex: 0 }];
  const cos = Math.cos(yaw);
  const sin = Math.sin(yaw);

  const project = (i) => {
    const x = points[i * 3];
    const y = points[i * 3 + 1];
    const z = points[i * 3 + 2];
    const rx = x * cos - z * sin;
    const rz = x * sin + z * cos;
    const sy = y * COS_TILT + rz * SIN_TILT;
    const sz = rz * COS_TILT - y * SIN_TILT;
    return {
      x: ((rx + HALF_FRAME_W) / (HALF_FRAME_W * 2)) * (CELL - 1),
      y: ((FRAME_TOP - sy) / FRAME_H) * (CELL - 1),
      z: sz,
      rx,
      ry: y,
      rz,
    };
  };

  const paint = (ax, ay, az, shade, part) => {
    const x = ax | 0;
    const y = ay | 0;
    if (x < 0 || y < 0 || x >= CELL || y >= CELL) return;
    const slot = y * CELL + x;
    if (az >= zbuf[slot]) return;
    zbuf[slot] = az;
    const dst = ((originY + y) * atlasW + (originX + x)) * 4;
    const lit = Math.max(152, Math.min(252, Math.round(shade / 4) * 4));
    if (part === PART.shirt || part === PART.shorts || part === PART.socks) {
      body[dst] = lit;
      body[dst + 1] = lit;
      body[dst + 2] = lit;
      body[dst + 3] = 0;
      kit[dst] = lit;
      kit[dst + 1] = lit;
      kit[dst + 2] = lit;
      kit[dst + 3] = 255;
    } else {
      body[dst] = lit;
      body[dst + 1] = lit;
      body[dst + 2] = lit;
      body[dst + 3] = 255;
      kit[dst + 3] = 0;
    }
    const code = part * 32;
    parts[dst] = code;
    parts[dst + 1] = code;
    parts[dst + 2] = code;
    parts[dst + 3] = 255;
    painted += 1;
  };

  // Studio + stadium floodlight vector (upper front-left toward camera at -Z)
  const lx = -0.26;
  const ly = 0.72;
  const lz = -0.64;

  for (const group of groups) {
    for (let t = group.start; t < group.start + group.count; t += 3) {
      const ia = index.getX(t);
      const ib = index.getX(t + 1);
      const ic = index.getX(t + 2);
      const a = project(ia);
      const b = project(ib);
      const c = project(ic);
      const minX = Math.max(0, Math.floor(Math.min(a.x, b.x, c.x)));
      const maxX = Math.min(CELL - 1, Math.ceil(Math.max(a.x, b.x, c.x)));
      const minY = Math.max(0, Math.floor(Math.min(a.y, b.y, c.y)));
      const maxY = Math.min(CELL - 1, Math.ceil(Math.max(a.y, b.y, c.y)));
      const area = (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y);
      if (Math.abs(area) < 0.008) continue;

      // Compute true 3D triangle normal in camera-rotated space for sculpted lighting
      const e1x = b.rx - a.rx;
      const e1y = b.ry - a.ry;
      const e1z = b.rz - a.rz;
      const e2x = c.rx - a.rx;
      const e2y = c.ry - a.ry;
      const e2z = c.rz - a.rz;
      let nx = e1y * e2z - e1z * e2y;
      let ny = e1z * e2x - e1x * e2z;
      let nz = e1x * e2y - e1y * e2x;
      const nLen = Math.hypot(nx, ny, nz) || 1;
      nx /= nLen;
      ny /= nLen;
      nz /= nLen;
      // Orient normal toward camera (-Z) so double-sided faces light consistently
      if (nz > 0) {
        nx = -nx;
        ny = -ny;
        nz = -nz;
      }
      const ndotl = Math.max(0, nx * lx + ny * ly + nz * lz);
      const hemi = 0.5 + 0.5 * Math.max(-1, Math.min(1, ny));
      const shade = 168 + ndotl * 60 + hemi * 27;

      const part = triParts[(t / 3) | 0];
      for (let y = minY; y <= maxY; y += 1) {
        for (let x = minX; x <= maxX; x += 1) {
          const w0 = ((b.x - x) * (c.y - y) - (c.x - x) * (b.y - y)) / area;
          const w1 = ((c.x - x) * (a.y - y) - (a.x - x) * (c.y - y)) / area;
          const w2 = 1 - w0 - w1;
          if (w0 < 0 || w1 < 0 || w2 < 0) continue;
          paint(x, y, w0 * a.z + w1 * b.z + w2 * c.z, shade, part);
        }
      }
    }
  }
}

/** Add a crisp 1px dark silhouette outline around each cell so players pop cleanly against bright/dark turf. */
function addCellOutline(body, kit, parts, originX, originY, atlasW) {
  const occupied = new Uint8Array(CELL * CELL);
  for (let y = 0; y < CELL; y += 1) {
    for (let x = 0; x < CELL; x += 1) {
      const dst = ((originY + y) * atlasW + (originX + x)) * 4;
      if (body[dst + 3] > 20 || kit[dst + 3] > 20) occupied[y * CELL + x] = 1;
    }
  }
  for (let y = 1; y < CELL - 1; y += 1) {
    for (let x = 1; x < CELL - 1; x += 1) {
      if (occupied[y * CELL + x]) continue;
      const hasNeighbor =
        occupied[y * CELL + (x - 1)] ||
        occupied[y * CELL + (x + 1)] ||
        occupied[(y - 1) * CELL + x] ||
        occupied[(y + 1) * CELL + x];
      if (!hasNeighbor) continue;
      const dst = ((originY + y) * atlasW + (originX + x)) * 4;
      body[dst] = 14;
      body[dst + 1] = 22;
      body[dst + 2] = 20;
      body[dst + 3] = 210;
      kit[dst + 3] = 0;
      parts[dst] = 0;
      parts[dst + 1] = 0;
      parts[dst + 2] = 0;
      parts[dst + 3] = 255;
    }
  }
}

function footAnchor(clouds, yaw) {
  const cos = Math.cos(yaw);
  const sin = Math.sin(yaw);
  // Forward direction in rotated screen X is -sin(yaw), depth forward is cos(yaw)
  const fwdScreenX = -sin;
  const samples = [];
  for (const points of clouds) {
    for (let i = 0; i < points.length; i += 9) {
      const y = points[i + 1];
      const rx = points[i] * cos - points[i + 2] * sin;
      const rz = points[i] * sin + points[i + 2] * cos;
      samples.push({ x: rx, y, z: rz, lead: points[i + 2] });
    }
  }
  samples.sort((a, b) => a.y - b.y);
  const feet = samples.slice(0, Math.max(12, Math.floor(samples.length * 0.03)));
  let best = feet[0];
  for (const sample of feet) {
    if (sample.lead > best.lead) best = sample;
  }
  if (!best) return { x: 0.5, y: 0.08 };
  const nudgedX = best.x + fwdScreenX * 0.08;
  return {
    x: Math.max(0.08, Math.min(0.92, (nudgedX + HALF_FRAME_W) / (HALF_FRAME_W * 2))),
    y: Math.max(0, Math.min(1, best.y / FRAME_H)),
  };
}

const kit = await parseGltf(path.join(shell, "public/models/footballer/gtex_gt_mixamo_kit.glb"));
const clips = await parseGltf(path.join(shell, "public/models/footballer/gtex_mixamo_clips.glb"));
const clipByName = new Map(clips.animations.map((clip) => [clip.name, clip]));
kit.scene.traverse((obj) => {
  obj.frustumCulled = false;
});
kit.scene.updateMatrixWorld(true);

function measureCloud(points) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  for (let i = 0; i < points.length; i += 3) {
    minX = Math.min(minX, points[i]);
    maxX = Math.max(maxX, points[i]);
    minY = Math.min(minY, points[i + 1]);
    maxY = Math.max(maxY, points[i + 1]);
    minZ = Math.min(minZ, points[i + 2]);
    maxZ = Math.max(maxZ, points[i + 2]);
  }
  return { minX, maxX, minY, maxY, minZ, maxZ, height: maxY - minY };
}

function standOnPitch(points, fit) {
  const out = new Float32Array(points.length);
  for (let i = 0; i < points.length; i += 3) {
    out[i] = (points[i] - fit.midX) * fit.scale;
    out[i + 1] = (points[i + 1] - fit.ground) * fit.scale;
    out[i + 2] = (points[i + 2] - fit.midZ) * fit.scale;
  }
  return out;
}

const meshes = [];
kit.scene.traverse((obj) => {
  if (obj.isSkinnedMesh) meshes.push(obj);
});
if (!meshes.length) throw new Error("GT kit has no skinned mesh");
const mainMesh = meshes.reduce((best, mesh) =>
  mesh.geometry.attributes.position.count > best.geometry.attributes.position.count ? mesh : best
);
kit.scene.traverse((obj) => {
  if (obj.isBone) obj.userData.restQuaternion = obj.quaternion.clone();
});
const mixer = new THREE.AnimationMixer(kit.scene);
const columns = DIRECTIONS * FRAMES;
const rows = ACTIONS.length;
const atlasW = columns * CELL;
const atlasH = rows * CELL;
const body = new Uint8Array(atlasW * atlasH * 4);
const kitPx = new Uint8Array(atlasW * atlasH * 4);
const parts = new Uint8Array(atlasW * atlasH * 4);
const anchors = {};
let fit = null;
let painted = 0;

const meshMatNames = meshes.map((mesh) => meshMaterialName(mesh));
// Classify every triangle's anatomical part ONCE from the upright rest pose
// so boots, socks, knees, shorts, shirt, face, and hair stay anatomically locked in jumps, dives, and kicks.
const restSkinned = meshes.map((mesh) => skin(mesh));
const restCloud = measureCloud(restSkinned.flatMap((points) => Array.from(points)));
const restFit = {
  ground: restCloud.minY,
  midX: (restCloud.minX + restCloud.maxX) / 2,
  midZ: (restCloud.minZ + restCloud.maxZ) / 2,
  scale: 1.83 / Math.max(0.05, restCloud.height),
};
const meshTriParts = meshes.map((mesh, i) => classifyRestParts(restSkinned[i], mesh.geometry, meshMatNames[i], restFit));
const cellZbuf = new Float32Array(CELL * CELL);

function tiltPoseAll(meshClouds, rollRad, pitchRad) {
  if (Math.abs(rollRad) < 1e-4 && Math.abs(pitchRad) < 1e-4) return meshClouds;
  const cr = Math.cos(rollRad);
  const sr = Math.sin(rollRad);
  const cp = Math.cos(pitchRad);
  const sp = Math.sin(pitchRad);
  const pivotY = 0.85;
  let minY = Infinity;
  const rotated = meshClouds.map((points) => {
    const out = new Float32Array(points.length);
    for (let i = 0; i < points.length; i += 3) {
      const x = points[i];
      const y = points[i + 1] - pivotY;
      const z = points[i + 2];
      const y1 = y * cp - z * sp;
      const z1 = y * sp + z * cp;
      const x2 = x * cr - y1 * sr;
      const y2 = x * sr + y1 * cr + pivotY;
      out[i] = x2;
      out[i + 1] = y2;
      out[i + 2] = z1;
      if (y2 < minY) minY = y2;
    }
    return out;
  });
  const drop = Math.max(0, minY - 0.04);
  if (drop > 0) {
    for (const out of rotated) {
      for (let i = 1; i < out.length; i += 3) out[i] -= drop;
    }
  }
  return rotated;
}

for (let row = 0; row < ACTIONS.length; row += 1) {
  const action = ACTIONS[row];
  const source = clipByName.get(action.clip);
  if (!source) throw new Error(`Missing clip ${action.clip}`);
  kit.scene.traverse((obj) => {
    if (obj.isBone && obj.userData.restQuaternion) obj.quaternion.copy(obj.userData.restQuaternion);
  });
  kit.scene.updateMatrixWorld(true);
  const clip = retarget(source, kit.scene);
  mixer.stopAllAction();
  const play = mixer.clipAction(clip);
  play.setLoop(THREE.LoopOnce, 1);
  play.clampWhenFinished = true;
  play.play();
  anchors[action.id] = [];
  for (let frame = 0; frame < FRAMES; frame += 1) {
    mixer.setTime(((frame + 0.5) / FRAMES) * (clip.duration || 1));
    kit.scene.updateMatrixWorld(true);
    const skinned = meshes.map((mesh) => skin(mesh));
    const frameCloud = measureCloud(skinned.flatMap((points) => Array.from(points)));
    if (!fit) {
      fit = {
        ground: frameCloud.minY,
        midX: (frameCloud.minX + frameCloud.maxX) / 2,
        midZ: (frameCloud.minZ + frameCloud.maxZ) / 2,
        scale: 1.83 / Math.max(0.05, frameCloud.height),
      };
      console.log("\nfit", frameCloud.height.toFixed(3), fit.scale.toFixed(3));
      if (frameCloud.height < 1.2) throw new Error(`Posed body is folded (${frameCloud.height.toFixed(3)} m)`);
    }
    const groundOffset =
      action.id === "header"
        ? fit.ground
        : Math.min(fit.ground, frameCloud.minY) + (frameCloud.minY > fit.ground + 0.25 ? frameCloud.minY - fit.ground : 0);
    const frameFit = {
      ground: groundOffset,
      midX: (frameCloud.minX + frameCloud.maxX) / 2,
      midZ: (frameCloud.minZ + frameCloud.maxZ) / 2,
      scale: fit.scale,
    };
    const phase = Math.sin(((frame + 0.5) / FRAMES) * Math.PI);
    const rollRad = action.id === "dive" ? -0.78 * phase : 0;
    const pitchRad = action.id === "slide_tackle" ? -0.62 * phase : 0;
    const posed = tiltPoseAll(
      skinned.map((points) => standOnPitch(points, frameFit)),
      rollRad,
      pitchRad
    );
    const frameAnchors = [];
    for (let direction = 0; direction < DIRECTIONS; direction += 1) {
      const yaw = -Math.PI / 2 + (direction / DIRECTIONS) * Math.PI * 2;
      const originX = (direction * FRAMES + frame) * CELL;
      const originY = row * CELL;
      cellZbuf.fill(1e9);
      meshes.forEach((mesh, meshIndex) => {
        raster(posed[meshIndex], mesh.geometry, meshTriParts[meshIndex], cellZbuf, body, kitPx, parts, originX, originY, atlasW, yaw);
      });
      addCellOutline(body, kitPx, parts, originX, originY, atlasW);
      frameAnchors.push(footAnchor(posed, yaw));
    }
    anchors[action.id].push(frameAnchors);
    process.stdout.write(`\r${action.id} ${frame + 1}/${FRAMES}`);
  }
  process.stdout.write("\n");
}

if (painted < 20000) throw new Error(`Atlas is blank (${painted} pixels)`);
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "body.png"), png(atlasW, atlasH, body));
fs.writeFileSync(path.join(outDir, "kit.png"), png(atlasW, atlasH, kitPx));
fs.writeFileSync(path.join(outDir, "parts.png"), png(atlasW, atlasH, parts));
const manifest = {
  cell: CELL,
  directions: DIRECTIONS,
  frames: FRAMES,
  actions: ACTIONS.map((action) => action.id),
  anchors,
};
fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify(manifest));
console.log("atlas", atlasW, atlasH, "bytes", fs.statSync(path.join(outDir, "body.png")).size);
