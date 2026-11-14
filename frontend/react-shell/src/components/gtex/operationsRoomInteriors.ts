import * as THREE from "three";
import type { OperationsHubDestination } from "@/lib/ownerBriefing";

export interface DepartmentInteriorBuild {
  group: THREE.Group;
  pickables: THREE.Object3D[];
  animatedActors: THREE.Group[];
}

type Hotspot = OperationsHubDestination["hotspots"][number];

const ROOM_WIDTH = 10.5;
const ROOM_DEPTH = 8.5;
const WALL_HEIGHT = 4.25;

function accentCssColor(accent: THREE.ColorRepresentation): string {
  return typeof accent === "string" ? accent : `#${new THREE.Color(accent).getHexString()}`;
}

function standardMaterial(
  color: THREE.ColorRepresentation,
  roughness = 0.68,
  metalness = 0.08,
): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness });
}

function addBox(
  root: THREE.Group,
  size: [number, number, number],
  position: [number, number, number],
  material: THREE.Material,
  rotationY = 0,
): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
  mesh.position.set(...position);
  mesh.rotation.y = rotationY;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  root.add(mesh);
  return mesh;
}

function addCylinder(
  root: THREE.Group,
  radiusTop: number,
  radiusBottom: number,
  height: number,
  position: [number, number, number],
  material: THREE.Material,
  radialSegments = 20,
): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(radiusTop, radiusBottom, height, radialSegments),
    material,
  );
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  root.add(mesh);
  return mesh;
}

function addCanvasDisplay(title: string, subtitle: string, accent: string): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 768;
  canvas.height = 384;
  const ctx = canvas.getContext("2d");
  if (!ctx) return new THREE.CanvasTexture(canvas);
  ctx.fillStyle = "#07111f";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = accent;
  ctx.fillRect(0, 0, 12, canvas.height);
  ctx.fillStyle = "#91a9c4";
  ctx.font = "600 24px Arial, sans-serif";
  ctx.fillText("GTEX  /  CLUB OPERATIONS", 44, 58);
  ctx.fillStyle = "#f8fafc";
  ctx.font = "700 46px Arial, sans-serif";
  ctx.fillText(title.slice(0, 25).toUpperCase(), 44, 154);
  ctx.fillStyle = "#b6c5d8";
  ctx.font = "24px Arial, sans-serif";
  ctx.fillText(subtitle.slice(0, 42), 44, 206);
  ctx.fillStyle = accent;
  ctx.fillRect(44, 258, 180, 7);
  ctx.fillStyle = "#64748b";
  ctx.font = "18px Arial, sans-serif";
  ctx.fillText("LIVE CLUB DATA  •  AUTHORITATIVE SYSTEM", 44, 320);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

function addStaffActor(
  root: THREE.Group,
  position: [number, number, number],
  palette: { jacket: number; shirt: number; tie: number; skin: number; hair: number },
  phase: number,
): THREE.Group {
  const actor = new THREE.Group();
  actor.name = "department-staff-actor";
  actor.position.set(...position);
  actor.userData = { idlePhase: phase, baseY: position[1] };

  const jacket = standardMaterial(palette.jacket, 0.48, 0.12);
  const shirt = standardMaterial(palette.shirt, 0.82, 0.02);
  const tie = standardMaterial(palette.tie, 0.42, 0.18);
  const skin = standardMaterial(palette.skin, 0.88, 0.01);
  const hair = standardMaterial(palette.hair, 0.92, 0.01);
  const trousers = standardMaterial(0x172335, 0.72, 0.04);
  const shoes = standardMaterial(0x080d16, 0.34, 0.16);

  // A clean, stylised club-staff figure built from low-poly forms; no external
  // character asset or texture dependency is required.
  addCylinder(actor, 0.29, 0.38, 0.82, [0, 1.22, 0], jacket, 12);
  addCylinder(actor, 0.12, 0.12, 0.16, [0, 1.72, 0], skin, 12);
  const head = new THREE.Group();
  head.position.set(0, 1.96, 0);
  const face = new THREE.Mesh(new THREE.SphereGeometry(0.19, 12, 10), skin);
  face.position.y = 0.02;
  face.castShadow = true;
  head.add(face);
  const hairCap = new THREE.Mesh(new THREE.SphereGeometry(0.195, 12, 8), hair);
  hairCap.scale.set(1.02, 0.58, 1.02);
  hairCap.position.set(0, 0.13, -0.015);
  head.add(hairCap);
  actor.add(head);

  addBox(actor, [0.14, 0.46, 0.035], [0, 1.28, 0.345], shirt);
  addBox(actor, [0.07, 0.42, 0.045], [0, 1.27, 0.37], tie);
  const leftArm = new THREE.Group();
  leftArm.position.set(-0.34, 1.52, 0);
  addCylinder(leftArm, 0.105, 0.13, 0.56, [0, -0.29, 0], jacket, 10);
  addCylinder(leftArm, 0.075, 0.085, 0.22, [0, -0.65, 0], skin, 10);
  actor.add(leftArm);
  const rightArm = new THREE.Group();
  rightArm.position.set(0.34, 1.52, 0);
  addCylinder(rightArm, 0.105, 0.13, 0.56, [0, -0.29, 0], jacket, 10);
  addCylinder(rightArm, 0.075, 0.085, 0.22, [0, -0.65, 0], skin, 10);
  actor.add(rightArm);

  [-0.15, 0.15].forEach((x) => {
    addCylinder(actor, 0.105, 0.13, 0.72, [x, 0.42, 0], trousers, 10);
    addBox(actor, [0.22, 0.12, 0.38], [x, 0.08, 0.055], shoes);
  });

  actor.userData.leftArmPivot = leftArm;
  actor.userData.rightArmPivot = rightArm;
  actor.userData.headPivot = head;
  root.add(actor);
  return actor;
}

