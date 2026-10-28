import React, { useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Award,
  BookOpen,
  Building2,
  CandlestickChart,
  Clock,
  Compass,
  Flag,
  Flame,
  Gauge,
  Globe,
  Inbox,
  LogOut,
  Newspaper,
  Search,
  Shield,
  Shirt,
  ShoppingBag,
  Sparkles,
  Sprout,
  Trophy,
  Wallet,
  Video,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { fmt, useActiveClub, useControlCenter } from "@/lib/owner";
import { Loading } from "@/components/gtex/ui";
import { GlobalLiveTicker } from "@/components/gtex/GlobalLiveTicker";
import { CommandPaletteModal } from "@/components/gtex/ApexWidgets";
import { formatWorldDate, formatWorldTime, useWorldClock } from "@/lib/worldClock";

const NAV = [
  { to: "/app", label: "Control Center", icon: Gauge, end: true, id: "home", category: "CLUB HQ & DYNASTY" },
  { to: "/app/clubs", label: "My Clubs", icon: Building2, id: "clubs", category: "CLUB HQ & DYNASTY" },
  { to: "/app/showroom", label: "Showroom", icon: Sparkles, id: "showroom", category: "CLUB HQ & DYNASTY" },
  { to: "/app/story", label: "Club Story", icon: BookOpen, id: "story", category: "CLUB HQ & DYNASTY" },
  { to: "/app/inbox", label: "Inbox", icon: Inbox, id: "inbox", category: "CLUB HQ & DYNASTY" },

  { to: "/app/squad", label: "Manager & Squad", icon: Shirt, id: "squad", category: "FOOTBALL & TRANSFERS" },
  { to: "/app/transfer-hub", label: "Transfer Hub", icon: Compass, id: "transfers", category: "FOOTBALL & TRANSFERS" },
  { to: "/app/academy", label: "Academy", icon: Sprout, id: "academy", category: "FOOTBALL & TRANSFERS" },
  { to: "/app/competitions", label: "Competitions", icon: Trophy, id: "competitions", category: "FOOTBALL & TRANSFERS" },
  { to: "/app/national", label: "National Team", icon: Flag, id: "national", category: "FOOTBALL & TRANSFERS" },

  { to: "/app/newsroom", label: "AI Newsroom", icon: Newspaper, id: "newsroom", category: "WORLD & MEDIA" },
  { to: "/app/regen-world", label: "Regen World", icon: Globe, id: "regen-world", category: "WORLD & MEDIA" },
  { to: "/app/awards", label: "Regen Awards", icon: Award, id: "awards", category: "WORLD & MEDIA" },
  { to: "/app/creator-access", label: "Creator Access", icon: Video, id: "creator-access", category: "WORLD & MEDIA" },

  { to: "/app/finance", label: "Finance & Ledger", icon: Wallet, id: "finance", category: "ECONOMY & VAULT" },
  { to: "/app/market", label: "Player Shares", icon: ShoppingBag, id: "market", category: "ECONOMY & VAULT" },
  { to: "/app/jackpot", label: "Global Jackpot", icon: Flame, id: "jackpot", category: "ECONOMY & VAULT" },
  { to: "/app/coin-traders", label: "Coin Traders", icon: CandlestickChart, id: "coin-traders", category: "ECONOMY & VAULT" },
];

function NavItem({ item, badge }: any) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      data-testid={`nav-${item.id}`}
      className={({ isActive }) =>
        `group flex items-center gap-3 rounded-xl px-3 py-2 text-xs font-bold uppercase tracking-wider transition-all ${
          isActive
            ? "bg-gradient-to-r from-emerald-500/20 to-emerald-500/5 text-white shadow-[inset_3px_0_0_#10B981,0_4px_14px_rgba(0,0,0,0.4)] border border-emerald-500/35"
            : "text-slate-400 hover:bg-white/[0.05] hover:text-white border border-transparent"
        }`
      }
    >
      <Icon size={15} className="shrink-0 text-emerald-400/85 group-hover:text-emerald-300" />
      <span className="truncate">{item.label}</span>
      {badge > 0 && (
        <span className="gx-mono ml-auto rounded-md bg-amber-400 px-1.5 py-0.2 text-[10px] font-black text-slate-950 shadow">
          {badge}
        </span>
      )}
    </NavLink>
  );
}

