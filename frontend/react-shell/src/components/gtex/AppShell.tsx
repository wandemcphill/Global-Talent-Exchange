import React from "react";
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { Building2, Flag, Gauge, Inbox, LogOut, Shield, Shirt, ShoppingBag, Sprout, Trophy, Wallet } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { fmt, useActiveClub, useControlCenter } from "@/lib/owner";
import { Loading } from "@/components/gtex/ui";

const NAV = [
  { to: "/app", label: "Control Center", icon: Gauge, end: true, id: "home" },
  { to: "/app/clubs", label: "My Clubs", icon: Building2, id: "clubs" },
  { to: "/app/market", label: "Market & Transfers", icon: ShoppingBag, id: "market" },
  { to: "/app/competitions", label: "Competitions", icon: Trophy, id: "competitions" },
  { to: "/app/squad", label: "Manager & Squad", icon: Shirt, id: "squad" },
  { to: "/app/academy", label: "Academy / Regens", icon: Sprout, id: "academy" },
  { to: "/app/national", label: "National Team", icon: Flag, id: "national" },
  { to: "/app/finance", label: "Finance", icon: Wallet, id: "finance" },
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
        `group flex items-center gap-3 rounded-sm px-3 py-2.5 text-[13px] font-medium transition-colors ${isActive ? "bg-emerald-500/10 text-white shadow-[inset_2px_0_0_#10B981]" : "text-slate-400 hover:bg-white/[0.04] hover:text-white"}`
      }
    >
      <Icon size={16} className="shrink-0" />
      <span className="truncate">{item.label}</span>
      {badge > 0 && <span className="gx-mono ml-auto rounded-sm bg-amber-500 px-1.5 text-[10px] font-bold text-slate-950">{badge}</span>}
    </NavLink>
  );
}

function ClubSwitcher() {
  const { clubs, active, select } = useActiveClub();
  if (!clubs.length) return null;
  return (
    <select data-testid="club-switcher" className="gx-input max-w-[220px] py-1.5 text-xs" value={active?.club_id} onChange={(e) => select(e.target.value)}>
      {clubs.map((c) => (
        <option key={c.club_id} value={c.club_id}>
          {c.club_name}
        </option>
      ))}
    </select>
  );
}

export default function AppShell() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const { data, isLoading } = useControlCenter();
  if (loading) return <Loading label="Opening the boardroom" />;
  if (!user) return <Navigate to="/login" replace />;
  if (isLoading) return <Loading label="Loading your clubs" />;
  const isAdmin = ["admin", "super_admin"].includes(String(user.role).toLowerCase());
  if (!isAdmin && data && !data.clubs.some((c: any) => ["competition", "active"].includes(c.stage))) return <Navigate to="/onboarding" replace />;
  const wallet = data?.economy?.wallet || {};
  return (
    <div className="min-h-screen bg-[#070B11] text-slate-200">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-white/[0.06] bg-[#070B11] lg:flex">
        <div className="px-5 pb-6 pt-6">
          <p className="gx-display text-3xl font-black tracking-tight text-white">GTEX</p>
          <p className="gx-eyebrow mt-1 text-[9px]">Owner Console · NG</p>
        </div>
        <nav className="flex-1 space-y-0.5 px-3" data-testid="primary-nav">
          {NAV.map((n) => (
            <NavItem key={n.to} item={n} badge={n.id === "inbox" ? data?.inbox_open_count : 0} />
          ))}
          {isAdmin && <NavItem item={{ to: "/app/admin", label: "Admin Review", icon: Shield, id: "admin" }} />}
        </nav>
        <div className="border-t border-white/[0.06] p-4">
          <p className="truncate text-sm text-white">{user.display_name || user.username}</p>
          <p className="gx-mono text-[10px] text-slate-500">Integrity {data?.integrity?.score ?? 100}/100</p>
          <button data-testid="logout-button" onClick={() => { logout(); navigate("/"); }} className="mt-3 flex items-center gap-2 text-xs text-slate-500 transition-colors hover:text-white">
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-white/[0.06] bg-slate-950/80 px-4 py-3 backdrop-blur-xl sm:px-8">
          <p className="gx-display text-xl font-black text-white lg:hidden">GTEX</p>
          <ClubSwitcher />
          <div className="ml-auto flex items-center gap-4 text-xs">
            <span data-testid="topbar-gtex-balance" className="gx-mono text-slate-300">
              Wallet <b className="text-white">{fmt(wallet.gtex_total)}</b> <span className="text-blue-400">GTX</span>
            </span>
            <span data-testid="topbar-fan-balance" className="gx-mono hidden text-slate-300 sm:inline">
              <b className="text-white">{fmt(wallet.fan_total)}</b> <span className="text-amber-400">FAN</span>
            </span>
          </div>
          <nav className="gx-scroll -mx-1 flex w-full gap-1 overflow-x-auto lg:hidden">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `whitespace-nowrap rounded-sm px-3 py-1.5 text-xs ${isActive ? "bg-emerald-500/15 text-white" : "text-slate-400"}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="mx-auto max-w-[1400px] px-4 py-8 sm:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