function addDepartmentScreen(
  root: THREE.Group,
  title: string,
  subtitle: string,
  accent: string,
  position: [number, number, number],
  size: [number, number],
  rotationY = 0,
): THREE.Mesh {
  const texture = addCanvasDisplay(title, subtitle, accent);
  const screen = new THREE.Mesh(
    new THREE.PlaneGeometry(size[0], size[1]),
    new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide }),
  );
  screen.position.set(...position);
  screen.rotation.y = rotationY;
  root.add(screen);
  return screen;
}

function addRoomShell(
  root: THREE.Group,
  accent: THREE.ColorRepresentation,
  departmentLabel: string,
  departmentSubtitle: string,
): void {
  const floor = addBox(
    root,
    [ROOM_WIDTH, 0.24, ROOM_DEPTH],
    [0, -0.12, 0],
    standardMaterial(0x172335, 0.42, 0.3),
  );
  floor.receiveShadow = true;

  const back = addBox(
    root,
    [ROOM_WIDTH, WALL_HEIGHT, 0.18],
    [0, WALL_HEIGHT / 2, -ROOM_DEPTH / 2],
    standardMaterial(0x101b2b, 0.82, 0.08),
  );
  back.receiveShadow = true;

  // Side walls stop short of the front edge, leaving the room readable as a cutaway.
  addBox(root, [0.18, WALL_HEIGHT, ROOM_DEPTH], [-ROOM_WIDTH / 2, WALL_HEIGHT / 2, 0], standardMaterial(0x122034));
  addBox(root, [0.18, WALL_HEIGHT, ROOM_DEPTH], [ROOM_WIDTH / 2, WALL_HEIGHT / 2, 0], standardMaterial(0x122034));

  // Architectural frame, ceiling ribs and restrained accent lighting.
  const accentMat = new THREE.MeshStandardMaterial({
    color: accent,
    emissive: accent,
    emissiveIntensity: 0.24,
    metalness: 0.32,
    roughness: 0.4,
  });
  addBox(root, [ROOM_WIDTH, 0.12, 0.16], [0, WALL_HEIGHT, -ROOM_DEPTH / 2 + 0.12], accentMat);
  addBox(root, [0.12, WALL_HEIGHT, 0.16], [-ROOM_WIDTH / 2 + 0.12, WALL_HEIGHT / 2, -ROOM_DEPTH / 2 + 0.12], accentMat);
  addBox(root, [0.12, WALL_HEIGHT, 0.16], [ROOM_WIDTH / 2 - 0.12, WALL_HEIGHT / 2, -ROOM_DEPTH / 2 + 0.12], accentMat);

  const trim = new THREE.Mesh(
    new THREE.BoxGeometry(ROOM_WIDTH - 0.6, 0.035, 0.035),
    new THREE.MeshBasicMaterial({ color: accent }),
  );
  trim.position.set(0, 0.06, ROOM_DEPTH / 2 - 0.18);
  root.add(trim);

  addDepartmentScreen(
    root,
    departmentLabel,
    departmentSubtitle,
    accentCssColor(accent),
    [0, 3.55, -ROOM_DEPTH / 2 + 0.115],
    [3.4, 0.92],
  );
  const ceilingLight = new THREE.PointLight(accent, 1.8, 18);
  ceilingLight.position.set(0, 3.85, -0.2);
  root.add(ceilingLight);
}

