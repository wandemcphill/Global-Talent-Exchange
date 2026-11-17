import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { disposeScene } from "@/lib/3d/disposeScene";
import { kitSwatchDataUri, type KitVariant } from "./clubIdentityDefaults";

type JerseyTurntableProps = {
  kit: KitVariant;
  crestDataUri?: string | null;
  chestText: string;
};

const KIT_MODEL_URL = "/models/footballer/gtex_home_kit_mixamo.glb?kit=1";

let kitTemplate: Promise<THREE.Group> | null = null;

function loadKitTemplate(): Promise<THREE.Group> {
  if (!kitTemplate) {
    kitTemplate = new Promise((resolve, reject) => {
      new GLTFLoader().load(
        KIT_MODEL_URL,
        (gltf) => resolve(gltf.scene),
        undefined,
        () => {
          kitTemplate = null;
          reject(new Error("kit model failed"));
        },
      );
    });
  }
  return kitTemplate;
}

function boneKey(name: string): string {
  return name.replace(/[^a-z0-9]/gi, "").toLowerCase();
}

function findBone(root: THREE.Object3D, suffix: string): THREE.Object3D | null {
  const needle = boneKey(suffix);
  let found: THREE.Object3D | null = null;
  root.traverse((obj) => {
    if (!found && obj.name && boneKey(obj.name) === needle) found = obj;
  });
  return found;
}

function hangSleeves(root: THREE.Object3D, style: string): void {
  const drop = style === "long" ? 1.05 : style === "raglan" ? 0.25 : 0.55;
  const left = findBone(root, "mixamorigLeftArm");
  const right = findBone(root, "mixamorigRightArm");
  if (left) left.rotateX(drop);
  if (right) right.rotateX(drop);
}

function patternCode(pattern: string): number {
  if (pattern === "stripes") return 1;
  if (pattern === "hoops") return 2;
  if (pattern === "sash") return 3;
  if (pattern === "chevron") return 4;
  if (pattern === "gradient") return 5;
  return 0;
}

