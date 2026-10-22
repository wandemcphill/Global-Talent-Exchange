import React from "react";
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Award,
  BookOpen,
  Building2,
  CandlestickChart,
  Compass,
  Flag,
  Gauge,
  Globe,
  Inbox,
  LogOut,
  Newspaper,
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

const NAV = [
  { to: "/app", label: "Control Center", icon: Gauge, end: true, id: "home" },
  { to: "/app/clubs", label: "My Clubs", icon: Building2, id: "clubs" },
  { to: "/app/story", label: "Club Story", icon: BookOpen, id: "story" },
  { to: "/app/newsroom", label: "AI Newsroom", icon: Newspaper, id: "newsroom" },
  { to: "/app/transfer-hub", label: "Transfer Hub", icon: Compass, id: "transfers" },
  { to: "/app/regen-world", label: "Regen World", icon: Globe, id: "regen-world" },
  { to: "/app/awards", label: "Regen Awards", icon: Award, id: "awards" },
  { to: "/app/market", label: "Player Shares", icon: ShoppingBag, id: "market" },
  { to: "/app/competitions", label: "Competitions", icon: Trophy, id: "competitions" },
  { to: "/app/squad", label: "Manager & Squad", icon: Shirt, id: "squad" },
  { to: "/app/academy", label: "Academy", icon: Sprout, id: "academy" },
  { to: "/app/national", label: "National Team", icon: Flag, id: "national" },
  { to: "/app/finance", label: "Finance & Ledger", icon: Wallet, id: "finance" },
  { to: "/app/creator-access", label: "Creator Access", icon: Video, id: "creator-access" },
  { to: "/app/coin-traders", label: "Coin Traders", icon: CandlestickChart, id: "coin-traders" },
  { to: "/app/inbox", label: "Inbox", icon: Inbox, id: "inbox" },
];

function NavItem({ item, badge }: any) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      data-testid={`nav-${item.id}`}
      className={({ isActive }) =>
        `group flex items-center gap-3 rounded-md px-3 py-2 text-xs font-bold uppercase tracking-wider transition-all ${
          isActive
            ? "bg-emerald-500/15 text-white shadow-[inset_3px_0_0_#10B981] border-r border-emerald-500/30"
            : "text-slate-400 hover:bg-white/[0.04] hover:text-white"
        }`
      }
    >
      <Icon size={15} className="shrink-0" />
      <span className="truncate">{item.label}</span>
      {badge > 0 && (
        <span className="gx-mono ml-auto rounded bg-amber-500 px-1.5 py-0.2 text-[10px] font-black text-slate-950">
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
          className="gx-display hidden sm:flex size-6 shrink-0 items-center justify-center rounded text-[10px] font-black shadow-sm"
          style={{ background: active.primary_color || "#10b981", color: active.secondary_color || "#070b11" }}
        >
          {(active.short_name || active.club_name).slice(0, 3).toUpperCase()}
        </span>
      )}
      <select
        data-testid="club-switcher"
        className="gx-input max-w-[220px] py-1 text-xs border-white/15 bg-black/60 font-semibold"
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