function addChair(root: THREE.Group, x: number, z: number, accent: THREE.ColorRepresentation, rotation = 0): void {
  const dark = standardMaterial(0x17253a, 0.35, 0.35);
  const seat = addBox(root, [0.82, 0.18, 0.78], [x, 0.65, z], dark, rotation);
  addBox(root, [0.82, 0.92, 0.16], [x, 1.14, z - 0.28], dark, rotation);
  addCylinder(root, 0.07, 0.07, 0.52, [x, 0.31, z], dark, 10);
  addBox(root, [0.68, 0.06, 0.06], [x, 0.16, z], standardMaterial(accent), rotation);
  seat.userData = { furniture: "chair" };
}

function addTerminal(
  root: THREE.Group,
  destination: OperationsHubDestination,
  hotspot: Hotspot,
  pickables: THREE.Object3D[],
): void {
  const [x, hotspotY, z] = hotspot.offset;
  const accent = destination.accent_color || "#38bdf8";
  const bodyMat = standardMaterial(0x24344a, 0.34, 0.48);
  const base = addBox(root, [0.88, 0.92, 0.68], [x, 0.56, z], bodyMat);
  const top = addBox(root, [1.08, 0.08, 0.78], [x, 1.06, z], standardMaterial(0x0b1422, 0.28, 0.56));
  const stem = addBox(root, [0.12, 0.34, 0.12], [x, 1.27, z - 0.22], standardMaterial(0x64748b, 0.3, 0.72));
  const screenTexture = addCanvasDisplay(hotspot.label, "Action: " + hotspot.action.replace(/_/g, " "), accent);
  const screen = new THREE.Mesh(
    new THREE.PlaneGeometry(0.92, 0.52),
    new THREE.MeshBasicMaterial({ map: screenTexture, side: THREE.DoubleSide }),
  );
  screen.position.set(x, Math.max(1.55, hotspotY + 0.18), z + 0.03);
  screen.rotation.y = 0;
  root.add(screen);

  const actionData = {
    destinationKey: destination.destination_key,
    hotspotId: hotspot.id,
    hotspotLabel: hotspot.label,
    hotspotAction: hotspot.action,
  };
  [base, top, stem, screen].forEach((object) => {
    object.userData = { ...object.userData, ...actionData };
  });
  pickables.push(base, top, screen);
}

function addExecutiveBoardroom(root: THREE.Group): void {
  const wood = standardMaterial(0x493723, 0.3, 0.28);
  addBox(root, [4.5, 0.22, 1.8], [0, 0.98, -1.95], wood);
  addBox(root, [0.22, 0.9, 0.22], [-1.8, 0.43, -1.95], standardMaterial(0x273449, 0.3, 0.6));
  addBox(root, [0.22, 0.9, 0.22], [1.8, 0.43, -1.95], standardMaterial(0x273449, 0.3, 0.6));
  [-3.0, -1.0, 1.0, 3.0].forEach((x) => {
    addChair(root, x, -0.65, 0xd6b56d, Math.PI);
    addChair(root, x, -3.15, 0xd6b56d, 0);
  });
  addBox(root, [3.2, 0.045, 0.025], [0, 1.13, -1.95], standardMaterial(0xd6b56d, 0.25, 0.7));
  addBox(root, [1.7, 0.08, 0.6], [0, 1.14, -1.95], standardMaterial(0x0d2235, 0.25, 0.2));
  addBox(root, [2.4, 1.45, 0.12], [0, 1.82, -4.02], standardMaterial(0x0d1a2b, 0.28, 0.32));
  addDepartmentScreen(root, "Boardroom", "Strategy, governance and owner decisions", "#d6b56d", [0, 1.88, -3.94], [2.1, 0.96]);
  addCylinder(root, 0.62, 0.62, 0.14, [-4.1, 0.08, -3.2], standardMaterial(0x162c3d, 0.3, 0.35));
  addCylinder(root, 0.48, 0.48, 0.28, [-4.1, 0.27, -3.2], standardMaterial(0x2c4b58, 0.25, 0.42));
  addBox(root, [1.0, 1.2, 0.5], [4.1, 0.6, -3.1], standardMaterial(0x202f40, 0.58, 0.18));
}