function ClubSwitcher() {
  const { clubs, active, select } = useActiveClub();
  if (!clubs.length) return null;
  return (
    <div className="flex items-center gap-2">
      {active && (
        <span
          className="gx-display hidden sm:flex size-7 shrink-0 items-center justify-center rounded-lg text-[10px] font-black shadow-md border border-white/20"
          style={{
            background: active.primary_color || "#10b981",
            color: active.secondary_color || "#070b11",
          }}
        >
          {(active.short_name || active.club_name).slice(0, 3).toUpperCase()}
        </span>
      )}
      <select
        data-testid="club-switcher"
        className="gx-input max-w-[220px] py-1.5 text-xs border-white/15 bg-slate-950/90 font-bold rounded-xl"
        value={active?.club_id}
        onChange={(e) => select(e.target.value)}
      >
        {clubs.map((c) => (
          <option key={c.club_id} value={c.club_id}>
            {c.club_name}
          </option>
        ))}
      </select>
    </div>
  );
}

function GlobalWorldClockPill() {
  const { data: clock } = useWorldClock();
  if (!clock) return null;
  return (
    <div
      data-testid="global-world-clock-pill"
      className="hidden md:flex items-center gap-2 rounded-full border border-sky-400/35 bg-sky-950/50 px-3 py-1 text-[11px] font-medium text-sky-200 shadow-inner"
      title={`Authoritative GTEX World Clock · ${clock.isPaused ? "Paused" : "Running"}`}
    >
      <Clock size={13} className="text-amber-300 shrink-0" />
      <span className="font-bold text-amber-300">
        {clock.currentSeasonLabel || `GTEX Year ${clock.gtexYearsRunning || 1}`}
      </span>
      <span className="text-white/40">·</span>
      <span className="gx-mono text-white">{formatWorldDate(clock.worldDate)}</span>
      <span className="text-white/40">·</span>
      <span className="gx-mono text-sky-300">{formatWorldTime(clock.worldTime)}</span>
    </div>
  );
}

