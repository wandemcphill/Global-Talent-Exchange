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

const PART = { shirt: 1, shorts: 2, socks: 3, skin: 4, hair: 5, boots: 6 };

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
    if (key.endsWith("hips") || track.name.endsWith(".scale") || track.name.endsWith(".position")) continue;
    const bone = bones.get(key);
    if (!bone) continue;
    const next = track.clone();
    const prop = track.name.slice(dot + 1);
    next.name = `${bone.name}.${prop}`;
    if (prop === "quaternion") {
      const source = new THREE.Quaternion(next.values[0], next.values[1], next.values[2], next.values[3]);
      if (source.lengthSq() > 0.5) {
        source.normalize();
        const inv = source.invert();
        const rest = (bone.userData.restQuaternion || bone.quaternion).clone();
        const keyframe = new THREE.Quaternion();
        const posed = new THREE.Quaternion();
        for (let i = 0; i < next.values.length; i += 4) {
          keyframe.set(next.values[i], next.values[i + 1], next.values[i + 2], next.values[i + 3]).normalize();
          posed.copy(rest).multiply(inv.clone().multiply(keyframe)).normalize();
          next.values[i] = posed.x;
          next.values[i + 1] = posed.y;
          next.values[i + 2] = posed.z;
          next.values[i + 3] = posed.w;
        }
      }
    }
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
  const idat = zlib.deflateSync(raw, { level: 6 });
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

function partFor(_materialIndex, y) {
  if (y > 1.58) return PART.hair;
  if (y > 1.42) return PART.skin;
  if (y > 0.92) return PART.shirt;
  if (y > 0.58) return PART.shorts;
  if (y > 0.16) return PART.socks;
  if (y > 0.02) return PART.boots;
  return PART.skin;
}

function raster(points, geometry, body, kit, parts, originX, originY, atlasW, yaw) {
  const index = geometry.index;
  const groups = geometry.groups.length ? geometry.groups : [{ start: 0, count: index.count, materialIndex: 0 }];
  const cos = Math.cos(yaw);
  const sin = Math.sin(yaw);
  const zbuf = new Float32Array(CELL * CELL);
  zbuf.fill(1e9);
  const project = (i) => {
    const x = points[i * 3];
    const y = points[i * 3 + 1];
    const z = points[i * 3 + 2];
    const rx = x * cos - z * sin;
    const rz = x * sin + z * cos;
    return {
      x: (rx + 0.85) / 1.7 * (CELL - 1),
      y: (1.95 - y) / 2.05 * (CELL - 1),
      z: rz,
      h: y,
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
    const lit = Math.max(70, Math.min(255, shade));
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
      if (Math.abs(area) < 0.01) continue;
      const shade = 150 + Math.min(90, Math.abs(area) * 0.15);
      const midY = (points[ia * 3 + 1] + points[ib * 3 + 1] + points[ic * 3 + 1]) / 3;
      const part = partFor(group.materialIndex || 0, midY);
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

function footAnchor(clouds, yaw) {
  const cos = Math.cos(yaw);
  const sin = Math.sin(yaw);
  const samples = [];
  for (const points of clouds) {
    for (let i = 0; i < points.length; i += 9) {
      const y = points[i + 1];
      const rx = points[i] * cos - points[i + 2] * sin;
      samples.push({ x: rx, y });
    }
  }
  samples.sort((a, b) => a.y - b.y);
  const feet = samples.slice(0, Math.max(12, Math.floor(samples.length * 0.03)));
  let best = feet[0];
  for (const sample of feet) if (sample.x > best.x) best = sample;
  if (!best) return { x: 0.5, y: 0.08 };
  return {
    x: Math.max(0, Math.min(1, (best.x + 0.85) / 1.7)),
    y: Math.max(0, Math.min(1, best.y / 2.05)),
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
    if (!fit) {
      const cloud = measureCloud(skinned.flatMap((points) => Array.from(points)));
      fit = {
        ground: cloud.minY,
        midX: (cloud.minX + cloud.maxX) / 2,
        midZ: (cloud.minZ + cloud.maxZ) / 2,
        scale: 1.83 / Math.max(0.05, cloud.height),
      };
      console.log("\nfit", cloud.height.toFixed(3), fit.scale.toFixed(3));
      if (cloud.height < 1.2) throw new Error(`Posed body is folded (${cloud.height.toFixed(3)} m)`);
    }
    const posed = skinned.map((points) => standOnPitch(points, fit));
    const frameAnchors = [];
    for (let direction = 0; direction < DIRECTIONS; direction += 1) {
      const yaw = -Math.PI / 2 + (direction / DIRECTIONS) * Math.PI * 2;
      const originX = (direction * FRAMES + frame) * CELL;
      const originY = row * CELL;
      meshes.forEach((mesh, meshIndex) => {
        raster(posed[meshIndex], mesh.geometry, body, kitPx, parts, originX, originY, atlasW, yaw);
      });
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