function addManagerTechnicalRoom(root: THREE.Group): void {
  const turf = standardMaterial(0x174c3d, 0.85, 0.02);
  addBox(root, [5.2, 0.08, 3.4], [0, 0.06, -2.25], turf);
  const line = new THREE.Mesh(
    new THREE.PlaneGeometry(4.8, 3.0),
    new THREE.MeshBasicMaterial({ color: 0xd6f7e8, transparent: true, opacity: 0.55, side: THREE.DoubleSide }),
  );
  line.rotation.x = -Math.PI / 2;
  line.position.set(0, 0.112, -2.25);
  root.add(line);
  const pitchMark = new THREE.Mesh(
    new THREE.RingGeometry(0.48, 0.52, 32),
    new THREE.MeshBasicMaterial({ color: 0xe4f8ec, side: THREE.DoubleSide }),
  );
  pitchMark.rotation.x = -Math.PI / 2;
  pitchMark.position.set(0, 0.12, -2.25);
  root.add(pitchMark);
  addBox(root, [3.8, 1.5, 0.16], [0, 1.9, -4.02], standardMaterial(0x0c1727, 0.22, 0.52));
  addDepartmentScreen(root, "Tactical Theatre", "Formation, match preparation and squad decisions", "#38bdf8", [0, 1.9, -3.92], [3.3, 1.15]);
  for (let i = 0; i < 5; i += 1) {
    addBox(root, [0.74, 0.16, 0.46], [-4.15 + i * 0.92, 0.16, 3.55], standardMaterial(0x26384e, 0.42, 0.24));
    addBox(root, [0.74, 1.1, 0.08], [-4.15 + i * 0.92, 0.76, 3.73], standardMaterial(0x1c2c40, 0.52, 0.2));
  }
  addBox(root, [2.3, 0.72, 1.0], [0, 0.52, -0.05], standardMaterial(0x182a40, 0.28, 0.48));
  addBox(root, [2.1, 0.025, 0.8], [0, 0.9, -0.05], standardMaterial(0x0d6b58, 0.4, 0.15));
  [-1.3, 1.3].forEach((x) => addChair(root, x, 0.25, 0x38bdf8));
}

function addGeneralManagerSuite(root: THREE.Group): void {
  const wood = standardMaterial(0x5a4635, 0.34, 0.18);
  addBox(root, [2.9, 0.18, 1.45], [0, 0.93, -1.7], wood);
  addBox(root, [0.16, 0.78, 0.16], [-1.15, 0.42, -1.2], standardMaterial(0x29384a, 0.36, 0.46));
  addBox(root, [0.16, 0.78, 0.16], [1.15, 0.42, -1.2], standardMaterial(0x29384a, 0.36, 0.46));
  addChair(root, 0, 0.0, 0xa78bfa, Math.PI);
  [-3.9, -3.0, -2.1].forEach((z, index) => {
    addBox(root, [1.1, 0.16, 0.72], [4.0, 0.36 + index * 0.62, z], standardMaterial(0x26384a, 0.52, 0.14));
    addBox(root, [0.95, 0.05, 0.55], [4.0, 0.47 + index * 0.62, z], standardMaterial(0x394d61, 0.65, 0.08));
  });
  addBox(root, [3.0, 1.5, 0.15], [0, 1.85, -4.02], standardMaterial(0x141d32, 0.32, 0.38));
  addDepartmentScreen(root, "Administration", "Delegation, staffing and campus masterplan", "#a78bfa", [0, 1.85, -3.92], [2.7, 1.1]);
  addBox(root, [1.0, 0.05, 0.65], [-3.9, 0.12, -3.4], standardMaterial(0x34485e, 0.52, 0.12));
}

