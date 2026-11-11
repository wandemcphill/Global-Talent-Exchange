import React, { useEffect, useState } from "react";
import { publicAssetPath } from "@/lib/publicPath";
import type { InspectionFrame } from "@/lib/showroomInspection";

const STILL_MS = 2800;

export function ShowroomInspectionReel({
  frames,
  fit = "cover",
  showLabel = true,
  onMediaError,
}: {
  frames: InspectionFrame[];
  fit?: "cover" | "contain";
  showLabel?: boolean;
  onMediaError?: (frame: InspectionFrame) => void;
}) {
  const [index, setIndex] = useState(0);
  const count = frames.length;
  const frame = frames[index] || frames[0];

  useEffect(() => {
    setIndex(0);
  }, [frames]);

  useEffect(() => {
    if (!frame || frame.kind === "video") return undefined;
    const timer = window.setTimeout(() => {
      setIndex((current) => (current + 1) % count);
    }, STILL_MS);
    return () => window.clearTimeout(timer);
  }, [frame, count, index]);

  if (!frame) return null;

  const src = publicAssetPath(frame.src);
  const objectFit = fit === "contain" ? "object-contain" : "object-cover";

  return (
    <div className="relative h-full w-full bg-black" data-testid="showroom-inspection-reel">
      {frame.kind === "video" ? (
        <video
          key={src}
          src={src}
          className={`h-full w-full ${objectFit}`}
          autoPlay
          muted
          playsInline
          data-testid="showroom-inspection-video"
          onEnded={() => setIndex((current) => (current + 1) % count)}
          onError={() => onMediaError?.(frame)}
        />
      ) : (
        <img
          key={src}
          src={src}
          alt={frame.label}
          className={`h-full w-full ${objectFit}`}
          data-testid="showroom-inspection-still"
        />
      )}
      {showLabel && (
        <div className="absolute bottom-3 left-3 rounded-md border border-white/15 bg-black/70 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-white">
          {frame.label}
          <span className="ml-2 font-mono text-white/60">
            {index + 1}/{count}
          </span>
        </div>
      )}
    </div>
  );
}
