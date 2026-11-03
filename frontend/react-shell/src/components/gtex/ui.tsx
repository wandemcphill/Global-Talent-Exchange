import React from "react";
import { fmt } from "@/lib/owner";

export function Panel({ title, eyebrow, action, children, className = "", testid, live }: any) {
  return (
    <section
      data-testid={testid}
      className={`gx-panel gx-rise overflow-hidden ${live ? "gx-panel-live" : ""} ${className}`}
    >
      {/* Subtle Top-Left Specular Ambient Spotlight */}
      <div
        className="pointer-events-none absolute -top-16 -left-16 h-36 w-52 rounded-full opacity-20 blur-2xl"
        style={{
          background: live
            ? "radial-gradient(circle, rgba(0,201,145,0.45), transparent 70%)"
            : "radial-gradient(circle, rgba(66,185,236,0.30), transparent 70%)",
        }}
      />
      {(title || eyebrow || action) && (
        <header className="relative z-10 mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-[#25354B]/70 pb-3">
          <div>
            {eyebrow && (
              <p className="gx-eyebrow mb-1 flex items-center gap-1.5">
                {live && <span className="gx-live-dot inline-block h-2 w-2 rounded-full bg-[#00C991]" />}
                {eyebrow}
              </p>
            )}
            {title && <h3 className="gx-h3 tracking-wide">{title}</h3>}
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
  const isFan = currency === "FAN";
  const isNgn = currency === "NGN";
  const badgeStyle = isFan
    ? "text-[#E5B63F] bg-[#E5B63F]/15 border-[#E5B63F]/35"
    : isNgn
    ? "text-[#00C991] bg-[#00C991]/15 border-[#00C991]/35"
    : "text-[#42B9EC] bg-[#42B9EC]/15 border-[#42B9EC]/35";

  return (
    <span data-testid={testid} className={`gx-mono font-bold text-white inline-flex items-baseline gap-1.5 ${className}`}>
      <span>
        {isNgn ? "₦" : ""}
        {fmt(amount)}
      </span>
      {!isNgn && (
        <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-extrabold tracking-wider border ${badgeStyle}`}>
          {isFan ? "FAN" : "GTX"}
        </span>
      )}
    </span>
  );
}

export function Stat({ label, value, hint, tone = "default", testid }: any) {
  const tones: any = {
    default: "text-white",
    good: "text-[#00C991]",
    warn: "text-[#E5B63F]",
    bad: "text-[#EF4444]",
    pitch: "text-[#42B9EC]",
  };
  const barColors: any = {
    default: "bg-[#42B9EC]",
    good: "bg-[#00C991]",
    warn: "bg-[#E5B63F]",
    bad: "bg-[#EF4444]",
    pitch: "bg-[#42B9EC]",
  };
  const strokeColors: any = {
    default: "#42B9EC",
    good: "#00C991",
    warn: "#E5B63F",
    bad: "#EF4444",
    pitch: "#42B9EC",
  };

  return (
    <div
      data-testid={testid}
      className="group relative min-w-0 overflow-hidden rounded-xl border border-[#25354B] bg-[#0E1A2C] p-3.5 transition-all hover:border-[#42B9EC]/40"
      style={{
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 20px -6px rgba(0,0,0,0.5)",
      }}
    >
      {/* Left Vertical Matchday Telemetry Accent */}
      <div className={`absolute left-0 top-2.5 bottom-2.5 w-1 rounded-r ${barColors[tone] || barColors.default}`} />

      {/* Background SVG Sparkline */}
      <svg
        viewBox="0 0 120 36"
        className="pointer-events-none absolute right-2 bottom-1.5 h-8 w-24 opacity-20 transition-opacity group-hover:opacity-35"
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

      <div className="pl-2.5">
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400 truncate">
          {label}
        </p>
        <p className={`gx-display mt-0.5 truncate text-2xl font-black tracking-tight ${tones[tone] || tones.default}`}>
          {value}
        </p>
        {hint && <p className="mt-0.5 text-xs font-normal text-slate-400 truncate">{hint}</p>}
      </div>
    </div>
  );
}

export function Chip({ children, tone = "slate", testid }: any) {
  const tones: any = {
    slate: "border-[#25354B] bg-white/[0.04] text-slate-300",
    emerald: "border-[#00C991]/45 text-[#00E8A8] bg-[#00C991]/12",
    gold: "border-[#E5B63F]/45 text-[#E5B63F] bg-[#E5B63F]/12",
    red: "border-red-500/40 text-red-300 bg-red-500/12",
    cyan: "border-[#42B9EC]/45 text-[#42B9EC] bg-[#42B9EC]/12",
    blue: "border-[#42B9EC]/45 text-[#42B9EC] bg-[#42B9EC]/12",
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
      ? "from-[#00C991] via-teal-300 to-[#E5B63F]"
      : pct >= 45
      ? "from-[#42B9EC] to-[#00C991]"
      : "from-[#E5B63F] to-orange-500";

  return (
    <div data-testid={testid}>
      <div className="mb-1 flex justify-between text-[11px] font-bold uppercase tracking-[0.1em] text-slate-300">
        <span>{label}</span>
        <span className="gx-mono text-white">
          {value}/{max}
        </span>
      </div>
      <div className="h-2 rounded-full bg-[#080F1C] p-0.5 border border-[#25354B]">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-[width] duration-500`}
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
      className="rounded-2xl border border-dashed border-[#25354B] bg-[#0E1A2C]/60 p-8 text-center"
    >
      <p className="gx-display text-xl font-black uppercase text-white">{title}</p>
      {body && <p className="mx-auto mt-1.5 max-w-md text-sm text-slate-400 leading-relaxed">{body}</p>}
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
      <span className="gx-live-dot h-2.5 w-2.5 rounded-full bg-[#00C991]" />{" "}
      {label}…
    </div>
  );
}

export function PageHeader({ eyebrow, title, sub, action }: any) {
  return (
    <div
      className="relative mb-6 overflow-hidden rounded-2xl border border-[#25354B] p-5 sm:p-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between gx-pitch-grid"
      style={{
        background:
          "linear-gradient(135deg, rgba(0, 201, 145, 0.10) 0%, rgba(20, 36, 58, 0.94) 50%, rgba(8, 15, 28, 0.98) 100%)",
        boxShadow:
          "0 14px 36px -10px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.08)",
      }}
    >
      <div className="relative z-10">
        {eyebrow && (
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[#00C991]/35 bg-[#00C991]/12 px-3 py-0.5">
            <span className="gx-live-dot h-1.5 w-1.5 rounded-full bg-[#00C991]" />
            <p className="gx-eyebrow !text-[10px]">{eyebrow}</p>
          </div>
        )}
        <h1 className="gx-h2 tracking-wide leading-none">{title}</h1>
        {sub && <p className="mt-1.5 max-w-2xl text-sm font-normal text-slate-300 leading-relaxed">{sub}</p>}
      </div>
      {action && <div className="relative z-10 flex flex-wrap items-center gap-2.5">{action}</div>}
    </div>
  );
}