function addAcademyDevelopmentLab(root: THREE.Group): void {
  addBox(root, [5.2, 0.08, 3.3], [0, 0.05, -2.25], standardMaterial(0x23513a, 0.94, 0.01));
  const markings = new THREE.Group();
  const markMat = new THREE.MeshBasicMaterial({ color: 0xd9f4e3, transparent: true, opacity: 0.75 });
  const centerLine = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.012, 3.0), markMat);
  centerLine.position.set(0, 0.11, -2.25);
  markings.add(centerLine);
  const circle = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.46, 32), markMat);
  circle.rotation.x = -Math.PI / 2;
  circle.position.set(0, 0.12, -2.25);
  markings.add(circle);
  root.add(markings);
  addBox(root, [1.3, 0.9, 0.15], [0, 0.56, -3.95], standardMaterial(0xe2e8f0, 0.58, 0.04));
  addBox(root, [0.08, 1.0, 0.08], [-0.61, 0.54, -3.95], standardMaterial(0xe2e8f0));
  addBox(root, [0.08, 1.0, 0.08], [0.61, 0.54, -3.95], standardMaterial(0xe2e8f0));
  addBox(root, [1.3, 0.08, 0.08], [0, 1.02, -3.95], standardMaterial(0xe2e8f0));
  [-3.5, -2.3, 2.3, 3.5].forEach((x, index) => {
    addCylinder(root, 0.12, 0.15, 0.42, [x, 0.3, 0.25 + (index % 2) * 0.55], standardMaterial(index % 2 ? 0xf59e0b : 0x38bdf8), 12);
  });
  addBox(root, [2.4, 1.15, 0.22], [3.9, 0.78, -3.5], standardMaterial(0x172b3f, 0.34, 0.42));
  addDepartmentScreen(root, "Player Development", "Youth intake, progression and scholar contracts", "#f59e0b", [3.9, 1.2, -3.36], [2.05, 0.9]);
  addBox(root, [1.8, 0.8, 0.9], [-3.7, 0.5, -3.3], standardMaterial(0x273a4b, 0.5, 0.1));
}

function addMedicalRehabilitationSuite(root: THREE.Group): void {
  const tile = standardMaterial(0x1a3543, 0.28, 0.36);
  addBox(root, [4.2, 0.11, 1.55], [-2.55, 0.05, -2.2], tile);
  [ -3.55, -2.35, -1.15 ].forEach((x, index) => {
    addBox(root, [0.92, 0.36, 1.12], [x, 0.34, -2.25], standardMaterial(0x607d8b, 0.25, 0.34));
    addBox(root, [0.82, 0.08, 1.02], [x, 0.57, -2.25], standardMaterial(0x8ad4df, 0.18, 0.2));
    addBox(root, [0.9, 0.06, 0.08], [x, 0.64, -2.75], standardMaterial(0xd5f5f4, 0.22, 0.06));
  });
  [1.4, 3.1].forEach((x, index) => {
    addBox(root, [1.3, 0.22, 2.1], [x, 0.56, -1.8], standardMaterial(0xd8e2e9, 0.44, 0.05));
    addBox(root, [1.3, 0.6, 0.14], [x, 0.96, -2.7], standardMaterial(0x637c91, 0.48, 0.06));
    addCylinder(root, 0.045, 0.045, 0.75, [x - 0.48, 0.26, -1.05], standardMaterial(0x526a7d), 10);
    addCylinder(root, 0.045, 0.045, 0.75, [x + 0.48, 0.26, -1.05], standardMaterial(0x526a7d), 10);
  });
  addBox(root, [3.8, 1.45, 0.16], [0, 1.9, -4.02], standardMaterial(0x10283a, 0.3, 0.42));
  addDepartmentScreen(root, "Sports Medicine", "Rehabilitation, player strain and recovery protocols", "#ec4899", [0, 1.9, -3.92], [3.2, 1.1]);
  addBox(root, [0.12, 2.2, 0.12], [-0.4, 1.1, 2.9], standardMaterial(0x64748b, 0.3, 0.65));
  addBox(root, [0.12, 2.2, 0.12], [0.4, 1.1, 2.9], standardMaterial(0x64748b, 0.3, 0.65));
  addBox(root, [0.92, 0.08, 0.08], [0, 2.08, 2.9], standardMaterial(0x94a3b8, 0.3, 0.6));
}

