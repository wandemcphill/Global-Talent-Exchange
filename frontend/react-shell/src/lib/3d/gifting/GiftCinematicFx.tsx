import React, { useEffect, useRef } from "react";

interface BurstParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  max: number;
  size: number;
  color: string;
  spark: boolean;
}

const COLORS: Record<string, string[]> = {
  mythic: ["#fff6d8", "#f5cd83", "#ff7a18", "#ffffff"],
  legendary: ["#fff1c2", "#f5cd83", "#ffd56a", "#ffffff"],
  epic: ["#efe8ff", "#b8a6ff", "#7c6cff", "#ffffff"],
  rare: ["#e7fbff", "#8de0e8", "#3ec6ff", "#ffffff"],
  common: ["#f4f7fb", "#d5deea", "#9fb0c6", "#ffffff"],
};

function palette(rarity?: string): string[] {
  return COLORS[(rarity || "common").toLowerCase()] || COLORS.common;
}

function spawn(width: number, height: number, colors: string[], count: number, power: number): BurstParticle[] {
  const originX = width * 0.5;
  const originY = height * 0.42;
  const particles: BurstParticle[] = [];
  for (let i = 0; i < count; i += 1) {
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.4;
    const speed = (2.4 + Math.random() * 7.5) * power;
    particles.push({
      x: originX,
      y: originY,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 1.4,
      life: 0,
      max: 0.55 + Math.random() * 0.7,
      size: Math.random() < 0.2 ? 3.4 + Math.random() * 3 : 1.2 + Math.random() * 2.2,
      color: colors[i % colors.length],
      spark: Math.random() > 0.72,
    });
  }
  return particles;
}

export function GiftCinematicFx({
  giftKey,
  rarity,
  active,
}: {
  giftKey: string;
  rarity?: string;
  active: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!active || !giftKey) return;
    const reduced =
      typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const colors = palette(rarity);
    const rank = (rarity || "common").toLowerCase();
    const power = rank === "mythic" || rank === "legendary" ? 1.35 : rank === "epic" ? 1.15 : 1;
    let particles: BurstParticle[] = [];
    let frame = 0;
    let raf = 0;

    const resize = () => {
      const parent = canvas.parentElement;
      const width = parent?.clientWidth || 800;
      const height = parent?.clientHeight || 450;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };
    resize();

    const burst = (extra = 1) => {
      const width = canvas.clientWidth || 800;
      const height = canvas.clientHeight || 450;
      const count = Math.round((rank === "common" ? 72 : 150) * extra);
      particles = particles.concat(spawn(width, height, colors, count, power));
    };
    burst(1.15);
    let lastBeat = "entrance";
    let lastFountain = 0;

    const draw = () => {
      const width = canvas.clientWidth || 800;
      const height = canvas.clientHeight || 450;
      context.clearRect(0, 0, width, height);
      frame += 1;
      const stage = canvas.closest("[data-gift-beat]");
      const beat = stage?.getAttribute("data-gift-beat") || "hold";
      if (beat !== lastBeat) {
        if (beat === "hold") burst(0.85);
        if (beat === "exit") burst(1.4);
        lastBeat = beat;
      }
      if (beat === "hold" && frame - lastFountain > 90) {
        burst(0.45);
        lastFountain = frame;
      }
      const ringLife = beat === "entrance" ? 1 : beat === "exit" ? 0.8 : 0;
      if (ringLife > 0) {
        context.strokeStyle = `rgba(255,236,196,${ringLife})`;
        context.lineWidth = 3;
        context.beginPath();
        context.arc(width / 2, height * 0.42, 30 + (frame % 40) * 8, 0, Math.PI * 2);
        context.stroke();
      }
      particles = particles.filter((particle) => {
        particle.life += 0.016;
        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.vy += 0.045;
        particle.vx *= 0.992;
        const alpha = Math.max(0, 1 - particle.life / particle.max);
        if (alpha <= 0) return false;
        context.globalAlpha = alpha;
        context.fillStyle = particle.color;
        context.shadowColor = particle.color;
        context.shadowBlur = particle.spark ? 16 : 6;
        context.beginPath();
        if (particle.spark) {
          context.ellipse(particle.x, particle.y, particle.size * 2.2, particle.size * 0.35, Math.atan2(particle.vy, particle.vx), 0, Math.PI * 2);
        } else {
          context.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        }
        context.fill();
        return true;
      });
      context.globalAlpha = 1;
      context.shadowBlur = 0;
      const stillCelebrating = beat !== "exit" || particles.length > 0;
      if (stillCelebrating && frame < 60 * 20) raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    window.addEventListener("resize", resize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, [active, giftKey, rarity]);

  if (!active) return null;

  return (
    <>
      <div key={`${giftKey}-flash`} className="gtex-gift-flash" aria-hidden />
      <div key={`${giftKey}-shock`} className="gtex-gift-shock" aria-hidden />
      <div key={`${giftKey}-shock-b`} className="gtex-gift-shock gtex-gift-shock-late" aria-hidden />
      <canvas ref={canvasRef} className="gtex-gift-burst" aria-hidden />
    </>
  );
}
