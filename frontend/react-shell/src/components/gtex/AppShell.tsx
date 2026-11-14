import React, { useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Award,
  Bell,
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
  Megaphone,
  MessagesSquare,
  Newspaper,
  Search,
  Shield,
  Shirt,
  ShoppingBag,
  Sparkles,
  Sprout,
  Swords,
  Trophy,
  User,
  Wallet,
  Video,
  Palette,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { fmt, useActiveClub, useControlCenter } from "@/lib/owner";
import { nairaText, setMoneyRates, useMoneyRates } from "@/lib/money";
import { Loading } from "@/components/gtex/ui";
import { GlobalLiveTicker } from "@/components/gtex/GlobalLiveTicker";
import { CommandPaletteModal } from "@/components/gtex/ApexWidgets";
import { NotificationBell } from "@/components/gtex/NotificationBell";
import { GtexTraxTopBarControl } from "@/components/gtex/GtexTraxPlayer";
import { GtexSponsoredMusicCard } from "@/lib/audio";
import { formatWorldDate, formatWorldTime, useWorldClock } from "@/lib/worldClock";
import { useSkin } from "@/lib/skin-engine";

const NAV = [
  // 1. HOME
  { to: "/app", label: "Control Centre", icon: Gauge, end: true, id: "home", category: "HOME" },

  // 2. MY CLUB
  { to: "/app/clubs", label: "My Clubs", icon: Building2, id: "clubs", category: "MY CLUB" },
  { to: "/app/showroom", label: "Club Prestige", icon: Sparkles, id: "showroom", category: "MY CLUB" },
  { to: "/app/campus", label: "3D Campus Builder", icon: Compass, id: "campus", category: "MY CLUB" },
  { to: "/app/story", label: "Club Story & Dynasty", icon: BookOpen, id: "story", category: "MY CLUB" },
  { to: "/app/trophies", label: "Trophy Cabinet", icon: Trophy, id: "trophies", category: "MY CLUB" },
  { to: "/app/inbox", label: "Boardroom Inbox", icon: Inbox, id: "inbox", category: "MY CLUB" },
  { to: "/app/governance", label: "Authority & Delegation", icon: Shield, id: "governance", category: "MY CLUB" },

  // 3. TRANSFERS
  { to: "/app/transfer-hub", label: "Player Transfers", icon: Compass, id: "transfers", category: "TRANSFERS" },
  { to: "/app/market?tab=club-sales", label: "Club Equity Market", icon: Building2, id: "club-sale-market", category: "TRANSFERS" },

  // 4. FOOTBALL
  { to: "/app/squad", label: "Squad & Management", icon: Shirt, id: "squad", category: "FOOTBALL" },
  { to: "/app/staff-market", label: "Staff Market", icon: User, id: "staff-market", category: "FOOTBALL" },
  { to: "/app/lineup", label: "Tactics & Lineup", icon: Swords, id: "lineup", category: "FOOTBALL" },
  { to: "/app/competitions", label: "Competitions & Tournaments", icon: Trophy, id: "competitions", category: "FOOTBALL" },
  { to: "/app/national", label: "National Teams", icon: Flag, id: "national", category: "FOOTBALL" },

  // 5. TALENT & SCOUTING
  { to: "/app/regen-world", label: "Scouting & Regen World", icon: Globe, id: "regen-world", category: "TALENT & SCOUTING" },
  { to: "/app/awards", label: "Regen Awards", icon: Award, id: "awards", category: "TALENT & SCOUTING" },
  { to: "/app/academy", label: "Youth Academy", icon: Sprout, id: "academy", category: "TALENT & SCOUTING" },
  { to: "/app/build-a-son", label: "Build-a-Son Scion", icon: Award, id: "build-a-son", category: "TALENT & SCOUTING" },

  // 6. COMMUNITY & MEDIA
  { to: "/app/community", label: "GTEX Community", icon: MessagesSquare, id: "community", category: "COMMUNITY & MEDIA" },
  { to: "/app/newsroom", label: "Football Newsroom", icon: Newspaper, id: "newsroom", category: "COMMUNITY & MEDIA" },

  // 7. WALLET & ECONOMY
  { to: "/app/finance", label: "Wallet & Finance", icon: Wallet, id: "finance", category: "WALLET & ECONOMY" },
  { to: "/app/market", label: "Player Shares Market", icon: ShoppingBag, id: "market", category: "WALLET & ECONOMY" },
  { to: "/app/jackpot", label: "Global Jackpot", icon: Flame, id: "jackpot", category: "WALLET & ECONOMY" },
  { to: "/app/coin-traders", label: "Buy & Sell GTEX Coin", icon: CandlestickChart, id: "coin-traders", category: "WALLET & ECONOMY" },

  // 8. BUSINESS
  { to: "/app/creator-access", label: "Creator Studio", icon: Video, id: "creator-access", category: "BUSINESS" },
];

function NavItem({ item, badge, compact }: any) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={item.label}
      data-testid={`nav-${item.id}`}
      className={({ isActive }) =>
        `group flex items-center ${compact ? "justify-center px-2" : "gap-3 px-3"} rounded-xl py-2 text-xs font-bold uppercase tracking-wider transition-all ${
          isActive
            ? "bg-gradient-to-r from-[#00C991]/20 to-[#00C991]/5 text-white shadow-[inset_3px_0_0_#00C991,0_4px_14px_rgba(0,0,0,0.4)] border border-[#00C991]/35"
            : "text-slate-300 hover:bg-white/[0.04] hover:text-white border border-transparent"
        }`
      }
    >
      <Icon size={15} className="shrink-0 text-[#00C991] group-hover:text-[#00E8A8] transition-colors" />
      {!compact && <span className="truncate">{item.label}</span>}
      {badge > 0 && !compact && (
        <span className="gx-mono ml-auto rounded-md bg-[#E5B63F] px-1.5 py-0.2 text-[10px] font-black text-slate-950 shadow">
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
            background: active.primary_color || "#00C991",
            color: active.secondary_color || "#080F1C",
          }}
        >
          {(active.short_name || active.club_name).slice(0, 3).toUpperCase()}
        </span>
      )}
      <select
        data-testid="club-switcher"
        className="gx-input max-w-[210px] py-1.5 text-xs border-[#25354B] bg-[#0E1A2C] font-bold rounded-xl text-slate-100"
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
      className="hidden md:flex items-center gap-2 rounded-full border border-[#42B9EC]/35 bg-[#0E1A2C] px-3 py-1 text-[11px] font-medium text-[#42B9EC] shadow-inner"
      title={`Authoritative GTEX World Clock · ${clock.isPaused ? "Paused" : "Running"}`}
    >
      <Clock size={13} className="text-[#E5B63F] shrink-0" />
      <span className="font-bold text-[#E5B63F]">
        {clock.currentSeasonLabel || `GTEX Year ${clock.gtexYearsRunning || 1}`}
      </span>
      <span className="text-white/30">·</span>
      <span className="gx-mono text-white">{formatWorldDate(clock.worldDate)}</span>
      <span className="text-white/30">·</span>
      <span className="gx-mono text-[#42B9EC]">{formatWorldTime(clock.worldTime)}</span>
    </div>
  );
}

