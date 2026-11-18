/**
 * Copies the GT Mixamo kit into the public model folder and appends the
 * football takes that the baked Mixamo library does not already contain.
 * Raw FBX stays in the Unity art folder. Only the rebaked GLB is written here.
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import * as THREE from "three";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
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
  readAsDataURL(blob) {
    blob.arrayBuffer().then((ab) => {
      const b64 = Buffer.from(ab).toString("base64");
      this.result = `data:${blob.type || "application/octet-stream"};base64,${b64}`;
      if (this.onloadend) this.onloadend();
    });
  }
}
globalThis.FileReader = NodeFileReader;

const here = path.dirname(fileURLToPath(import.meta.url));
const shell = path.resolve(here, "..");
const repo = path.resolve(shell, "../..");
const outDir = path.join(shell, "public/models/footballer");
const kitOut = path.join(outDir, "gtex_gt_mixamo_kit.glb");
const clipsOut = path.join(outDir, "gtex_mixamo_clips.glb");
const contactOut = path.join(shell, "src/lib/3d/broadcast/clipContact.json");

const additions = [
  {
    name: "Gtex_Dribble_Run",
    file: "Gtex_Test_Migration/Assets/Arts/FootballPlayer/Animations/Locomotion/DribbleNew.fbx",
  },
  {
    name: "Gtex_Strike",
    file: "Gtex_Test_Migration/Assets/Arts/FootballPlayer/Animations/Actions/Strike Foward Jog.fbx",
  },
  {
    name: "Gtex_Standing_Tackle",
    file: "Gtex_Test_Migration/Assets/Arts/FootballPlayer/Animations/Actions/Tackling.fbx",
  },
  {
    name: "Gtex_Slump",
    file: "Gtex_Test_Migration/Assets/Arts/FootballPlayer/Animations/Actions/Tackled.fbx",
  },
];

function loadFbx(filePath) {
  const loader = new FBXLoader();
  const buf = fs.readFileSync(filePath);
  return loader.parse(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), path.dirname(filePath) + "/");
}

function prefixMixamo(clip, name) {
  const tracks = [];
  for (const track of clip.tracks) {
    const dot = track.name.lastIndexOf(".");
    if (dot <= 0) continue;
    const bone = track.name.slice(0, dot);
    const prop = track.name.slice(dot + 1);
    if (/hips$/i.test(bone) && prop.startsWith("position")) continue;
    const mixamo = bone.toLowerCase().startsWith("mixamorig") ? bone : `mixamorig${bone}`;
    const next = track.clone();
    next.name = `${mixamo}.${prop}`;
    tracks.push(next);
  }
  return new THREE.AnimationClip(name, clip.duration, tracks);
}

function parseGltf(filePath) {
  const loader = new GLTFLoader();
  const buf = fs.readFileSync(filePath);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  return new Promise((resolve, reject) => {
    loader.parse(ab, path.dirname(filePath) + "/", resolve, reject);
  });
}

function exportGlb(root) {
  const exporter = new GLTFExporter();
  return new Promise((resolve, reject) => {
    exporter.parse(root, resolve, reject, { binary: true, animations: root.animations });
  });
}

function findBone(root, suffix) {
  const needle = suffix.replace(/[^a-z0-9]/gi, "").toLowerCase();
  let found = null;
  root.traverse((obj) => {
    if (found || !obj.name) return;
    if (obj.name.replace(/[^a-z0-9]/gi, "").toLowerCase().endsWith(needle) && obj.name.replace(/[^a-z0-9]/gi, "").toLowerCase().includes("mixamorig")) {
      found = obj;
    }
  });
  return found;
}

function retargetOnto(clip, root) {
  const names = [];
  root.traverse((obj) => {
    if (obj.name) names.push(obj.name);
  });
  const resolved = new Map();
  for (const name of names) {
    resolved.set(name.replace(/[^a-z0-9]/gi, "").toLowerCase(), name);
  }
  const tracks = [];
  for (const track of clip.tracks) {
    const dot = track.name.lastIndexOf(".");
    if (dot <= 0) continue;
    const key = track.name.slice(0, dot).replace(/[^a-z0-9]/gi, "").toLowerCase();
    if (key.endsWith("hips") && track.name.endsWith("position")) continue;
    const bone = resolved.get(key);
    if (!bone) continue;
    const next = track.clone();
    next.name = `${bone}.${track.name.slice(dot + 1)}`;
    tracks.push(next);
  }
  return new THREE.AnimationClip(clip.name, clip.duration, tracks);
}

function contactPhase(clip, root) {
  const left = findBone(root, "LeftFoot");
  const right = findBone(root, "RightFoot");
  if (!left || !right) return 0.45;
  const mixer = new THREE.AnimationMixer(root);
  const action = mixer.clipAction(retargetOnto(clip, root));
  action.play();
  const vL = new THREE.Vector3();
  const vR = new THREE.Vector3();
  let bestT = 0.4;
  let best = -Infinity;
  const steps = 32;
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    mixer.setTime((clip.duration || 1) * t);
    root.updateMatrixWorld(true);
    left.getWorldPosition(vL);
    right.getWorldPosition(vR);
    const low = Math.min(vL.y, vR.y);
    const fwd = Math.max(vL.z, vR.z);
    const score = fwd * 2 - low;
    if (score > best) {
      best = score;
      bestT = t;
    }
  }
  mixer.stopAllAction();
  return Math.round(bestT * 100) / 100;
}

const zipDir = fs.mkdtempSync(path.join(os.tmpdir(), "gt-kit-"));
execSync(`tar -xf "C:/Users/ayomc/Desktop/GT/MIXAMO+RIG.zip" -C "${zipDir}"`);
fs.mkdirSync(outDir, { recursive: true });
fs.copyFileSync(path.join(zipDir, "MIXAMO RIG.glb"), kitOut);
console.log("kit", kitOut, fs.statSync(kitOut).size);

const clipsGltf = await parseGltf(clipsOut);
const library = [...(clipsGltf.animations || [])];
if (library.length < 60) {
  throw new Error(`Refusing to rebake a clip library that only has ${library.length} takes`);
}
const names = new Set(library.map((clip) => clip.name));
const fresh = [];
for (const addition of additions) {
  if (names.has(addition.name)) {
    console.log("already", addition.name);
    continue;
  }
  const fbx = loadFbx(path.join(repo, addition.file));
  const source = fbx.animations?.[0];
  if (!source) throw new Error(`No clip in ${addition.file}`);
  const clip = prefixMixamo(source, addition.name);
  library.push(clip);
  fresh.push(addition.name);
  console.log("added", addition.name, "duration", clip.duration.toFixed(2), "tracks", clip.tracks.length);
}

clipsGltf.scene.animations = library;
clipsGltf.animations = library;
if (fresh.length > 0) {
  const bin = await exportGlb(clipsGltf.scene);
  const nextPath = `${clipsOut}.next`;
  fs.writeFileSync(nextPath, Buffer.from(bin));
  const check = fs.readFileSync(nextPath);
  const checkJson = JSON.parse(check.slice(20, 20 + check.readUInt32LE(12)).toString("utf8"));
  if ((checkJson.animations || []).length < library.length) {
    fs.unlinkSync(nextPath);
    throw new Error(`Export kept ${(checkJson.animations || []).length} of ${library.length} clips`);
  }
  fs.renameSync(nextPath, clipsOut);
  console.log("clips", clipsOut, check.length, "anims", checkJson.animations.length);
}

const kit = await parseGltf(kitOut);
const measureNames = [
  "Forward_Jog_Dribbling_Soccer_Ball",
  "Gtex_Dribble_Run",
  "Soccer_Pass_From_Idle_Pose",
  "Jogging_And_Kicking_A_Soccerball_Forward",
  "Gtex_Strike",
  "Male_Soccer_Penalty_Kick",
  "Soccer_Slide_Tackle",
  "Gtex_Standing_Tackle",
  "Kicking_Up_A_Soccer_Ball",
  "Gtex_Slump",
  "Soccer_Chip_Shot_While_Jogging",
];
const byName = new Map((clipsGltf.animations || []).map((clip) => [clip.name, clip]));
const contact = {};
for (const name of measureNames) {
  const clip = byName.get(name);
  if (!clip) {
    console.log("missing for contact", name);
    continue;
  }
  contact[name] = contactPhase(clip, kit.scene);
  console.log("contact", name, contact[name]);
}
fs.writeFileSync(contactOut, JSON.stringify(contact, null, 2));
console.log("wrote", contactOut);
