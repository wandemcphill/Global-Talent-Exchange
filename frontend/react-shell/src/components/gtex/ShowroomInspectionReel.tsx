import React, { useEffect, useMemo, useState } from "react";
import { publicAssetPath } from "@/lib/publicPath";
import { splitInspectionStills, type InspectionFrame } from "@/lib/showroomInspection";

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

export function ShowroomStillStage({
  frames,
  compact = false,
}: {
  frames: InspectionFrame[];
  compact?: boolean;
}) {
  const split = useMemo(() => splitInspectionStills(frames), [frames]);
  const frameKey = frames.map((frame) => `${frame.kind}:${frame.src}`).join("|");
  const [side, setSide] = useState<"exterior" | "interior">(split.exterior.length > 0 ? "exterior" : "interior");
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setSide(split.exterior.length > 0 ? "exterior" : "interior");
    setIndex(0);
  }, [frameKey, split.exterior.length]);

  const active = side === "exterior" ? split.exterior : split.interior;
  const frame = active[index] ?? active[0];
  if (!frame) return null;

  const both = split.exterior.length > 0 && split.interior.length > 0;
  const chipClass = compact ? "bottom-12" : "bottom-3";

  return (
    <div className="relative h-full w-full bg-black" data-testid="showroom-still-stage">
      <img
        key={publicAssetPath(frame.src)}
        src={publicAssetPath(frame.src)}
        alt={frame.label}
        className="h-full w-full object-contain"
        data-testid="showroom-inspection-still"
      />
      {both && (
        <div className={`absolute left-3 z-10 flex gap-1 ${chipClass}`}>
          {(["exterior", "interior"] as const).map((choice) => (
            <button
              key={choice}
              type="button"
              onClick={() => {
                setSide(choice);
                setIndex(0);
              }}
              className={`rounded-md px-2 py-1 text-[9px] font-black uppercase tracking-wider ${
                side === choice ? "bg-amber-400 text-slate-950" : "border border-white/20 bg-black/75 text-white"
              }`}
              data-testid={`showroom-side-${choice}`}
            >
              {choice}
            </button>
          ))}
        </div>
      )}
      {active.length > 1 && (
        <div className={`absolute right-3 z-10 flex items-center gap-1 ${chipClass}`}>
          <button
            type="button"
            aria-label="Previous view"
            onClick={() => setIndex((current) => (current - 1 + active.length) % active.length)}
            className="rounded-md border border-white/20 bg-black/75 px-2 py-1 text-[10px] font-bold text-white"
          >
            ‹
          </button>
          <span className="rounded-md border border-white/15 bg-black/75 px-1.5 py-1 font-mono text-[9px] text-white/80">
            {index + 1}/{active.length}
          </span>
          <button
            type="button"
            aria-label="Next view"
            onClick={() => setIndex((current) => (current + 1) % active.length)}
            className="rounded-md border border-white/20 bg-black/75 px-2 py-1 text-[10px] font-bold text-white"
          >
            ›
          </button>
        </div>
      )}
      {!compact && (
        <div className="absolute left-3 top-3 z-10 rounded-md border border-white/15 bg-black/70 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-white">
          {frame.label}
        </div>
      )}
    </div>
  );
}
