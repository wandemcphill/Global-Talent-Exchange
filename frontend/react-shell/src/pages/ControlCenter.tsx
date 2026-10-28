import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Award,
  BookOpen,
  Building,
  CandlestickChart,
  CheckCircle2,
  Clock,
  Coins,
  Compass,
  Crown,
  DollarSign,
  ExternalLink,
  Flame,
  Gift,
  Globe2,
  Inbox,
  Newspaper,
  Radio,
  Shield,
  ShieldAlert,
  Shirt,
  Sparkles,
  Sprout,
  Swords,
  Trophy,
  Users,
  Video,
  Wallet,
  X,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub, useClub, useControlCenter, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, Panel, Stat } from "@/components/gtex/ui";
import { InboxItem } from "@/components/gtex/InboxItem";
import { WorldClockCard } from "@/components/gtex/WorldClockCard";
import { OwnerBriefingPanel } from "@/components/gtex/OwnerBriefingPanel";
import { Cinema3DStage, Cinema3DSceneType } from "@/components/gtex/Cinema3DStage";

function NoClubDashboard({ onCreateClub }: { onCreateClub: () => void }) {
  return (
    <div className="space-y-8 p-4 sm:p-8" data-testid="no-club-home">
      <section className="relative overflow-hidden rounded-3xl border border-emerald-500/25 bg-gradient-to-br from-[#061e16] via-[#09151f] to-[#040b10] p-6 sm:p-10">
        <p className="gx-eyebrow mb-3">GTEX member workspace</p>
        <h1 className="gx-display max-w-3xl text-3xl font-black uppercase leading-tight text-white sm:text-5xl">
          Your account is ready. Your football journey starts here.
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-300">
          You do not need to own a club to use GTEX. Explore the football world, follow talent, buy club shares, and manage a national team in eligible competitions with your user account.
        </p>
      </section>

      <WorldClockCard />

      <section className="grid gap-4 md:grid-cols-3" aria-label="Explore GTEX">
        <Link to="/app/national" data-testid="no-club-national-team" className="rounded-2xl border border-emerald-500/25 bg-emerald-500/[0.06] p-5 transition hover:border-emerald-400/60">
          <Trophy className="mb-4 text-emerald-300" size={22} />
          <h2 className="gx-display text-xl font-bold uppercase text-white">National team</h2>
          <p className="mt-2 text-sm leading-5 text-slate-400">Enter an eligible national competition and rent players without owning a club.</p>
          <span className="mt-5 inline-block text-xs font-bold uppercase tracking-wider text-emerald-300">Explore national duty →</span>
        </Link>
        <Link to="/app/regen-world" data-testid="no-club-regen-world" className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 transition hover:border-white/25">
          <Globe2 className="mb-4 text-cyan-300" size={22} />
          <h2 className="gx-display text-xl font-bold uppercase text-white">Regen world</h2>
          <p className="mt-2 text-sm leading-5 text-slate-400">Discover emerging talent and follow the next generation across GTEX.</p>
          <span className="mt-5 inline-block text-xs font-bold uppercase tracking-wider text-cyan-300">Explore talent →</span>
        </Link>
        <Link to="/app/market" data-testid="no-club-player-shares" className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 transition hover:border-white/25">
          <Users className="mb-4 text-amber-300" size={22} />
          <h2 className="gx-display text-xl font-bold uppercase text-white">Player shares</h2>
          <p className="mt-2 text-sm leading-5 text-slate-400">Explore available player-share opportunities and club ownership markets.</p>
          <span className="mt-5 inline-block text-xs font-bold uppercase tracking-wider text-amber-300">Explore the market →</span>
        </Link>
      </section>

      <section className="grid gap-4 md:grid-cols-2" aria-label="Optional GTEX capabilities">
        <Link to="/app/creator-access" data-testid="no-club-creator-access" className="rounded-2xl border border-pink-400/20 bg-pink-400/[0.04] p-5 transition hover:border-pink-300/50">
          <Video className="mb-4 text-pink-300" size={22} />
          <p className="gx-eyebrow text-pink-300">Creator tools</p>
          <h2 className="gx-display mt-1 text-xl font-bold uppercase text-white">Build a football audience</h2>
          <p className="mt-2 text-sm leading-5 text-slate-400">Use your existing GTEX ID to apply for creator access, publish football stories, and build a community. Creator tools do not require club ownership.</p>
          <span className="mt-5 inline-block text-xs font-bold uppercase tracking-wider text-pink-300">Apply for creator access →</span>
        </Link>
        <Link to="/app/coin-traders" data-testid="no-club-coin-traders" className="rounded-2xl border border-amber-400/20 bg-amber-400/[0.04] p-5 transition hover:border-amber-300/50">
          <CandlestickChart className="mb-4 text-amber-300" size={22} />
          <p className="gx-eyebrow text-amber-300">Coin trader tools</p>
          <h2 className="gx-display mt-1 text-xl font-bold uppercase text-white">Enter the GTEX economy</h2>
          <p className="mt-2 text-sm leading-5 text-slate-400">Buy and sell GTEX Coin with approved traders, or apply to operate a trader desk. Approval is required for liquidity-partner operations.</p>
          <span className="mt-5 inline-block text-xs font-bold uppercase tracking-wider text-amber-300">Explore Coin Traders →</span>
        </Link>
      </section>

      <Panel eyebrow="Optional next step" title="Own a club when you are ready">
        <p className="max-w-3xl text-sm leading-6 text-slate-300">
          Club ownership unlocks the club treasury, facilities, squad management, and club operations. You can start that journey now or return to it later; your GTEX user account remains useful either way.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Btn onClick={onCreateClub} data-testid="no-club-create-club">Explore club ownership</Btn>
          <Link to="/app/clubs" className="text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white">My clubs</Link>
        </div>
      </Panel>
    </div>
  );
}

