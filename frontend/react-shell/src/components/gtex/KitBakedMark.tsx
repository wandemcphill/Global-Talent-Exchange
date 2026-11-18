import React, { useEffect, useState } from "react";

import { BAKED_ATLAS, bakedUv, type BakedManifest } from "../../match2d/bakedAtlas";

let manifestPromise: Promise<BakedManifest | null> | null = null;

function loadManifest(): Promise<BakedManifest | null> {
  if (!manifestPromise) {
    manifestPromise = fetch(BAKED_ATLAS.manifest)
      .then((response) => (response.ok ? (response.json() as Promise<BakedManifest>) : null))
      .catch(() => null);
  }
  return manifestPromise;
}

/** Idle frame of the match footballer, tinted with the club shirt. */
export function KitBakedMark({
  color = "#00C991",
  size = 28,
}: {
  color?: string;
  size?: number;
}) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const manifest = await loadManifest();
      if (!manifest || cancelled) return;
      const uv = bakedUv(manifest, "idle", 0, 0);
      const load = (url: string) => {
        const image = new Image();
        image.src = url;
        return image.decode().then(() => image);
      };
      const [kitImage, bodyImage] = await Promise.all([load(BAKED_ATLAS.kit), load(BAKED_ATLAS.body)]);
      if (cancelled || !kitImage.naturalWidth) return;
      const canvas = document.createElement("canvas");
      canvas.width = manifest.cell;
      canvas.height = manifest.cell;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const crop = (image: HTMLImageElement) => {
        ctx.drawImage(
          image,
          uv.offsetX * image.naturalWidth,
          (1 - uv.offsetY - uv.repeatY) * image.naturalHeight,
          uv.repeatX * image.naturalWidth,
          uv.repeatY * image.naturalHeight,
          0,
          0,
          manifest.cell,
          manifest.cell,
        );
      };
      crop(kitImage);
      ctx.globalCompositeOperation = "multiply";
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, manifest.cell, manifest.cell);
      ctx.globalCompositeOperation = "source-over";
      crop(bodyImage);
      if (!cancelled) setSrc(canvas.toDataURL());
    })();
    return () => {
      cancelled = true;
    };
  }, [color]);

  if (!src) {
    return (
      <span
        aria-hidden
        className="inline-block rounded-full border border-white/30"
        style={{ width: size, height: size, background: color }}
      />
    );
  }
  return <img src={src} alt="" width={size} height={size} className="inline-block object-contain" />;
}
