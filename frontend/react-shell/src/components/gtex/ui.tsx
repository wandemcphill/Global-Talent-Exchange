import React from "react";
import { fmt } from "@/lib/owner";

export function Panel({ title, eyebrow, action, children, className = "", testid, live }: any) {
  return (
    <section data-testid={testid} className={`gx-panel gx-rise ${live ? "gx-panel-live" : ""} ${className}`}>
      {(title || eyebrow || action) && (
        <header className="mb-5 flex items-start justify-between gap-4">
          <div>
            {eyebrow && <p className="gx-eyebrow mb-1">{eyebrow}</p>}
            {title && <h3 className="gx-h3">{title}</h3>}
          </div>
          {action}
        </header>
      )}
      {children}
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
  const color = currency === "FAN" ? "text-amber-400" : currency === "NGN" ? "text-green-400" : "text-blue-400";
  return (
    <span data-testid={testid} className={`gx-mono font-semibold text-white ${className}`}>
      {currency === "NGN" ? "₦" : ""}
      {fmt(amount)} <span className={`text-[10px] font-bold ${color}`}>{currency === "NGN" ? "" : currency === "FAN" ? "FAN" : "GTX"}</span>
    </span>
  );
}

export function Stat({ label, value, hint, tone = "default", testid }: any) {
  const tones: any = { default: "text-white", good: "text-emerald-400", warn: "text-amber-400", bad: "text-red-400" };
  return (
    <div data-testid={testid} className="min-w-0">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={`gx-display mt-1 truncate text-2xl font-bold ${tones[tone]}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function Chip({ children, tone = "slate", testid }: any) {
  const tones: any = {
    slate: "border-white/15 text-slate-300",
    emerald: "border-emerald-500/40 text-emerald-300 bg-emerald-500/10",
    gold: "border-amber-500/40 text-amber-300 bg-amber-500/10",
    red: "border-red-500/40 text-red-300 bg-red-500/10",
    cyan: "border-cyan-500/40 text-cyan-300 bg-cyan-500/10",
    blue: "border-blue-500/40 text-blue-300 bg-blue-500/10",
  };
  return (
    <span data-testid={testid} className={`gx-chip ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function TraitBar({ label, value, max = 20, testid }: any) {
  const pct = Math.max(0, Math.min(100, (Number(value) / max) * 100));
  const color = pct >= 70 ? "bg-emerald-400" : pct >= 40 ? "bg-cyan-400" : "bg-amber-400";
  return (
    <div data-testid={testid}>
      <div className="mb-1 flex justify-between text-[11px] uppercase tracking-[0.12em] text-slate-400">
        <span>{label}</span>
        <span className="gx-mono text-slate-200">
          {value}/{max}
        </span>
      </div>
      <div className="h-1.5 rounded-sm bg-white/5">
        <div className={`h-1.5 rounded-sm ${color} transition-[width] duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Empty({ title, body, action, testid }: any) {
  return (
    <div data-testid={testid} className="rounded-sm border border-dashed border-white/10 p-6 text-center">
      <p className="gx-display text-lg font-bold uppercase text-slate-200">{title}</p>
      {body && <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Loading({ label = "Loading" }: any) {
  return (
    <div data-testid="loading-state" className="flex items-center gap-3 p-8 text-sm text-slate-400">
      <span className="gx-live-dot h-2 w-2 rounded-full bg-emerald-400" /> {label}…
    </div>
  );
}

export function PageHeader({ eyebrow, title, sub, action }: any) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="gx-eyebrow mb-2">{eyebrow}</p>
        <h1 className="gx-h2">{title}</h1>
        {sub && <p className="mt-2 max-w-2xl text-sm text-slate-400">{sub}</p>}
      </div>
      {action}
    </div>
  );
}