export function ControlCenter() {
  const { data, isLoading, isError } = useControlCenter();
  const { active: activeClub } = useActiveClub();
  const { data: clubDetail } = useClub(activeClub?.club_id);
  const refresh = useRefreshOwner();
  const navigate = useNavigate();

  const [winBonusOpen, setWinBonusOpen] = useState(false);
  const [winBonusAmount, setWinBonusAmount] = useState("5000");
  const [winBonusNote, setWinBonusNote] = useState("Victory performance bonus for the starting squad.");
  const [pledgingBonus, setPledgingBonus] = useState(false);
  const [active3DScene, setActive3DScene] = useState<Cinema3DSceneType>("manager_arrival");

  if (isLoading) return <Loading label="Loading your GTEX workspace..." />;
  if (isError || !data) return <Empty title="GTEX workspace unavailable" body="We could not load your account right now. Please refresh and try again." />;
  if (!(data.clubs || []).length) return <NoClubDashboard onCreateClub={() => navigate("/onboarding")} />;

  const wallet = data.economy?.wallet || {};
  const activeClubProfile = data.clubs?.find((c: any) => c.club_id === activeClub?.club_id) || data.clubs?.[0] || {};
  const upcomingFixture = data.fixtures?.upcoming?.[0];
  const recentResult = data.fixtures?.recent?.[0];
  const pendingInbox = data.inbox?.filter((i: any) => !i.is_read) || [];
  const waterfall = data.ecosystem_waterfall || {};
  const tvRevenue = waterfall.club_tv_revenue_gtex ?? data.economy?.tv_revenue ?? data.economy?.broadcast_revenue ?? null;

  const staffMap = clubDetail?.staff || {};
  const executives = [
    {
      roleKey: "first_team_manager",
      roleLabel: "First-Team Manager",
      name: staffMap.first_team_manager?.name || activeClubProfile.manager?.name || "Tactical Boss",
      mood: staffMap.first_team_manager?.mood ?? activeClubProfile.manager?.mood ?? 78,
      agenda: staffMap.first_team_manager?.personal_agenda || "Win silverware & enforce high-press identity",
      secretTrait: staffMap.first_team_manager?.secret_trait || "Dressing-Room Loyalist",
      poachingRisk: staffMap.first_team_manager?.poaching_risk || "low",
      to: "/app/squad",
      tone: "emerald",
    },
    {
      roleKey: "general_manager",
      roleLabel: "General Manager (GM)",
      name: staffMap.general_manager?.name || "Commercial Director",
      mood: staffMap.general_manager?.mood ?? 82,
      agenda: staffMap.general_manager?.personal_agenda || "Maximize sponsor yield & wage-to-turnover discipline",
      secretTrait: staffMap.general_manager?.secret_trait || "Clause Architect",
      poachingRisk: staffMap.general_manager?.poaching_risk || "low",
      to: "/app/finance",
      tone: "cyan",
    },
    {
      roleKey: "head_of_youth_development",
      roleLabel: "Head of Youth Dev (HOYD)",
      name: staffMap.head_of_youth_development?.name || "Youth Director",
      mood: staffMap.head_of_youth_development?.mood ?? 85,
      agenda: staffMap.head_of_youth_development?.personal_agenda || "Fast-track academy wonderkids & Build-A-Son scions",
      secretTrait: staffMap.head_of_youth_development?.secret_trait || "Bloodline Whisperer",
      poachingRisk: staffMap.head_of_youth_development?.poaching_risk || "medium",
      to: "/app/academy",
      tone: "amber",
    },
  ];

  const handlePledgeWinBonus = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = Number(winBonusAmount);
    if (!amount || amount <= 0) {
      toast.error("Please enter a valid GTX bonus amount.");
      return;
    }
    setPledgingBonus(true);
    try {
      await api.post(`/owner/clubs/${activeClubProfile.club_id}/win-bonus`, {
        amount_gtex: amount,
        note: winBonusNote.trim() || undefined,
      });
      toast.success(`Pledged ${fmt(amount)} GTX pre-match win bonus! Squad morale boosted.`);
      setWinBonusOpen(false);
      refresh();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setPledgingBonus(false);
    }
  };

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
              to={`/club/${activeClubProfile.public_profile_slug || activeClubProfile.club_id}`}
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
              {activeClubProfile.value ? fmt(activeClubProfile.value) : fmt(activeClubProfile.cash || 0)} <span className="text-xs text-emerald-400/80">GTX</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              Trend: <b className="text-emerald-400">+{activeClubProfile.value_trend ?? "0.0"}%</b>
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

      {/* 2a. EXECUTIVE BOARDROOM TRIUMVIRATE (MANAGER, GM, HOYD) */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="executive-triumvirate-strip">
        {executives.map((exec) => (
          <Link
            key={exec.roleKey}
            to={exec.to}
            className="group rounded-2xl border border-white/10 bg-slate-900/60 p-4 transition-all hover:border-emerald-500/40 hover:bg-slate-900/90 shadow-lg space-y-2.5"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase tracking-wider text-emerald-300">
                {exec.roleLabel}
              </span>
              <div className="flex items-center gap-1.5">
                <Chip tone={exec.mood >= 70 ? "emerald" : exec.mood >= 50 ? "gold" : "red"}>
                  Mood {exec.mood}
                </Chip>
                {exec.poachingRisk === "high" && <Chip tone="red">Poach Risk</Chip>}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <h3 className="gx-display text-lg font-bold uppercase text-white group-hover:text-emerald-300">
                {exec.name}
              </h3>
              <span className="rounded bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
                {exec.secretTrait}
              </span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-2">
              <b className="text-slate-300">Agenda:</b> {exec.agenda}
            </p>
          </Link>
        ))}
      </section>

      {/* 2a-3D. INTERACTIVE 3D CEREMONIAL & BOARDROOM PRESENTATION SUITE */}
      <section className="rounded-2xl border border-amber-500/30 bg-slate-950/80 p-5 shadow-2xl space-y-4" data-testid="executive-3d-suite">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-amber-400">
              GTEX 3D CEREMONIAL & DIORAMA ENGINE · FIFA MOTION + FM 3D STILLS
            </p>
            <h3 className="gx-display text-xl font-black uppercase text-white mt-0.5">
              3D Club Presentation & Executive Stage
            </h3>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {[
              { id: "manager_arrival" as Cinema3DSceneType, label: "3D Manager Day 1" },
              { id: "signing_walkout" as Cinema3DSceneType, label: "3D Signing Walkout" },
              { id: "world_gala" as Cinema3DSceneType, label: "3D World Player Gala" },
              { id: "luxury_turntable" as Cinema3DSceneType, label: "3D Luxury Vault" },
              { id: "boardroom_clash" as Cinema3DSceneType, label: "3D Boardroom Clash" },
              { id: "club_takeover" as Cinema3DSceneType, label: "3D Takeover Keys" },
              { id: "facility_upgrade" as Cinema3DSceneType, label: "3D Stadium Upgrade" },
              { id: "competition_final" as Cinema3DSceneType, label: "3D Finals Plinth" },
              { id: "private_jet_flex" as Cinema3DSceneType, label: "3D Jet Flex" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActive3DScene(tab.id)}
                className={`rounded-lg px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider transition-all ${
                  active3DScene === tab.id
                    ? "bg-amber-400 text-slate-950 font-black shadow-md"
                    : "border border-white/10 bg-slate-900/70 text-slate-300 hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <Cinema3DStage
          scene={active3DScene}
          compact
          title={
            active3DScene === "manager_arrival"
              ? `3D First-Day Training Ground Arrival · ${executives[0].name}`
              : active3DScene === "signing_walkout"
              ? `3D Stadium Floodlight Signing Walkout · ${activeClubProfile.club_name}`
              : active3DScene === "world_gala"
              ? `3D GTEX World Player of the Year Gala · ${activeClubProfile.club_name}`
              : active3DScene === "luxury_turntable"
              ? `3D Owner Luxury Vault & Gifting Unveil · ${activeClubProfile.club_name}`
              : `3D Executive Boardroom War Room · ${executives[0].name} vs ${executives[1].name}`
          }
          subtitle={
            active3DScene === "manager_arrival"
              ? `Trait: ${executives[0].secretTrait} · Mandate: ${executives[0].agenda}`
              : active3DScene === "boardroom_clash"
              ? `Tactical Ambition vs. Commercial Wage Cap Discipline`
              : `Interactive 360° 3D Stage · Switch between FIFA Motion & FM 3D Diorama Still`
          }
          badgeText="LIVE 3D STAGE"
          clubName={activeClubProfile.club_name || "GTEX FC"}
          subjectName={
            active3DScene === "manager_arrival" || active3DScene === "boardroom_clash"
              ? executives[0].name
              : active3DScene === "luxury_turntable"
              ? "Rose-Gold Tourbillon"
              : "Marquee #9 Superstar"
          }
          subjectRole={
            active3DScene === "manager_arrival"
              ? `First-Team Manager · Mood ${executives[0].mood}`
              : active3DScene === "boardroom_clash"
              ? `Executive Alignment: ${executives[0].secretTrait}`
              : "Club Icon"
          }
          jerseyNumber={9}
          overallRating={89}
          quote="Every detail of this club's 3D identity is built for continental supremacy."
        />
      </section>

      {/* 2b. AUTHORITATIVE WORLD TIME + PERSISTED-EVENT DAILY BRIEFING */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <WorldClockCard />
        <OwnerBriefingPanel clubId={activeClubProfile.club_id} initialData={data.daily_briefing} />
      </div>

      {/* 2c. ECOSYSTEM REVENUE & PRE-MATCH WIN BONUS */}
      <section className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 shadow-xl space-y-4" data-testid="ecosystem-revenue-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Coins className="text-amber-400" size={18} />
              <h3 className="gx-display text-xl font-bold uppercase text-white">
                Ecosystem Revenue & Win Bonus Command
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              TV broadcast allocation, participation grants, prize recycling, and squad win bonus incentives.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setWinBonusOpen(true)}
            className="gx-btn gx-btn-primary text-xs flex items-center gap-2 w-fit"
            data-testid="pledge-win-bonus-btn"
          >
            <Flame size={14} className="text-amber-300" />
            <span>Pledge Win Bonus</span>
          </button>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-xl border border-white/10 bg-black/40 p-3.5">
            <p className="text-[10px] uppercase font-bold text-slate-400">TV Broadcast Rights</p>
            <p className="gx-mono text-xl font-black text-cyan-300 mt-1">
              {fmt(waterfall.club_tv_revenue_gtex ?? 0)} <span className="text-xs">GTX</span>
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Continental pool share</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/40 p-3.5">
            <p className="text-[10px] uppercase font-bold text-slate-400">Competition Grants</p>
            <p className="gx-mono text-xl font-black text-emerald-300 mt-1">
              {fmt(waterfall.club_competition_grants_gtex ?? 0)} <span className="text-xs">GTX</span>
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Participation stipend</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/40 p-3.5">
            <p className="text-[10px] uppercase font-bold text-slate-400">Prize Winnings</p>
            <p className="gx-mono text-xl font-black text-amber-300 mt-1">
              {fmt(waterfall.club_prize_winnings_gtex ?? 0)} <span className="text-xs">GTX</span>
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Matchday performance</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/40 p-3.5">
            <p className="text-[10px] uppercase font-bold text-slate-400">Matchday Gate & Misc</p>
            <p className="gx-mono text-xl font-black text-purple-300 mt-1">
              {fmt(waterfall.club_matchday_revenue_gtex ?? 0)} <span className="text-xs">GTX</span>
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Turnstile & concessions</p>
          </div>
        </div>

        {/* Recycling Waterfall Note */}
        <div className="rounded-xl border border-dashed border-emerald-500/30 bg-emerald-950/20 p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-emerald-200">
          <div className="flex items-center gap-2">
            <Sparkles size={15} className="text-emerald-400 shrink-0" />
            <span>
              Ecosystem Fee Recycling: <b>40% TV Broadcast Pool</b> · <b>35% Competition Prizes</b> · <b>25% Global Jackpot Pool</b>
            </span>
          </div>
          <Link to="/app/jackpot" className="text-emerald-300 hover:text-white font-bold uppercase underline shrink-0">
            View Jackpot Pool →
          </Link>
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
                {upcomingFixture?.round && (
                  <span className="gx-mono text-[10px] text-slate-400">
                    Round {upcomingFixture.round}
                  </span>
                )}
              </div>
              {upcomingFixture ? (
                <div className="space-y-1">
                  <p className="text-sm font-bold text-white uppercase">{upcomingFixture.home_name || activeClubProfile.club_name}</p>
                  <p className="gx-mono text-base font-black text-emerald-400">vs</p>
                  <p className="text-sm font-bold text-white uppercase">{upcomingFixture.away_name || "Opponent"}</p>
                </div>
              ) : (
                <div className="py-2 text-center">
                  <p className="text-xs font-bold text-slate-300">No Scheduled Match</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Fixtures appear once calendar draw occurs.</p>
                </div>
              )}
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
                {recentResult?.round && (
                  <span className="gx-mono text-[10px] text-slate-400">
                    Round {recentResult.round}
                  </span>
                )}
              </div>
              {recentResult ? (
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-slate-200">{recentResult.home_name || activeClubProfile.club_name}</p>
                  <p className="gx-mono text-xl font-black text-amber-300">
                    {recentResult.home_goals} - {recentResult.away_goals}
                  </p>
                  <p className="text-sm font-semibold text-slate-200">{recentResult.away_name || "Opponent"}</p>
                </div>
              ) : (
                <div className="py-2 text-center">
                  <p className="text-xs font-bold text-slate-300">No Results Recorded Yet</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Completed match reports will show here.</p>
                </div>
              )}
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
        <div className="flex items-center justify-between">
          <h3 className="gx-display text-2xl font-black uppercase text-white tracking-wide">
            Club Operations Workspaces
          </h3>
          <span className="text-xs text-slate-400">9 Integrated Executive Suites</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-3">
          {[
            { to: "/app/squad", label: "Squad Tactics", sub: "Lineup & Morale", icon: Shirt, color: "text-emerald-400" },
            { to: "/app/academy", label: "Youth & Son", sub: "Build-A-Son & HOYD", icon: Sprout, color: "text-emerald-300" },
            { to: "/app/regen-world", label: "Regen World", sub: "Bloodlines & DNA", icon: Sparkles, color: "text-amber-300" },
            { to: "/app/transfer-hub", label: "Transfer Hub", sub: "Bids & Unveilings", icon: Compass, color: "text-cyan-300" },
            { to: "/app/competitions", label: "Competitions", sub: "ELO & Leaderboards", icon: Swords, color: "text-emerald-400" },
            { to: "/app/showroom", label: "Luxury Room", sub: "Jets, Watches & Gifts", icon: Gift, color: "text-purple-300" },
            { to: "/app/jackpot", label: "Jackpot Pool", sub: "25% Fee Recycling", icon: Crown, color: "text-amber-400" },
            { to: "/app/newsroom", label: "AI Newsroom", sub: "Press & Broadcasts", icon: Newspaper, color: "text-white" },
            { to: "/app/finance", label: "Club Ledger", sub: "Sponsors & Shares", icon: Wallet, color: "text-emerald-300" },
          ].map((op) => {
            const Icon = op.icon;
            return (
              <Link
                key={op.to}
                to={op.to}
                className="group rounded-xl border border-white/10 bg-slate-900/60 p-3.5 text-center transition-all hover:-translate-y-1 hover:border-emerald-500/40 hover:bg-slate-900/90 shadow-lg"
              >
                <Icon size={20} className={`mx-auto mb-1.5 ${op.color} transition-transform group-hover:scale-110`} />
                <p className="gx-display text-xs font-bold uppercase text-white group-hover:text-emerald-300 transition-colors">
                  {op.label}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5 truncate">{op.sub}</p>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Pledge Win Bonus Modal */}
      {winBonusOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" data-testid="win-bonus-modal">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#070B11] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Flame className="text-amber-400" size={18} />
                <h3 className="gx-display text-lg font-black uppercase text-white">Pledge Match Win Bonus</h3>
              </div>
              <button onClick={() => setWinBonusOpen(false)} className="text-slate-400 hover:text-white"><X size={16} /></button>
            </div>
            <form onSubmit={handlePledgeWinBonus} className="space-y-4">
              <p className="text-xs text-slate-300 leading-relaxed">
                Pledging a matchday victory bonus motivates the squad, elevates morale (+8 to +15), and sharpens coach tactical commitment for the next fixture.
              </p>
              <div>
                <label className="gx-label">Bonus Amount (GTX)</label>
                <input
                  type="number"
                  min="1000"
                  step="500"
                  value={winBonusAmount}
                  onChange={(e) => setWinBonusAmount(e.target.value)}
                  className="gx-input w-full mt-1"
                  required
                />
              </div>
              <div>
                <label className="gx-label">Locker Room Note / Owner Speech</label>
                <input
                  type="text"
                  value={winBonusNote}
                  onChange={(e) => setWinBonusNote(e.target.value)}
                  className="gx-input w-full mt-1"
                  placeholder="Victory incentive statement..."
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setWinBonusOpen(false)}
                  className="gx-btn gx-btn-secondary flex-1 text-xs"
                  disabled={pledgingBonus}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="gx-btn gx-btn-primary flex-1 text-xs"
                  disabled={pledgingBonus}
                >
                  {pledgingBonus ? "Pledging…" : "Confirm Win Bonus"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
export default ControlCenter;
