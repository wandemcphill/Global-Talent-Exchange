import React from "react";
import { fmt } from "@/lib/owner";

export function Panel({ title, eyebrow, action, children, className = "", testid, live }: any) {
  return (
    <section
      data-testid={testid}
      className={`gx-panel gx-rise overflow-hidden ${live ? "gx-panel-live" : ""} ${className}`}
    >
      {/* Subtle Top-Left Specular Ambient Glow */}
      <div
        className="pointer-events-none absolute -top-16 -left-16 h-40 w-56 rounded-full opacity-25 blur-2xl"
        style={{
          background: live
            ? "radial-gradient(circle, rgba(16,185,129,0.55), transparent 70%)"
            : "radial-gradient(circle, rgba(56,189,248,0.35), transparent 70%)",
        }}
      />
      {(title || eyebrow || action) && (
        <header className="relative z-10 mb-5 flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.07] pb-3.5">
          <div>
            {eyebrow && (
              <p className="gx-eyebrow mb-1 flex items-center gap-1.5">
                {live && <span className="gx-live-dot inline-block h-2 w-2 rounded-full bg-emerald-400" />}
                {eyebrow}
              </p>
            )}
            {title && <h3 className="gx-h3">{title}</h3>}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </header>
      )}
      <div className="relative z-10">{children}</div>
    </section>
  );
}