export default function AppShell() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data, isLoading } = useControlCenter();

  if (loading) return <Loading label="Opening the boardroom..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (isLoading) return <Loading label="Loading your clubs..." />;

  const role = String(user.role || "").toLowerCase();
  const accountType = String(user.account_type || user.accountType || "user").toLowerCase();
  const isAdmin = ["admin", "super_admin"].includes(role);
  const isTraderAccount = accountType === "coin_trader" || role === "coin_trader";
  const isCreatorAccount = accountType === "creator" || role === "creator";
  const isDedicatedAccount = isTraderAccount || isCreatorAccount;
  const clubs: any[] = data?.clubs || [];
  const hasClubProfile = !isDedicatedAccount && clubs.length > 0;
  const hasActiveClub =
    !isDedicatedAccount &&
    clubs.some((c: any) => ["competition", "active"].includes(c.stage));

  // Account type is a lane boundary, not a workspace preference. Trader and
  // Creator accounts cannot navigate into club-owner actions or switch personas.
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

  // Only normal member accounts enter club activation. Dedicated Creator and
  // Coin Trader accounts never inherit club onboarding from old ownership data.
  if (!isAdmin && !isDedicatedAccount && hasClubProfile && !hasActiveClub) {
    return <Navigate to="/onboarding" replace />;
  }

  const normalNav = hasActiveClub
    ? NAV
    : NAV.filter((item) =>
        ["home", "clubs", "regen-world", "awards", "market", "competitions", "national", "finance", "creator-access", "coin-traders"].includes(item.id),
      );
  const visibleNav = isTraderAccount
    ? NAV.filter((item) => ["coin-traders", "finance"].includes(item.id))
    : isCreatorAccount
      ? NAV.filter((item) =>
          ["creator-access", "newsroom", "transfers", "regen-world", "awards", "market", "competitions", "national", "finance"].includes(item.id),
        ).map((item) => item.id === "creator-access" ? { ...item, label: "Creator Studio" } : item)
      : normalNav;
  const wallet = data?.economy?.wallet || {};

  return (
    <div className="min-h-screen bg-[#070B11] text-slate-200">
      {/* Desktop Fixed Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/[0.08] bg-[#05090f] lg:flex">
        <div className="px-5 pb-5 pt-6 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded bg-emerald-500 font-display text-sm font-black text-slate-950">
              GX
            </span>
            <p className="gx-display text-2xl font-black tracking-tight text-white leading-none">
              GTEX
            </p>
          </div>
          <p className="gx-eyebrow mt-1.5 text-[9px] text-emerald-400">
            Football Management Universe
          </p>
        </div>

        <nav className="gx-scroll flex-1 space-y-0.5 overflow-y-auto px-3 py-4" data-testid="primary-nav">
          {visibleNav.map((n) => (
            <NavItem key={n.to} item={n} badge={n.id === "inbox" ? data?.inbox_open_count : 0} />
          ))}
          {isAdmin && (
            <div className="pt-3 border-t border-white/[0.06]">
              <NavItem item={{ to: "/app/admin", label: "Admin Godmode", icon: Shield, id: "admin" }} />
            </div>
          )}
        </nav>

        <div className="border-t border-white/[0.08] bg-black/40 p-4">
          <p className="truncate text-xs font-bold text-white">{user.display_name || user.username}</p>
          <p className="gx-mono text-[10px] text-slate-400">
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
            className="mt-3 flex items-center gap-2 text-xs text-slate-500 transition-colors hover:text-white"
          >
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main App Content Viewport */}
      <div className="lg:pl-64">
        {/* Sticky Top Bar */}
        <header className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-white/[0.08] bg-slate-950/85 px-4 py-3 backdrop-blur-xl sm:px-8">
          <p className="gx-display text-xl font-black text-white lg:hidden">GTEX</p>
          {!isDedicatedAccount && <ClubSwitcher />}

          <div className="ml-auto flex items-center gap-4 text-xs">
            {hasActiveClub ? (
              <span data-testid="topbar-gtex-balance" className="gx-mono text-slate-300">
                Treasury <b className="text-white font-mono">{fmt(wallet.gtex_total)}</b> <span className="text-blue-400 font-bold">GTX</span>
              </span>
            ) : (
              <span data-testid="topbar-user-account" className="gx-mono text-slate-400">
                GTEX member account · no club required
              </span>
            )}
            <span data-testid="topbar-fan-balance" className="gx-mono hidden text-slate-300 sm:inline">
              <b className="text-white font-mono">{fmt(wallet.fan_total)}</b> <span className="text-amber-400 font-bold">FAN</span>
            </span>
          </div>

          {/* Responsive Mobile Navigation Rail */}
          <nav className="gx-scroll -mx-1 flex w-full gap-1 overflow-x-auto lg:hidden pt-2 border-t border-white/[0.06]">
            {visibleNav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded px-3 py-1.5 text-xs font-bold uppercase ${
                    isActive ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "text-slate-400"
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

        {/* Screen Outlet */}
        <main className="min-h-[calc(100vh-64px)]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