export default function AppShell() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data, isLoading } = useControlCenter();
  const moneyRates = useMoneyRates();
  useEffect(() => {
    const economy = data?.economy;
    if (!economy) return;
    setMoneyRates({
      nairaPerGtex: Number(economy.naira_per_gtex),
      nairaPerFan: Number(economy.naira_per_fan),
      fanPerGtex: Number(economy.fan_coin_per_gtex),
    });
  }, [data]);
  const { active } = useActiveClub();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { skin, sidebarMode, dataSaver } = useSkin();
  const isCompactSidebar = sidebarMode === "compact";

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

  if (loading) return <Loading label="Entering the matchday suite..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (isLoading) return <Loading label="Loading your clubs..." />;

  const role = String(user.role || "").toLowerCase();
  const accountType = String(user.account_type || user.accountType || "user").toLowerCase();
  const isAdmin = ["admin", "super_admin"].includes(role);
  const isAdvertiserAccount = role === "advertiser" || accountType === "advertiser";
  const isTraderAccount = accountType === "coin_trader";
  const isCreatorAccount = accountType === "creator";
  const isDedicatedAccount = isTraderAccount || isCreatorAccount || isAdvertiserAccount;

  if (isAdvertiserAccount && !isAdmin) {
    return <Navigate to="/advertiser/dashboard" replace />;
  }

  const clubs: any[] = data?.clubs || [];
  const hasClubProfile = !isDedicatedAccount && clubs.length > 0;
  const hasActiveClub =
    !isDedicatedAccount &&
    clubs.some((c: any) => ["competition", "active"].includes(c.stage));

  const traderAllowed = ["/app/coin-traders", "/app/finance", "/app/community", "/app/settings/appearance", "/app/appearance"];
  const creatorAllowed = [
    "/app/creator-access",
    "/app/community",
    "/app/newsroom",
    "/app/transfer-hub",
    "/app/regen-world",
    "/app/awards",
    "/app/market",
    "/app/competitions",
    "/app/national",
    "/app/finance",
    "/app/settings/appearance",
    "/app/appearance",
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

  // Club-independent pillars stay reachable via user account without owning a club
  const userLevelRoutes = [
    "/app/clubs",
    "/app/national",
    "/app/finance",
    "/app/market",
    "/app/transfer-hub",
    "/app/regen-world",
    "/app/awards",
    "/app/newsroom",
    "/app/community",
    "/app/competitions",
    "/app/jackpot",
    "/app/creator-access",
    "/app/coin-traders",
    "/app/inbox",
    "/app/settings/appearance",
    "/app/appearance",
  ];
  if (
    !isAdmin &&
    !isDedicatedAccount &&
    hasClubProfile &&
    !hasActiveClub &&
    !routeIsAllowed(userLevelRoutes)
  ) {
    return <Navigate to="/onboarding" replace />;
  }

  const normalNav = hasActiveClub
    ? NAV
    : NAV.filter((item) =>
        [
          "home",
          "clubs",
          "showroom",
          "campus",
          "trophies",
          "jackpot",
          "regen-world",
          "awards",
          "market",
          "transfer-hub",
          "transfers",
          "competitions",
          "national",
          "newsroom",
          "community",
          "finance",
          "creator-access",
          "coin-traders",
          "appearance-studio",
          "inbox",
        ].includes(item.id)
      );

  const visibleNav = isTraderAccount
    ? NAV.filter((item) => ["coin-traders", "finance", "community", "appearance-studio"].includes(item.id))
    : isCreatorAccount
    ? NAV.filter((item) =>
        [
          "creator-access",
          "community",
          "newsroom",
          "transfers",
          "regen-world",
          "awards",
          "market",
          "competitions",
          "national",
          "finance",
          "appearance-studio",
        ].includes(item.id)
      ).map((item) => (item.id === "creator-access" ? { ...item, label: "Creator Studio" } : item))
    : normalNav;

  const wallet = data?.economy?.wallet || {};
  const clubPrimary = active?.primary_color || "#00C991";
  const clubSecondary = active?.secondary_color || "#E5B63F";

  // Group visible navigation items by mandated categories
  const categories = Array.from(new Set(visibleNav.map((n) => n.category || "HOME")));

  return (
    <div className="min-h-screen bg-[#080F1C] text-slate-100 antialiased">
      {/* Global Command Palette (Ctrl+K) */}
      <CommandPaletteModal
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        items={visibleNav}
        onNavigate={(to) => navigate(to)}
      />

      {/* Desktop Fixed Matchday Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 hidden ${isCompactSidebar ? "w-20" : "w-64"} flex-col border-r border-[#25354B] lg:flex transition-all duration-200`}
        style={{
          background: "linear-gradient(180deg, #0E1A2C 0%, #080F1C 100%)",
          boxShadow: "8px 0 32px rgba(0,0,0,0.6)",
        }}
      >
        {/* Brand Header */}
        <div className="px-5 pb-4 pt-5 border-b border-[#25354B] flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <span
                className="flex size-8 items-center justify-center rounded-xl font-display text-sm font-black text-slate-950 shadow-lg"
                style={{
                  background: "linear-gradient(135deg, #00E8A8, #00C991)",
                  boxShadow: "0 0 16px rgba(0,201,145,0.45)",
                }}
              >
                GX
              </span>
              <div className="flex flex-col">
                <p className="gx-display text-2xl font-black tracking-tight text-white leading-none">
                  GTEX
                </p>
                <span className="text-[9px] font-extrabold uppercase tracking-[0.2em] text-[#00C991] leading-tight">
                  2027 EDITION
                </span>
              </div>
            </div>
            <p className="gx-eyebrow mt-1.5 !text-[9px] text-[#42B9EC]">
              Matchday Luxury Universe
            </p>
          </div>
        </div>

        {/* Navigation Groups */}
        <nav className="gx-scroll flex-1 space-y-4 overflow-y-auto px-3 py-4" data-testid="primary-nav">
          {categories.map((cat) => (
            <div key={cat} className="space-y-1">
              <p className="px-3 text-[9px] font-extrabold uppercase tracking-[0.2em] text-[#42B9EC]/80">
                {cat}
              </p>
              {visibleNav
                .filter((n) => (n.category || "HOME") === cat)
                .map((n) => (
                  <NavItem
                    key={n.to}
                    item={n}
                    badge={n.id === "inbox" ? data?.inbox_open_count : 0}
                    compact={isCompactSidebar}
                  />
                ))}
            </div>
          ))}

          {/* Administration Pillar */}
          {isAdmin && (
            <div className="pt-3 border-t border-[#25354B] space-y-1">
              <p className="px-3 text-[9px] font-extrabold uppercase tracking-[0.2em] text-[#E5B63F]/90">
                ADMINISTRATION
              </p>
              <NavItem item={{ to: "/app/admin/advertising", label: "Advertising Review", icon: Megaphone, id: "admin-advertising" }} />
              <NavItem item={{ to: "/app/admin", label: "Admin Godmode", icon: Shield, id: "admin" }} />
            </div>
          )}
        </nav>

        {/* User Profile Bar */}
        <div className="border-t border-[#25354B] bg-[#080F1C]/90 p-4">
          <div className="flex items-center gap-2.5">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[#14243A] border border-[#25354B] text-[#00C991]">
              <User size={14} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-bold text-white">
                {user.display_name || user.username}
              </p>
              <p className="gx-mono text-[9px] text-slate-400 truncate">
                {isTraderAccount
                  ? "Coin Trader · Dedicated Lane"
                  : isCreatorAccount
                  ? "Creator · Dedicated Lane"
                  : hasActiveClub
                  ? `Integrity ${data?.integrity?.score ?? 100}/100`
                  : "Member · Club Ownership Optional"}
              </p>
            </div>
          </div>
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

      {/* Main Viewport */}
      <div className={isCompactSidebar ? "lg:pl-20 transition-all duration-200" : "lg:pl-64 transition-all duration-200"}>
        {/* Matchday Top Control Strip */}
        <header className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-[#25354B] bg-[#0E1A2C]/95 px-4 py-2.5 backdrop-blur-2xl sm:px-8 shadow-[0_8px_32px_rgba(0,0,0,0.5),inset_0_-1px_0_rgba(0,201,145,0.18)]">
          <p className="gx-display text-xl font-black text-white lg:hidden">GTEX</p>
          {!isDedicatedAccount && <ClubSwitcher />}
          <GlobalWorldClockPill />

          {/* Appearance Studio Shortcut Pill */}
          <NavLink
            to="/app/settings/appearance"
            data-testid="topbar-appearance-studio-link"
            className="hidden sm:inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/[0.04] px-2.5 py-1.5 text-xs font-semibold text-slate-300 transition hover:border-emerald-400/50 hover:text-white"
            title="Appearance Studio · Customise Skins & Views"
          >
            <Palette size={13} className="text-emerald-400" />
            <span className="hidden xl:inline">Appearance</span>
          </NavLink>

          {/* Quick Jump Search Button (Ctrl+K) */}
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="hidden xl:inline-flex items-center gap-2 rounded-xl border border-[#25354B] bg-[#14243A]/80 px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:border-[#00C991]/50 hover:text-white"
          >
            <Search size={13} className="text-[#00C991]" />
            <span>Quick Jump...</span>
            <kbd className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] font-bold text-slate-300">
              Ctrl K
            </kbd>
          </button>

          {/* Top Bar Controls & Balances */}
          <div className="ml-auto flex items-center gap-2.5 text-xs">
            <GtexTraxTopBarControl />

            {/* Notification Access */}
            <NotificationBell
              ownerUnreadCount={data?.inbox_open_count ?? 0}
              hasActiveClub={hasActiveClub}
            />

            {/* GTEX Coin Treasury Balance */}
            {hasActiveClub ? (
              <span
                data-testid="topbar-gtex-balance"
                className="gx-mono inline-flex items-center gap-2 rounded-xl border border-[#42B9EC]/40 bg-[#080F1C] px-3 py-1 text-slate-200 shadow-[0_0_14px_rgba(66,185,236,0.18),inset_0_1px_0_rgba(255,255,255,0.1)] transition hover:border-[#42B9EC]"
              >
                <span className="h-2 w-2 rounded-full bg-[#42B9EC] shadow-[0_0_8px_#42B9EC] animate-pulse" />
                <span className="text-slate-400 text-[11px] font-bold">Treasury</span>
                <b className="text-white font-mono text-xs">{fmt(wallet.gtex_total)}</b>
                <span className="text-[#42B9EC] font-black text-xs">GTX</span>
                <span className="text-[10px] text-slate-400">{nairaText(wallet.gtex_total, "GTEX")}</span>
              </span>
            ) : (
              <span data-testid="topbar-user-account" className="gx-mono text-slate-300 text-xs">
                {isTraderAccount
                  ? "Coin Trader account"
                  : isCreatorAccount
                  ? "Creator account"
                  : "Member account"}
              </span>
            )}

            {/* Fan Coin Balance */}
            <span
              data-testid="topbar-fan-balance"
              className="gx-mono hidden sm:inline-flex items-center gap-2 rounded-xl border border-[#E5B63F]/40 bg-[#080F1C] px-3 py-1 text-slate-200 shadow-[0_0_14px_rgba(229,182,63,0.18),inset_0_1px_0_rgba(255,255,255,0.1)] transition hover:border-[#E5B63F]"
            >
              <span className="h-2 w-2 rounded-full bg-[#E5B63F] shadow-[0_0_8px_#E5B63F]" />
              <b className="text-white font-mono text-xs">{fmt(wallet.fan_total)}</b>
              <span className="text-[#E5B63F] font-black text-xs">FAN</span>
              <span className="text-[10px] text-slate-400">{nairaText(wallet.fan_total, "FAN")}</span>
            </span>
            <span className="hidden xl:inline text-[10px] font-semibold text-slate-500" data-testid="coin-naira-key">
              1 GTX = ₦{fmt(moneyRates.nairaPerGtex)} · 1 FAN = ₦{fmt(moneyRates.nairaPerFan, 2)}
            </span>
          </div>

          {/* Responsive Mobile Navigation Rail */}
          <nav className="gx-scroll -mx-1 flex w-full gap-1.5 overflow-x-auto lg:hidden pt-2 border-t border-[#25354B]">
            {visibleNav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-bold uppercase ${
                    isActive
                      ? "bg-[#00C991]/20 text-[#00E8A8] border border-[#00C991]/40"
                      : "text-slate-400"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </header>

        {/* Global Matchday Live Ticker */}
        <GlobalLiveTicker />

        {/* Screen Outlet with Ambient Stadium Spotlight */}
        <main
          className="relative min-h-[calc(100vh-64px)] p-4 sm:p-6 lg:p-8"
          style={{
            background: `radial-gradient(ellipse at 25% 0%, ${clubPrimary}16 0%, ${clubSecondary}08 35%, transparent 68%)`,
          }}
        >
          <Outlet />
          {/* Global GTEX Sponsored Music Presentation (when active) */}
          <div className="fixed bottom-4 right-4 z-40 max-w-md w-full sm:w-auto pointer-events-auto px-4 sm:px-0">
            <GtexSponsoredMusicCard />
          </div>
        </main>
      </div>
    </div>
  );
}