export function Btn({ variant = "primary", className = "", children, ...rest }: any) {
  return (
    <button className={`gx-btn gx-btn-${variant} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function Coin({ amount, currency = "GTEX", className = "", testid }: any) {
  const color =
    currency === "FAN"
      ? "text-amber-300 bg-amber-500/15 border-amber-400/35"
      : currency === "NGN"
      ? "text-emerald-300 bg-emerald-500/15 border-emerald-400/35"
      : "text-sky-300 bg-sky-500/15 border-sky-400/35";
  return (
    <span data-testid={testid} className={`gx-mono font-bold text-white inline-flex items-baseline gap-1 ${className}`}>
      <span>
        {currency === "NGN" ? "₦" : ""}
        {fmt(amount)}
      </span>
      {currency !== "NGN" && (
        <span className={`rounded px-1.5 py-0.2 text-[10px] font-extrabold border ${color}`}>
          {currency === "FAN" ? "FAN" : "GTX"}
        </span>
      )}
    </span>
  );
}

export function Stat({ label, value, hint, tone = "default", testid }: any) {
  const tones: any = {
    default: "text-white",
    good: "text-emerald-400",
    warn: "text-amber-300",
    bad: "text-red-400",
  };
  const barColors: any = {
    default: "bg-sky-400 shadow-[0_0_12px_#38bdf8]",
    good: "bg-emerald-400 shadow-[0_0_12px_#10b981]",
    warn: "bg-amber-400 shadow-[0_0_12px_#f59e0b]",
    bad: "bg-red-400 shadow-[0_0_12px_#ef4444]",
  };
  const strokeColors: any = {
    default: "#38bdf8",
    good: "#10b981",
    warn: "#f59e0b",
    bad: "#ef4444",
  };

  return (
    <div
      data-testid={testid}
      className="group relative min-w-0 overflow-hidden rounded-xl border border-white/[0.1] bg-slate-950/65 p-3.5 transition-all hover:border-white/20"
      style={{
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.1), 0 10px 24px -8px rgba(0,0,0,0.6)",
      }}
    >
      {/* Left Vertical Telemetry Bar */}
      <div className={`absolute left-0 top-2.5 bottom-2.5 w-1 rounded-r ${barColors[tone] || barColors.default}`} />

      {/* Subtle Background SVG Micro-Sparkline */}
      <svg
        viewBox="0 0 120 36"
        className="pointer-events-none absolute right-2 bottom-1.5 h-8 w-24 opacity-25 transition-opacity group-hover:opacity-45"
      >
        <path
          d={
            tone === "bad"
              ? "M2,8 L28,12 L54,10 L82,22 L118,30"
              : "M2,30 L28,24 L54,26 L84,14 L118,6"
          }
          fill="none"
          stroke={strokeColors[tone] || strokeColors.default}
          strokeWidth="2.2"
          strokeLinecap="round"
        />
      </svg>

      <div className="pl-2">
        <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-slate-400 truncate">
          {label}
        </p>
        <p className={`gx-display mt-1 truncate text-2xl font-black tracking-tight ${tones[tone] || tones.default}`}>
          {value}
        </p>
        {hint && <p className="mt-0.5 text-xs font-medium text-slate-400 truncate">{hint}</p>}
      </div>
    </div>
  );
}

export function Chip({ children, tone = "slate", testid }: any) {
  const tones: any = {
    slate: "border-white/15 bg-white/[0.05] text-slate-200",
    emerald: "border-emerald-400/45 text-emerald-300 bg-emerald-500/15 shadow-[0_0_14px_rgba(16,185,129,0.2)]",
    gold: "border-amber-400/50 text-amber-300 bg-amber-500/15 shadow-[0_0_14px_rgba(245,158,11,0.2)]",
    red: "border-red-400/45 text-red-300 bg-red-500/15",
    cyan: "border-cyan-400/45 text-cyan-300 bg-cyan-500/15 shadow-[0_0_14px_rgba(6,182,212,0.2)]",
    blue: "border-blue-400/45 text-blue-300 bg-blue-500/15",
  };
  return (
    <span data-testid={testid} className={`gx-chip ${tones[tone] || tones.slate}`}>
      {children}
    </span>
  );
}

export function TraitBar({ label, value, max = 20, testid }: any) {
  const pct = Math.max(0, Math.min(100, (Number(value) / max) * 100));
  const gradient =
    pct >= 75
      ? "from-emerald-400 via-teal-300 to-amber-300 shadow-[0_0_12px_rgba(16,185,129,0.6)]"
      : pct >= 45
      ? "from-cyan-400 to-emerald-400 shadow-[0_0_10px_rgba(6,182,212,0.45)]"
      : "from-amber-400 to-orange-500";
  return (
    <div data-testid={testid}>
      <div className="mb-1.5 flex justify-between text-[11px] font-bold uppercase tracking-[0.12em] text-slate-300">
        <span>{label}</span>
        <span className="gx-mono text-white">
          {value}/{max}
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-950/90 p-0.5 border border-white/10">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-[width] duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function Empty({ title, body, action, testid }: any) {
  return (
    <div
      data-testid={testid}
      className="rounded-2xl border border-dashed border-white/15 bg-slate-950/40 p-8 text-center"
    >
      <p className="gx-display text-xl font-black uppercase text-white">{title}</p>
      {body && <p className="mx-auto mt-1.5 max-w-md text-sm text-slate-400">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Loading({ label = "Loading" }: any) {
  return (
    <div
      data-testid="loading-state"
      className="flex items-center gap-3 p-8 text-sm font-semibold text-slate-300"
    >
      <span className="gx-live-dot h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_12px_#10b981]" />{" "}
      {label}…
    </div>
  );
}

export function PageHeader({ eyebrow, title, sub, action }: any) {
  return (
    <div
      className="relative mb-7 overflow-hidden rounded-2xl border border-white/[0.12] p-5 sm:p-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between gx-pitch-grid"
      style={{
        background:
          "linear-gradient(135deg, rgba(16, 185, 129, 0.14) 0%, rgba(15, 23, 42, 0.92) 52%, rgba(245, 158, 11, 0.10) 100%)",
        boxShadow:
          "0 18px 40px -12px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.16)",
      }}
    >
      <div className="relative z-10">
        {eyebrow && (
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-emerald-400/35 bg-emerald-500/15 px-3 py-0.5">
            <span className="gx-live-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <p className="gx-eyebrow !text-[10px]">{eyebrow}</p>
          </div>
        )}
        <h1 className="gx-h2">{title}</h1>
        {sub && <p className="mt-1.5 max-w-2xl text-sm font-medium text-slate-300">{sub}</p>}
      </div>
      {action && <div className="relative z-10 flex flex-wrap items-center gap-2.5">{action}</div>}
    </div>
  );
}
