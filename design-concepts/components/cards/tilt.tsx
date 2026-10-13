"use client";

import { useRef } from "react";
import { cn } from "@/lib/utils";

type TiltProps = {
  children: React.ReactNode;
  className?: string;
  intensity?: number;
};

/**
 * Pointer-driven tilt + floodlight sheen. Writes CSS variables directly so
 * moving the pointer never triggers a React render.
 */
export function Tilt({ children, className, intensity = 10 }: TiltProps) {
  const ref = useRef<HTMLDivElement>(null);

  function handleMove(event: React.PointerEvent<HTMLDivElement>) {
    const node = ref.current;
    if (!node || event.pointerType === "touch") return;
    const rect = node.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    node.style.setProperty("--rx", `${(0.5 - y) * intensity}deg`);
    node.style.setProperty("--ry", `${(x - 0.5) * intensity}deg`);
    node.style.setProperty("--mx", `${x * 100}%`);
    node.style.setProperty("--my", `${y * 100}%`);
    node.style.setProperty("--sheen", "1");
  }

  function handleLeave() {
    const node = ref.current;
    if (!node) return;
    node.style.setProperty("--rx", "0deg");
    node.style.setProperty("--ry", "0deg");
    node.style.setProperty("--sheen", "0");
  }

  return (
    <div className="[perspective:1000px]">
      <div
        ref={ref}
        onPointerMove={handleMove}
        onPointerLeave={handleLeave}
        className={cn(
          "group/tilt relative transition-transform duration-300 ease-out will-change-transform",
          "[transform:rotateX(var(--rx,0deg))_rotateY(var(--ry,0deg))] [transform-style:preserve-3d]",
          className,
        )}
      >
        {children}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-[var(--sheen,0)] mix-blend-soft-light transition-opacity duration-300"
          style={{
            background:
              "radial-gradient(circle at var(--mx,50%) var(--my,30%), color-mix(in oklab, var(--foreground) 55%, transparent), transparent 55%)",
          }}
        />
      </div>
    </div>
  );
}
