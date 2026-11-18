import React from "react";
import type { GtexSceneRendererProps } from "../GtexSceneTypes";

/** Editorial presentation for club announcements. WebGL is not used here. */
export function EditorialAnnouncement({
  title,
  subtitle,
  badgeText,
  clubName,
  subjectName,
  quote,
  stats,
}: GtexSceneRendererProps) {
  return (
    <article
      data-testid="editorial-announcement"
      className="relative overflow-hidden rounded-xl border border-emerald-500/25 bg-[#07111c] p-6 text-white shadow-2xl md:p-8"
    >
      <div className="pointer-events-none absolute inset-y-0 left-0 w-1.5 bg-gradient-to-b from-emerald-400 to-amber-400" />
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-amber-300">
        {badgeText || "Official communiqué"}
      </p>
      {clubName && <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-emerald-300">{clubName}</p>}
      <h3 className="mt-2 max-w-3xl text-2xl font-semibold tracking-tight text-white md:text-3xl">
        {title || subjectName || "Club announcement"}
      </h3>
      {subtitle && <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">{subtitle}</p>}
      {quote && (
        <blockquote className="mt-5 border-l-2 border-amber-400/70 pl-4 text-sm italic text-slate-200">
          {quote}
        </blockquote>
      )}
      {stats && stats.length > 0 && (
        <dl className="mt-6 grid gap-3 sm:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
              <dt className="text-[10px] uppercase tracking-wider text-slate-400">{stat.label}</dt>
              <dd className="mt-1 font-mono text-sm font-semibold" style={{ color: stat.accent || "#34d399" }}>
                {stat.value}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  );
}