function addFinanceCommercialSuite(root: THREE.Group): void {
  const stone = standardMaterial(0x24364a, 0.28, 0.44);
  addBox(root, [3.8, 0.2, 1.55], [0, 0.92, -1.75], stone);
  addBox(root, [0.18, 0.8, 0.18], [-1.5, 0.42, -1.25], standardMaterial(0x16273a, 0.3, 0.5));
  addBox(root, [0.18, 0.8, 0.18], [1.5, 0.42, -1.25], standardMaterial(0x16273a, 0.3, 0.5));
  [-2.2, 2.2].forEach((x) => addChair(root, x, 0.1, 0x22d3ee, Math.PI));
  // A secure records vault and commercial partner wall make this room visually distinct.
  addBox(root, [1.9, 2.6, 0.75], [-3.8, 1.3, -3.45], standardMaterial(0x34495c, 0.25, 0.72));
  addCylinder(root, 0.42, 0.42, 0.12, [-3.8, 1.3, -3.04], standardMaterial(0x91a4b8, 0.22, 0.82), 32);
  addCylinder(root, 0.12, 0.12, 0.16, [-3.8, 1.3, -2.96], standardMaterial(0x0b1726, 0.22, 0.78), 20);
  addBox(root, [2.5, 1.75, 0.14], [3.75, 1.7, -3.6], standardMaterial(0x0e2032, 0.28, 0.5));
  addDepartmentScreen(root, "Commercial Partners", "Sponsorship inventory, gate receipts and broadcast revenue", "#22d3ee", [3.75, 1.8, -3.48], [2.2, 1.15]);
  addBox(root, [0.9, 1.0, 0.75], [0, 0.5, 2.9], standardMaterial(0x1a2d42, 0.36, 0.46));
  addBox(root, [0.98, 0.55, 0.06], [0, 1.3, 2.48], standardMaterial(0x123b4a, 0.24, 0.58));
}

export function buildDepartmentInterior(destination: OperationsHubDestination): DepartmentInteriorBuild {
  const group = new THREE.Group();
  group.name = "department-interior-" + destination.destination_key;
  group.userData = { destinationKey: destination.destination_key, departmentInterior: true };
  const pickables: THREE.Object3D[] = [];
  const animatedActors: THREE.Group[] = [];
  const accent = destination.accent_color || "#38bdf8";

  addRoomShell(group, accent, destination.label, destination.subtitle);

  switch (destination.destination_key) {
    case "executive_office":
      addExecutiveBoardroom(group);
      animatedActors.push(addStaffActor(group, [-4.05, 0, 0.55], {
        jacket: 0x1e293b, shirt: 0xf8fafc, tie: 0xd6b56d, skin: 0x9a6548, hair: 0x20202a,
      }, 0.2));
      break;
    case "managers_office":
      addManagerTechnicalRoom(group);
      animatedActors.push(addStaffActor(group, [4.0, 0, 1.5], {
        jacket: 0x153c63, shirt: 0xe8f1fa, tie: 0x38bdf8, skin: 0x86583f, hair: 0x161c25,
      }, 1.1));
      break;
    case "general_managers_office":
      addGeneralManagerSuite(group);
      animatedActors.push(addStaffActor(group, [-4.0, 0, 1.45], {
        jacket: 0x3a315a, shirt: 0xf5f3ff, tie: 0xa78bfa, skin: 0x70452f, hair: 0x191820,
      }, 2.0));
      break;
    case "academy_department":
      addAcademyDevelopmentLab(group);
      animatedActors.push(addStaffActor(group, [-4.05, 0, 1.5], {
        jacket: 0x24533f, shirt: 0xf0fdf4, tie: 0xf59e0b, skin: 0x986447, hair: 0x211d18,
      }, 2.8));
      break;
    case "medical_department":
      addMedicalRehabilitationSuite(group);
      animatedActors.push(addStaffActor(group, [4.0, 0, 1.45], {
        jacket: 0x17616a, shirt: 0xf0fdfa, tie: 0xec4899, skin: 0x8d5e45, hair: 0x25212a,
      }, 3.6));
      break;
    case "finance_commercial_office":
      addFinanceCommercialSuite(group);
      animatedActors.push(addStaffActor(group, [4.05, 0, 0.8], {
        jacket: 0x26394c, shirt: 0xf8fafc, tie: 0x22d3ee, skin: 0x9b694c, hair: 0x20242c,
      }, 4.4));
      break;
  }

  (destination.hotspots || []).forEach((hotspot) => addTerminal(group, destination, hotspot, pickables));
  return { group, pickables, animatedActors };
}
