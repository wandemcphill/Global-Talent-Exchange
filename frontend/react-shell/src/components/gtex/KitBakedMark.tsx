import React, { useEffect, useState } from "react";

import { BAKED_ATLAS, bakedUv, type BakedManifest } from "../../match2d/bakedAtlas";

type AtlasAssets = {
  manifest: BakedManifest;
  kit: HTMLImageElement;
  body: HTMLImageElement;
  parts: HTMLImageElement;
};

let assetsPromise: Promise<AtlasAssets | null> | null = null;
const renderedMarkCache = new Map<string, string>();

function parseHex(hex: string): [number, number, number] {
  const cleaned = String(hex || "#00C991").trim().replace(/^#/, "");
  const full =
    cleaned.length === 3
      ? cleaned
          .split("")
          .map((c) => c + c)
          .join("")
      : cleaned.padEnd(6, "0");
  return [
    parseInt(full.slice(0, 2), 16) || 0,
    parseInt(full.slice(2, 4), 16) || 201,
    parseInt(full.slice(4, 6), 16) || 145,
  ];
}

function loadImage(url: string): Promise<HTMLImageElement> {
  const image = new Image();
  image.crossOrigin = "anonymous";
  image.src = url;
  return image.decode().then(() => image);
}

function loadAtlasAssets(): Promise<AtlasAssets | null> {
  if (!assetsPromise) {
    assetsPromise = (async () => {
      try {
        const res = await fetch(BAKED_ATLAS.manifest);
        if (!res.ok) return null;
        const manifest = (await res.json()) as BakedManifest;
        const [kit, body, parts] = await Promise.all([
          loadImage(BAKED_ATLAS.kit),
          loadImage(BAKED_ATLAS.body),
          loadImage(BAKED_ATLAS.parts),
        ]);
        if (!kit.naturalWidth || !body.naturalWidth) return null;
        return { manifest, kit, body, parts };
      } catch {
        return null;
      }
    })();
  }
  return assetsPromise;
}

function renderTintedMark(assets: AtlasAssets, color: string): string | null {
  const cached = renderedMarkCache.get(color);
  if (cached) return cached;

  const { manifest, kit, body, parts } = assets;
  const cell = manifest.cell || 64;
  // Direction 6 faces camera-forward cleanly for a lineup badge icon
  const uv = bakedUv(manifest, "idle", 6, 0);

  const sampleCell = (image: HTMLImageElement): Uint8ClampedArray | null => {
    const c = document.createElement("canvas");
    c.width = cell;
    c.height = cell;
    const cx = c.getContext("2d");
    if (!cx) return null;
    cx.drawImage(
      image,
      uv.offsetX * image.naturalWidth,
      (1 - uv.offsetY - uv.repeatY) * image.naturalHeight,
      uv.repeatX * image.naturalWidth,
      uv.repeatY * image.naturalHeight,
      0,
      0,
      cell,
      cell,
    );
    return cx.getImageData(0, 0, cell, cell).data;
  };

  const kitData = sampleCell(kit);
  const bodyData = sampleCell(body);
  const partsData = sampleCell(parts);
  if (!kitData || !bodyData || !partsData) return null;

  const outCanvas = document.createElement("canvas");
  outCanvas.width = cell;
  outCanvas.height = cell;
  const outCtx = outCanvas.getContext("2d");
  if (!outCtx) return null;

  const outImg = outCtx.createImageData(cell, cell);
  const dst = outImg.data;
  const shirtRgb = parseHex(color);
  const luma = (0.299 * shirtRgb[0] + 0.587 * shirtRgb[1] + 0.114 * shirtRgb[2]) / 255;
  const shortsRgb: [number, number, number] = luma > 0.65 ? [20, 30, 48] : [241, 245, 249];
  const skinRgb: [number, number, number] = [196, 134, 94];
  const hairRgb: [number, number, number] = [28, 25, 23];
  const bootRgb: [number, number, number] = [18, 24, 36];

  for (let i = 0; i < dst.length; i += 4) {
    const ka = kitData[i + 3];
    const ba = bodyData[i + 3];
    if (ka < 10 && ba < 10) {
      // Keep background 100% transparent — never fill solid rectangles!
      dst[i + 3] = 0;
      continue;
    }
    const code = Math.round(partsData[i] / 32);
    if (ka >= ba && ka >= 10) {
      const shade = kitData[i] / 255;
      const base = code === 2 ? shortsRgb : shirtRgb;
      dst[i] = Math.min(255, Math.round(base[0] * shade * 1.08));
      dst[i + 1] = Math.min(255, Math.round(base[1] * shade * 1.08));
      dst[i + 2] = Math.min(255, Math.round(base[2] * shade * 1.08));
      dst[i + 3] = ka;
    } else {
      const shade = bodyData[i] / 255;
      if (code === 4) {
        dst[i] = Math.min(255, Math.round(skinRgb[0] * shade));
        dst[i + 1] = Math.min(255, Math.round(skinRgb[1] * shade));
        dst[i + 2] = Math.min(255, Math.round(skinRgb[2] * shade));
      } else if (code === 5) {
        dst[i] = Math.min(255, Math.round(hairRgb[0] * (0.5 + shade * 0.6)));
        dst[i + 1] = Math.min(255, Math.round(hairRgb[1] * (0.5 + shade * 0.6)));
        dst[i + 2] = Math.min(255, Math.round(hairRgb[2] * (0.5 + shade * 0.6)));
      } else if (code === 6) {
        dst[i] = Math.min(255, Math.round(bootRgb[0] * (0.5 + shade * 0.6)));
        dst[i + 1] = Math.min(255, Math.round(bootRgb[1] * (0.5 + shade * 0.6)));
        dst[i + 2] = Math.min(255, Math.round(bootRgb[2] * (0.5 + shade * 0.6)));
      } else {
        dst[i] = bodyData[i];
        dst[i + 1] = bodyData[i + 1];
        dst[i + 2] = bodyData[i + 2];
      }
      dst[i + 3] = ba;
    }
  }

  outCtx.putImageData(outImg, 0, 0);
  const url = outCanvas.toDataURL();
  renderedMarkCache.set(color, url);
  return url;
}

/** Idle frame of the match footballer, tinted cleanly with the club shirt on a transparent background. */
export function KitBakedMark({
  color = "#00C991",
  size = 28,
}: {
  color?: string;
  size?: number;
}) {
  const [src, setSrc] = useState<string | null>(() => renderedMarkCache.get(color) || null);

  useEffect(() => {
    const existing = renderedMarkCache.get(color);
    if (existing) {
      setSrc(existing);
      return;
    }
    let cancelled = false;
    void loadAtlasAssets().then((assets) => {
      if (!assets || cancelled) return;
      const url = renderTintedMark(assets, color);
      if (url && !cancelled) setSrc(url);
    });
    return () => {
      cancelled = true;
    };
  }, [color]);

  if (!src) {
    return (
      <span
        aria-hidden
        className="inline-block shrink-0 rounded-full border border-white/30"
        style={{ width: size * 0.72, height: size * 0.72, background: color }}
      />
    );
  }
  return <img src={src} alt="" width={size} height={size} className="inline-block shrink-0 object-contain" />;
}