function patternedCloth(primary: string, secondary: string, pattern: string, freq: THREE.Vector2): THREE.MeshStandardMaterial {
  const material = new THREE.MeshStandardMaterial({
    color: primary,
    roughness: 0.62,
    metalness: 0.02,
    side: THREE.DoubleSide,
  });
  const code = patternCode(pattern);
  material.defines = { USE_UV: "" };
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uSecondary = { value: new THREE.Color(secondary) };
    shader.uniforms.uPattern = { value: code };
    shader.uniforms.uFreq = { value: freq };
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform vec3 uSecondary;\nuniform float uPattern;\nuniform vec2 uFreq;",
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        vec3 alt = uSecondary;
        float stripe = step(0.5, fract(vUv.x * uFreq.x));
        float hoop = step(0.55, fract(vUv.y * uFreq.y));
        float sash = step(0.35, fract((vUv.x + vUv.y) * uFreq.x));
        float chev = step(0.5, fract(abs(vUv.x - 0.5) * uFreq.x + vUv.y * uFreq.y));
        vec3 base = diffuseColor.rgb;
        if (uPattern > 0.5 && uPattern < 1.5) diffuseColor.rgb = mix(base, alt, stripe);
        else if (uPattern > 1.5 && uPattern < 2.5) diffuseColor.rgb = mix(base, alt, hoop);
        else if (uPattern > 2.5 && uPattern < 3.5) diffuseColor.rgb = mix(base, alt, sash);
        else if (uPattern > 3.5 && uPattern < 4.5) diffuseColor.rgb = mix(base, alt, chev);
        else if (uPattern > 4.5 && uPattern < 5.5) {
          float fade = clamp(vUv.y, 0.0, 1.0);
          diffuseColor.rgb = mix(base, alt, fade);
        }`,
      );
  };
  material.customProgramCacheKey = () => `gtex-kit-${material.uuid}`;
  return material;
}

function chestPlate(text: string, ink: string): THREE.Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 160;
  const context = canvas.getContext("2d");
  if (context) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "rgba(15, 23, 42, 0.55)";
    context.fillRect(16, 28, canvas.width - 32, 104);
    context.fillStyle = ink;
    context.strokeStyle = "#111827";
    context.lineWidth = 10;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = `900 ${text.length > 12 ? 54 : text.length > 8 ? 68 : 78}px Arial`;
    context.strokeText(text, 256, 84);
    context.fillText(text, 256, 84);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const plate = new THREE.Mesh(
    new THREE.PlaneGeometry(0.46, 0.14),
    new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      depthWrite: false,
      depthTest: true,
      side: THREE.FrontSide,
      polygonOffset: true,
      polygonOffsetFactor: -4,
    }),
  );
  plate.frustumCulled = false;
  plate.name = "ChestText";
  return plate;
}

function partName(mesh: THREE.Mesh): string {
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  return materials.map((material) => material.name || "").join(" ").toLowerCase();
}

function isGarment(name: string): boolean {
  return name.includes("tshirt") || name.includes("shirt") || name.includes("short");
}

export function JerseyTurntable({ kit, crestDataUri, chestText }: JerseyTurntableProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const shirtRef = useRef<THREE.Group | null>(null);
  const draggingRef = useRef(false);
  const lastXRef = useRef(0);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    const width = mount.clientWidth || 420;
    const height = mount.clientHeight || 320;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(30, width / height, 0.1, 40);
    camera.position.set(0, 0.05, 4.2);
    camera.lookAt(0, -0.05, 0);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    } catch {
      setFallback(true);
      return;
    }
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const key = new THREE.DirectionalLight(0xffffff, 1.45);
    key.position.set(2.2, 3.4, 4.2);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xdbeafe, 0.55);
    rim.position.set(-3.2, 1.6, -2);
    scene.add(rim);

    const shirt = new THREE.Group();
    shirt.rotation.y = 0.28;
    shirtRef.current = shirt;
    scene.add(shirt);

    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    let frame = 0;
    const render = () => {
      if (!draggingRef.current && !reducedMotion && !mount.matches(":hover")) shirt.rotation.y += 0.003;
      if (typeof document === "undefined" || !document.hidden) renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    render();

    const onResize = () => {
      const nextWidth = mount.clientWidth || width;
      const nextHeight = mount.clientHeight || height;
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, nextHeight);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      shirtRef.current = null;
      disposeScene(scene, renderer);
    };
  }, []);

  useEffect(() => {
    const shirt = shirtRef.current;
    if (!shirt) return;
    let cancelled = false;
    const added: THREE.Object3D[] = [];

    loadKitTemplate()
      .then((template) => {
        if (cancelled || shirtRef.current !== shirt) return;
        const root = cloneSkinned(template);
        root.traverse((obj) => {
          const mesh = obj as THREE.SkinnedMesh;
          if (!mesh.isMesh) return;
          mesh.geometry = mesh.geometry.clone();
          mesh.visible = true;
          mesh.frustumCulled = false;
        });
        hangSleeves(root, kit.sleeve_style);
        root.rotation.y = -Math.PI / 2;
        root.updateMatrixWorld(true);
        const freq = new THREE.Vector2(7, 5);
        const shirtMaterial = patternedCloth(kit.primary_color, kit.secondary_color, kit.pattern_type, freq);
        const shortsMaterial = new THREE.MeshStandardMaterial({
          color: kit.shorts_color || kit.primary_color,
          roughness: 0.64,
          metalness: 0.02,
          side: THREE.DoubleSide,
        });
        root.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (!mesh.isMesh || !mesh.visible) return;
          const label = partName(mesh);
          if (label.includes("short")) mesh.material = shortsMaterial;
          else if (label.includes("tshirt") || label.includes("shirt")) mesh.material = shirtMaterial;
        });

        const fitted = new THREE.Box3().setFromObject(root);
        const fittedSize = fitted.getSize(new THREE.Vector3());
        const chestY = fitted.min.y + fittedSize.y * 0.62;
        const scale = 2.4 / Math.max(fittedSize.y, 0.01);
        root.scale.setScalar(scale);
        root.position.set(-fitted.getCenter(new THREE.Vector3()).x * scale, -chestY * scale, -fitted.getCenter(new THREE.Vector3()).z * scale);
        shirt.add(root);
        root.updateMatrixWorld(true);
        draggingRef.current = false;
        shirt.rotation.set(0, Math.PI - 1.15, 0);

        const chest = findBone(root, "mixamorigSpine2") || findBone(root, "mixamorigSpine1");
        if (chest) {
          const plate = chestPlate(chestText, "#F8FAFC");
          plate.scale.setScalar(0.78);
          plate.position.set(0, -0.02, 0.18);
          plate.rotation.set(0, 0, 0);
          plate.renderOrder = 2;
          chest.add(plate);

          if (crestDataUri) {
            const crestTexture = new THREE.TextureLoader().load(crestDataUri, (loaded) => {
              if (cancelled) loaded.dispose();
            });
            crestTexture.colorSpace = THREE.SRGBColorSpace;
            const crest = new THREE.Mesh(
              new THREE.PlaneGeometry(1, 1.15),
              new THREE.MeshBasicMaterial({
                map: crestTexture,
                transparent: true,
                depthWrite: false,
                depthTest: true,
                side: THREE.FrontSide,
                polygonOffset: true,
                polygonOffsetFactor: -4,
              }),
            );
            crest.frustumCulled = false;
            crest.scale.setScalar(0.16);
            crest.position.set(0.09, 0.1, 0.185);
            crest.rotation.set(0, 0, 0);
            crest.renderOrder = 2;
            chest.add(crest);
          }
        }

        added.push(root);
      })
      .catch(() => {
        if (!cancelled) setFallback(true);
      });

    return () => {
      cancelled = true;
      added.forEach((object) => {
        shirt.remove(object);
        object.traverse((child) => {
          const mesh = child as THREE.Mesh;
          if (!mesh.isMesh) return;
          mesh.geometry?.dispose();
          const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          materials.forEach((material) => {
            const mapped = material as THREE.MeshStandardMaterial;
            mapped.map?.dispose();
            material.dispose();
          });
        });
      });
    };
  }, [kit, crestDataUri, chestText]);

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    draggingRef.current = true;
    lastXRef.current = event.clientX;
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current || !shirtRef.current) return;
    const delta = event.clientX - lastXRef.current;
    lastXRef.current = event.clientX;
    shirtRef.current.rotation.y += delta * 0.012;
  };
  const onPointerUp = () => {
    draggingRef.current = false;
  };

  return (
    <div className="relative h-80 w-full overflow-hidden rounded border border-white/10 bg-slate-950/80">
      {fallback ? (
        <img src={kitSwatchDataUri(kit)} alt={`${kit.jersey_type} kit`} className="mx-auto h-full object-contain" />
      ) : (
        <div
          ref={mountRef}
          className="h-full w-full cursor-grab touch-none active:cursor-grabbing"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          aria-label="3D jersey preview"
          data-testid="jersey-turntable"
        />
      )}
    </div>
  );
}
