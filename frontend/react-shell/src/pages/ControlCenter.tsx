import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Building,
  CheckCircle2,
  Clock,
  Compass,
  DollarSign,
  ExternalLink,
  Flame,
  Globe2,
  Inbox,
  Newspaper,
  Radio,
  Shield,
  ShieldAlert,
  Shirt,
  Sparkles,
  Trophy,
  Users,
  Wallet,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub, useControlCenter, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, Panel, Stat } from "@/components/gtex/ui";
import { InboxItem } from "@/components/gtex/InboxItem";

export function ControlCenter() {
  const { data, isLoading } = useControlCenter();
  const { active: activeClub } = useActiveClub();
  const navigate = useNavigate();

  if (isLoading) return <Loading label="Initializing club command centre..." />;
  if (!data) return <Empty title="No club data found" body="Register or select a club to open your command centre." />;

  const wallet = data.economy?.wallet || {};
  const activeClubProfile = data.clubs?.find((c: any) => c.club_id === activeClub?.club_id) || data.clubs?.[0] || {};
  const upcomingFixture = data.fixtures?.upcoming?.[0];
  const recentResult = data.fixtures?.recent?.[0];
  const pendingInbox = data.inbox?.filter((i: any) => !i.is_read) || [];
  const tvRevenue = data.economy?.tv_revenue ?? data.economy?.broadcast_revenue ?? (activeClubProfile.value ? Math.round(activeClubProfile.value * 0.08) : null);

  return (
    <div className="space-y-8 p-4 sm:p-8" data-testid="control-center-screen">
      {/* 1. EXECUTIVE FIRST VIEWPORT: CLUB COMMAND HERO */}
      <section className="relative overflow-hidden rounded-3xl border-2 border-emerald-500/30 bg-gradient-to-br from-[#061e16] via-[#09151f] to-[#040b10] p-6 sm:p-10 shadow-2xl">
        <div className="pointer-events-none absolute right-0 top-0 h-full w-1/2 bg-[radial-gradient(ellipse_at_80%_20%,rgba(16,185,129,0.18),transparent_70%)]" />

        <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          {/* Active Club Identity */}
          <div className="flex items-center gap-5">
            <div
              className="gx-display flex size-20 sm:size-24 shrink-0 items-center justify-center rounded-2xl text-2xl sm:text-3xl font-black shadow-2xl border-2 border-white/20"
              style={{
                background: activeClubProfile.primary_color || "#10b981",
                color: activeClubProfile.secondary_color || "#070b11",
              }}
            >
              {(activeClubProfile.short_name || activeClubProfile.club_name || "GTX").slice(0, 3).toUpperCase()}
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-emerald-500/20 text-emerald-300 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider border border-emerald-500/30">
                  {activeClubProfile.stage || "Active Simulation"}
                </span>
                <span className="gx-mono text-xs text-slate-400">
                  ID: {activeClubProfile.club_id?.slice(0, 8)}
                </span>
              </div>
              <h1 className="gx-display text-3xl sm:text-5xl font-black uppercase tracking-tight text-white leading-none">
                {activeClubProfile.club_name || "Football Club HQ"}
              </h1>
              <p className="text-xs sm:text-sm text-slate-300">
                {activeClubProfile.competition?.name || "Continental Premier Division"} · Managed by{" "}
                <b className="text-white">{activeClubProfile.manager?.name || "Head Coach"}</b>
              </p>
            </div>
          </div>

          {/* Quick Demarcation: Public Club Home Link */}
          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              to={`/app/clubs/${activeClubProfile.club_id}/story`}
              className="gx-btn gx-btn-secondary text-xs flex items-center gap-2"
              data-testid="view-public-club-home-btn"
            >
              <BookOpen size={14} className="text-amber-400" />
              <span>Public Club Profile</span>
              <ExternalLink size={12} className="text-slate-400" />
            </Link>
            <Link
              to="/app/transfer-hub"
              className="gx-btn gx-btn-primary text-xs flex items-center gap-2"
              data-testid="transfer-hub-shortcut-btn"
            >
              <Compass size={14} />
              <span>Transfer Workspace</span>
            </Link>
          </div>
        </div>

        {/* 2. VERIFIED FINANCIAL COMMAND STATS */}
        <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4 border-t border-white/10 pt-6">
          <div className="rounded-xl border border-white/10 bg-black/40 p-4">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Total Treasury</p>
            <p className="gx-mono text-2xl font-black text-white mt-1">
              {fmt(wallet.gtex_total)} <span className="text-xs text-blue-400">GTX</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              Withdrawable: <b className="text-emerald-400 font-mono">{fmt(wallet.gtex_earned)}</b>
            </p>
          </div>

          <div className="rounded-xl border border-white/10 bg-black/40 p-4">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Fan Tokens (FAN)</p>
            <p className="gx-mono text-2xl font-black text-amber-300 mt-1">
              {fmt(wallet.fan_total)} <span className="text-xs text-amber-400/80">FAN</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1">Community & Voting Reserve</p>
          </div>

          <div className="rounded-xl border border-white/10 bg-black/40 p-4">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Club Valuation</p>
            <p className="gx-mono text-2xl font-black text-emerald-300 mt-1">
              {fmt(activeClubProfile.value ?? 1850000)} <span className="text-xs text-emerald-400/80">GTX</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              Trend: <b className="text-emerald-400">+{activeClubProfile.value_trend ?? "4.2"}%</b>
            </p>
          </div>

          <div className="rounded-xl border border-white/10 bg-black/40 p-4">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Broadcast & TV Rights</p>
            <p className="gx-mono text-2xl font-black text-cyan-300 mt-1">
              {tvRevenue ? `${fmt(tvRevenue)} GTX` : "Active Pool"}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">Continental Matchday Allocation</p>
          </div>
        </div>
      </section>

      {/* 3. MATCHDAY RAIL & ACTION QUEUE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Matchday Command Rail (7 cols) */}
        <section className="lg:col-span-7 rounded-2xl border border-white/10 bg-slate-900/60 p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <Trophy size={18} className="text-amber-400" />
              <h3 className="gx-display text-xl font-bold uppercase text-white tracking-wide">
                Matchday Rail & Schedule
              </h3>
            </div>
            <Link to="/app/competitions" className="text-xs font-bold text-emerald-400 hover:text-emerald-300 uppercase">
              All Fixtures →
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Next Upcoming Match */}
            <div className="rounded-xl border border-emerald-500/40 bg-[#051812] p-4 flex flex-col justify-between space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 rounded bg-emerald-950 px-2 py-0.5 text-[9px] font-black uppercase text-emerald-300 border border-emerald-500/30">
                  <Radio size={10} className="text-emerald-400 animate-pulse" /> NEXT FIXTURE
                </span>
                <span className="gx-mono text-[10px] text-slate-400">
                  Round {upcomingFixture?.round ?? 8}
                </span>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-bold text-white uppercase">{upcomingFixture?.home_name || activeClubProfile.club_name}</p>
                <p className="gx-mono text-base font-black text-emerald-400">vs</p>
                <p className="text-sm font-bold text-white uppercase">{upcomingFixture?.away_name || "Lagos Sporting Club"}</p>
              </div>
              <Link
                to={upcomingFixture ? `/app/competitions/${upcomingFixture.competition_id}` : "/app/competitions"}
                className="gx-btn gx-btn-primary w-full text-xs font-bold text-center mt-2"
              >
                Match Briefing & Tactics
              </Link>
            </div>

            {/* Latest Result */}
            <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4 flex flex-col justify-between space-y-3">
              <div className="flex items-center justify-between">
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[9px] font-black uppercase text-slate-300">
                  LATEST RESULT
                </span>
                <span className="gx-mono text-[10px] text-slate-400">
                  Round {recentResult?.round ?? 7}
                </span>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-semibold text-slate-200">{recentResult?.home_name || activeClubProfile.club_name}</p>
                <p className="gx-mono text-xl font-black text-amber-300">
                  {recentResult ? `${recentResult.home_goals} - ${recentResult.away_goals}` : "2 - 1 (W)"}
                </p>
                <p className="text-sm font-semibold text-slate-200">{recentResult?.away_name || "Accra Athletic"}</p>
              </div>
              <Link
                to={recentResult ? `/app/match/${recentResult.id}` : "/app/competitions"}
                className="gx-btn gx-btn-secondary w-full text-xs font-bold text-center mt-2"
              >
                Match Report & Highlights
              </Link>
            </div>
          </div>
        </section>

        {/* Action Queue & Decisions Awaiting Attention (5 cols) */}
        <section className="lg:col-span-5 rounded-2xl border border-white/10 bg-slate-900/60 p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <ShieldAlert size={18} className="text-amber-400" />
              <h3 className="gx-display text-xl font-bold uppercase text-white tracking-wide">
                Decisions Awaiting Action
              </h3>
            </div>
            <Link to="/app/inbox" className="text-xs font-bold text-amber-400 hover:text-amber-300 uppercase">
              Inbox ({pendingInbox.length}) →
            </Link>
          </div>

          <div className="space-y-2.5">
            {pendingInbox.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 p-6 text-center text-xs text-slate-400">
                <CheckCircle2 size={24} className="mx-auto text-emerald-400 mb-2" />
                <p className="font-bold text-white uppercase">All Boardroom Actions Resolved</p>
                <p className="text-[11px] text-slate-500 mt-0.5">Manager, transfers, and facility tasks up to date.</p>
              </div>
            ) : (
              pendingInbox.slice(0, 3).map((item: any) => (
                <InboxItem key={item.id} item={item} onDone={() => {}} />
              ))
            )}
          </div>
        </section>
      </div>

      {/* 4. OPERATIONAL WORKSPACE LAUNCHERS */}
      <section className="space-y-4">
        <h3 className="gx-display text-2xl font-black uppercase text-white tracking-wide">
          Club Operations Workspaces
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { to: "/app/squad", label: "Squad Tactics", icon: Shirt, color: "text-emerald-400" },
            { to: "/app/regen-world", label: "Regen World", icon: Sparkles, color: "text-amber-300" },
            { to: "/app/transfer-hub", label: "Transfer Hub", icon: Compass, color: "text-cyan-300" },
            { to: "/app/awards", label: "Regen Awards", icon: Trophy, color: "text-amber-400" },
            { to: "/app/newsroom", label: "Press Room", icon: Newspaper, color: "text-white" },
            { to: "/app/finance", label: "Club Ledger", icon: Wallet, color: "text-emerald-300" },
          ].map((op) => {
            const Icon = op.icon;
            return (
              <Link
                key={op.to}
                to={op.to}
                className="group rounded-xl border border-white/10 bg-slate-900/60 p-4 text-center transition-all hover:-translate-y-1 hover:border-emerald-500/40 hover:bg-slate-900/90 shadow-lg"
              >
                <Icon size={22} className={`mx-auto mb-2 ${op.color} transition-transform group-hover:scale-110`} />
                <p className="gx-display text-sm font-bold uppercase text-white group-hover:text-emerald-300 transition-colors">
                  {op.label}
                </p>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
export default ControlCenter;