export default function AppShell() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data, isLoading } = useControlCenter();
  const { active } = useActiveClub();
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Global Ctrl+K / Cmd+K shortcut for Executive Command Spotlight
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      } else if (e.key === "Escape") {
        setPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (loading) return <Loading label="Opening the boardroom..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (isLoading) return <Loading label="Loading your clubs..." />;

  const role = String(user.role || "").toLowerCase();
  const accountType = String(user.account_type || user.accountType || "user").toLowerCase();
  const isAdmin = ["admin", "super_admin"].includes(role);
  const isTraderAccount = accountType === "coin_trader";
  const isCreatorAccount = accountType === "creator";
  const isDedicatedAccount = isTraderAccount || isCreatorAccount;
  const clubs: any[] = data?.clubs || [];
  const hasClubProfile = !isDedicatedAccount && clubs.length > 0;
  const hasActiveClub =
    !isDedicatedAccount &&
    clubs.some((c: any) => ["competition", "active"].includes(c.stage));

  const traderAllowed = ["/app/coin-traders", "/app/finance"];
  const creatorAllowed = [
    "/app/creator-access",
    "/app/newsroom",
    "/app/transfer-hub",
    "/app/regen-world",
    "/app/awards",
    "/app/market",
    "/app/competitions",
    "/app/national",
    "/app/finance",
  ];
  const routeIsAllowed = (allowed: string[]) =>
    allowed.some((route) => pathname === route || pathname.startsWith(`${route}/`));

  if (isTraderAccount && pathname !== "/app" && !routeIsAllowed(traderAllowed)) {
    return <Navigate to="/app/coin-traders" replace />;
  }
  if (isCreatorAccount && pathname !== "/app" && !routeIsAllowed(creatorAllowed)) {
    return <Navigate to="/app/creator-access" replace />;
  }
  if (isTraderAccount && pathname === "/app") {
    return <Navigate to="/app/coin-traders" replace />;
  }
  if (isCreatorAccount && pathname === "/app") {
    return <Navigate to="/app/creator-access" replace />;
  }

  if (!isAdmin && !isDedicatedAccount && hasClubProfile && !hasActiveClub) {
    return <Navigate to="/onboarding" replace />;
  }

  const normalNav = hasActiveClub
    ? NAV
    : NAV.filter((item) =>
        [
          "home",
          "clubs",
          "showroom",
          "jackpot",
          "regen-world",
          "awards",
          "market",
          "competitions",
          "national",
          "finance",
          "creator-access",
          "coin-traders",
        ].includes(item.id)
      );
  const visibleNav = isTraderAccount
    ? NAV.filter((item) => ["coin-traders", "finance"].includes(item.id))
    : isCreatorAccount
    ? NAV.filter((item) =>
        [
          "creator-access",
          "newsroom",
          "transfers",
          "regen-world",
          "awards",
          "market",
          "competitions",
          "national",
          "finance",
        ].includes(item.id)
      ).map((item) => (item.id === "creator-access" ? { ...item, label: "Creator Studio" } : item))
    : normalNav;

  const wallet = data?.economy?.wallet || {};
  const clubPrimary = active?.primary_color || "#10b981";
  const clubSecondary = active?.secondary_color || "#f59e0b";

  // Group visible navigation items by category for zero-clutter scanning
  const categories = Array.from(new Set(visibleNav.map((n) => n.category || "COMMAND")));

  return (
    <div className="min-h-screen bg-[#050811] text-slate-100">
      {/* Global Ctrl+K Command Spotlight Modal */}
      <CommandPaletteModal
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        items={visibleNav}
        onNavigate={(to) => navigate(to)}
      />

      {/* Desktop Fixed Sidebar */}
      <aside
        className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/[0.09] lg:flex"
        style={{
          background: "linear-gradient(180deg, #060a14 0%, #04070f 100%)",
          boxShadow: "10px 0 36px rgba(0,0,0,0.65)",
        }}
      >
        <div className="px-5 pb-4 pt-5 border-b border-white/[0.08] flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <span
                className="flex size-8 items-center justify-center rounded-xl font-display text-sm font-black text-slate-950 shadow-lg"
                style={{
                  background: "linear-gradient(135deg, #34d399, #10b981)",
                  boxShadow: "0 0 18px rgba(16,185,129,0.5)",
                }}
              >
                GX
              </span>
              <p className="gx-display text-2xl font-black tracking-tight text-white leading-none">
                GTEX
              </p>
            </div>
            <p className="gx-eyebrow mt-1.5 !text-[9px] text-emerald-400">
              Football Management Universe
            </p>
          </div>
        </div>

        <nav className="gx-scroll flex-1 space-y-4 overflow-y-auto px-3 py-4" data-testid="primary-nav">
          {categories.map((cat) => (
            <div key={cat} className="space-y-1">
              <p className="px-3 text-[9px] font-extrabold uppercase tracking-[0.2em] text-slate-500">
                {cat}
              </p>
              {visibleNav
                .filter((n) => (n.category || "COMMAND") === cat)
                .map((n) => (
                  <NavItem
                    key={n.to}
                    item={n}
                    badge={n.id === "inbox" ? data?.inbox_open_count : 0}
                  />
                ))}
            </div>
          ))}
          {isAdmin && (
            <div className="pt-3 border-t border-white/[0.08]">
              <NavItem item={{ to: "/app/admin", label: "Admin Godmode", icon: Shield, id: "admin" }} />
            </div>
          )}
        </nav>

        <div className="border-t border-white/[0.09] bg-black/50 p-4">
          <p className="truncate text-xs font-extrabold text-white">
            {user.display_name || user.username}
          </p>
          <p className="gx-mono text-[10px] text-slate-400 mt-0.5">
            {isTraderAccount
              ? "Coin trader account · dedicated lane"
              : isCreatorAccount
              ? "Creator account · dedicated lane"
              : hasActiveClub
              ? `Owner integrity ${data?.integrity?.score ?? 100}/100`
              : "User account · club ownership optional"}
          </p>
          <button
            data-testid="logout-button"
            onClick={() => {
              logout();
              navigate("/");
            }}
            className="mt-3 flex items-center gap-2 text-xs font-semibold text-slate-400 transition-colors hover:text-white"
          >
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main App Content Viewport */}
      <div className="lg:pl-64">
        {/* Sticky Broadcast Top Bar */}
        <header className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-white/[0.1] bg-slate-950/85 px-4 py-2.5 backdrop-blur-xl sm:px-8">
          <p className="gx-display text-xl font-black text-white lg:hidden">GTEX</p>
          {!isDedicatedAccount && <ClubSwitcher />}
          <GlobalWorldClockPill />

          {/* Quick Command Palette Trigger (Ctrl+K) */}
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="hidden xl:inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:border-emerald-400/50 hover:text-white"
          >
            <Search size={13} className="text-emerald-400" />
            <span>Quick Jump...</span>
            <kbd className="rounded bg-white/10 px-1.5 py-0.2 text-[10px] font-bold text-slate-300">
              Ctrl K
            </kbd>
          </button>

          {/* Glowing Vault Balance Pills */}
          <div className="ml-auto flex items-center gap-2.5 text-xs">
            {hasActiveClub ? (
              <span
                data-testid="topbar-gtex-balance"
                className="gx-mono inline-flex items-center gap-1.5 rounded-xl border border-sky-400/35 bg-slate-950/90 px-3 py-1 text-slate-200 shadow-inner"
              >
                <span className="h-2 w-2 rounded-full bg-sky-400 shadow-[0_0_8px_#38bdf8]" />
                <span>Treasury</span>
                <b className="text-white font-mono">{fmt(wallet.gtex_total)}</b>
                <span className="text-sky-400 font-extrabold">GTX</span>
              </span>
            ) : (
              <span data-testid="topbar-user-account" className="gx-mono text-slate-300">
                {isTraderAccount
                  ? "Coin Trader account · dedicated lane"
                  : isCreatorAccount
                  ? "Creator account · dedicated lane"
                  : "GTEX member account · no club required"}
              </span>
            )}
            <span
              data-testid="topbar-fan-balance"
              className="gx-mono hidden sm:inline-flex items-center gap-1.5 rounded-xl border border-amber-400/35 bg-slate-950/90 px-3 py-1 text-slate-200 shadow-inner"
            >
              <span className="h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_#f59e0b]" />
              <b className="text-white font-mono">{fmt(wallet.fan_total)}</b>
              <span className="text-amber-400 font-extrabold">FAN</span>
            </span>
          </div>

          {/* Responsive Mobile Navigation Rail */}
          <nav className="gx-scroll -mx-1 flex w-full gap-1.5 overflow-x-auto lg:hidden pt-2 border-t border-white/[0.08]">
            {visibleNav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-bold uppercase ${
                    isActive
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "text-slate-400"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </header>

        {/* Global Live Ticker */}
        <GlobalLiveTicker />

        {/* Screen Outlet with Dynamic Club-Color Ambient Stadium Spotlight */}
        <main
          className="relative min-h-[calc(100vh-64px)]"
          style={{
            background: `radial-gradient(ellipse at 25% 0%, ${clubPrimary}1f 0%, ${clubSecondary}0d 38%, transparent 70%)`,
          }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
