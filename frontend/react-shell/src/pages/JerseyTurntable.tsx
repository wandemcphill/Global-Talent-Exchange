import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import * as THREE from "three";
import { disposeScene } from "@/lib/3d/disposeScene";
import { kitSwatchDataUri, type KitVariant } from "./clubIdentityDefaults";

type JerseyTurntableProps = {
  kit: KitVariant;
  crestDataUri?: string | null;
  chestText: string;
};

function disposeObject(object: THREE.Object3D): void {
  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;
    child.geometry.dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.forEach((material) => {
      const mapped = material as THREE.MeshStandardMaterial;
      mapped.map?.dispose();
      material.dispose();
    });
  });
}

function paintShirtCanvas(kit: KitVariant, chestText: string): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 640;
  const context = canvas.getContext("2d");
  if (!context) return canvas;
  context.fillStyle = kit.primary_color;
  context.fillRect(0, 0, canvas.width, canvas.height);

  context.save();
  context.globalAlpha = 0.9;
  context.fillStyle = kit.secondary_color;
  if (kit.pattern_type === "stripes") {
    for (let x = 36; x < canvas.width; x += 72) {
      context.fillRect(x, 0, 28, canvas.height);
    }
  } else if (kit.pattern_type === "hoops") {
    for (let y = 150; y < canvas.height - 40; y += 78) {
      context.fillRect(0, y, canvas.width, 28);
    }
  } else if (kit.pattern_type === "sash") {
    context.beginPath();
    context.moveTo(0, 80);
    context.lineTo(150, 0);
    context.lineTo(250, 0);
    context.lineTo(0, 210);
    context.closePath();
    context.fill();
  } else if (kit.pattern_type === "chevron") {
    context.beginPath();
    context.moveTo(40, 210);
    context.lineTo(256, 300);
    context.lineTo(472, 210);
    context.lineTo(472, 250);
    context.lineTo(256, 340);
    context.lineTo(40, 250);
    context.closePath();
    context.fill();
  } else if (kit.pattern_type === "gradient") {
    const fade = context.createLinearGradient(0, 0, 0, canvas.height);
    fade.addColorStop(0, "rgba(255,255,255,0.05)");
    fade.addColorStop(1, kit.secondary_color);
    context.fillStyle = fade;
    context.fillRect(0, 0, canvas.width, canvas.height);
  }
  context.restore();

  const shade = context.createLinearGradient(0, 0, canvas.width, canvas.height);
  shade.addColorStop(0, "rgba(255,255,255,0.22)");
  shade.addColorStop(0.45, "rgba(0,0,0,0)");
  shade.addColorStop(1, "rgba(0,0,0,0.28)");
  context.fillStyle = shade;
  context.fillRect(0, 0, canvas.width, canvas.height);

  context.fillStyle = kit.accent_color;
  if (kit.collar_style === "v_neck") {
    context.beginPath();
    context.moveTo(170, 18);
    context.lineTo(256, 110);
    context.lineTo(342, 18);
    context.closePath();
    context.fill();
  } else if (kit.collar_style === "wrap") {
    context.fillRect(120, 70, 280, 16);
  } else {
    context.fillRect(150, 0, 212, 28);
  }

  context.fillStyle = "#F8FAFC";
  context.strokeStyle = "#111827";
  context.lineWidth = 6;
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.font = `900 ${chestText.length > 12 ? 36 : chestText.length > 8 ? 48 : 58}px Arial`;
  context.strokeText(chestText, 256, 330);
  context.fillText(chestText, 256, 330);
  return canvas;
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
    const camera = new THREE.PerspectiveCamera(32, width / height, 0.1, 20);
    camera.position.set(0, 0.15, 3.15);
    camera.lookAt(0, 0.05, 0);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    } catch {
      setFallback(true);
      return;
    }
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const key = new THREE.DirectionalLight(0xffffff, 1.35);
    key.position.set(2.4, 3.2, 4);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x7dd3fc, 0.7);
    rim.position.set(-3, 1.5, -2);
    scene.add(rim);

    const shirt = new THREE.Group();
    shirtRef.current = shirt;
    scene.add(shirt);

    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    let frame = 0;
    const render = () => {
      if (!draggingRef.current && !reducedMotion) shirt.rotation.y += 0.007;
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
    const track = (object: THREE.Object3D) => {
      shirt.add(object);
      added.push(object);
      return object;
    };

    const canvas = paintShirtCanvas(kit, chestText);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    const frontMaterial = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.42, metalness: 0.04 });
    const cloth = new THREE.MeshStandardMaterial({ color: kit.primary_color, roughness: 0.58, metalness: 0.02 });
    const back = new THREE.MeshStandardMaterial({ color: kit.primary_color, roughness: 0.72 });
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.15, 1.38, 0.18), [cloth, cloth, cloth, cloth, frontMaterial, back]);
    body.position.y = 0.12;
    track(body);

    const sleeveLength = kit.sleeve_style === "long" ? 0.78 : kit.sleeve_style === "raglan" ? 0.55 : 0.46;
    const sleeveLift = kit.sleeve_style === "raglan" ? 0.55 : 0.42;
    const sleeveGeometry = new THREE.CylinderGeometry(0.16, 0.14, sleeveLength, 16);
    const leftSleeve = new THREE.Mesh(sleeveGeometry, cloth);
    leftSleeve.position.set(-0.72, sleeveLift, 0);
    leftSleeve.rotation.z = kit.sleeve_style === "raglan" ? 1.15 : 0.85;
    track(leftSleeve);
    const rightSleeve = new THREE.Mesh(sleeveGeometry, cloth);
    rightSleeve.position.set(0.72, sleeveLift, 0);
    rightSleeve.rotation.z = kit.sleeve_style === "raglan" ? -1.15 : -0.85;
    track(rightSleeve);

    if (kit.sleeve_style === "cuffed" || kit.sleeve_style === "long") {
      const cuffMaterial = new THREE.MeshStandardMaterial({ color: kit.accent_color, roughness: 0.4 });
      const cuffGeometry = new THREE.CylinderGeometry(0.155, 0.155, 0.08, 16);
      const leftCuff = new THREE.Mesh(cuffGeometry, cuffMaterial);
      leftCuff.position.copy(leftSleeve.position);
      leftCuff.rotation.copy(leftSleeve.rotation);
      leftCuff.translateY(-sleeveLength / 2);
      track(leftCuff);
      const rightCuff = new THREE.Mesh(cuffGeometry, cuffMaterial);
      rightCuff.position.copy(rightSleeve.position);
      rightCuff.rotation.copy(rightSleeve.rotation);
      rightCuff.translateY(-sleeveLength / 2);
      track(rightCuff);
    }

    const collarMaterial = new THREE.MeshStandardMaterial({ color: kit.accent_color, roughness: 0.35 });
    const collar = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.045, 10, 24), collarMaterial);
    collar.position.y = 0.78;
    collar.rotation.x = Math.PI / 2;
    track(collar);

    const shorts = new THREE.Mesh(
      new THREE.BoxGeometry(1.05, 0.42, 0.2),
      new THREE.MeshStandardMaterial({ color: kit.shorts_color || kit.primary_color, roughness: 0.6 }),
    );
    shorts.position.y = -0.78;
    track(shorts);

    if (crestDataUri) {
      const crestTexture = new THREE.TextureLoader().load(crestDataUri, (loaded) => {
        if (cancelled) loaded.dispose();
      });
      crestTexture.colorSpace = THREE.SRGBColorSpace;
      const crest = new THREE.Mesh(
        new THREE.PlaneGeometry(0.34, 0.4),
        new THREE.MeshStandardMaterial({ map: crestTexture, transparent: true, roughness: 0.5 }),
      );
      crest.position.set(-0.28, 0.28, 0.11);
      track(crest);
    }

    return () => {
      cancelled = true;
      added.forEach((object) => {
        shirt.remove(object);
        disposeObject(object);
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
