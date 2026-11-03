import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeftRight,
  Building2,
  DollarSign,
  Info,
  ShieldAlert,
  ShoppingBag,
  TrendingUp,
  Users,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, PageHeader, Panel } from "@/components/gtex/ui";
import { MarketTable } from "@/components/gtex/MarketTable";
import { ShareMarket } from "@/components/gtex/ShareMarket";
import { ClubSaleMarket } from "@/components/gtex/ClubSaleMarket";

function SisterTransfer({ clubs, club }: any) {
  const refresh = useRefreshOwner();
  const [playerId, setPlayerId] = useState("");
  const [to, setTo] = useState("");
  const [fee, setFee] = useState("");
  const [check, setCheck] = useState<any>(null);
  const body = () => ({ player_id: playerId, to_club_id: to, fee: Number(fee || 0) });
  const runCheck = async () => {
    try {
      setCheck((await api.post("/owner/transfers/internal/check", body())).data);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const execute = async () => {
    try {
      const { data } = await api.post("/owner/transfers/internal", body());
      toast.success(`Transfer complete. ${data.notes.join(" ")}`);
      setCheck(null);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const sisters = clubs.filter((c: any) => c.club_id !== club?.club_id);
  if (!sisters.length) {
    return (
      <p className="text-sm text-slate-400">
        Own a second club to move players between sister clubs. Related-party rules apply: no free transfers, fee within 80–130% of fair value, 14-day reciprocal cooldown, and repeated shuffling is flagged.
      </p>
    );
  }
  return (
    <div className="grid gap-4 md:grid-cols-4" data-testid="sister-transfer-form">
      <select
        data-testid="sister-player-select"
        className="gx-input md:col-span-2"
        value={playerId}
        onChange={(e) => {
          setPlayerId(e.target.value);
          setCheck(null);
        }}
      >
        <option value="">Select player from {club?.club_name}</option>
        {(club?.squad || []).map((p: any) => (
          <option key={p.id} value={p.id}>
            {p.name} · value {fmt(p.value_coin)}
          </option>
        ))}
      </select>
      <select
        data-testid="sister-target-select"
        className="gx-input"
        value={to}
        onChange={(e) => {
          setTo(e.target.value);
          setCheck(null);
        }}
      >
        <option value="">To club</option>
        {sisters.map((s: any) => (
          <option key={s.club_id} value={s.club_id}>
            {s.club_name}
          </option>
        ))}
      </select>
      <input
        data-testid="sister-fee-input"
        className="gx-input"
        placeholder="Fee (GTX)"
        value={fee}
        onChange={(e) => {
          setFee(e.target.value);
          setCheck(null);
        }}
      />
      <div className="flex gap-2 md:col-span-4">
        <Btn variant="secondary" disabled={!playerId || !to} onClick={runCheck} data-testid="sister-check-button">
          Check fair-value rules
        </Btn>
        <Btn disabled={!check?.allowed} onClick={execute} data-testid="sister-execute-button">
          Execute transfer
        </Btn>
      </div>
      {check && (
        <div className="md:col-span-4 rounded-xl border border-[#25354B] bg-[#0E1A2C] p-4 text-sm" data-testid="sister-check-result">
          <p className="mb-2 text-slate-200">
            Fair value {fmt(check.fair_value)} · allowed band {fmt(check.band[0])}–{fmt(check.band[1])}
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(check.rules).map(([k, v]: any) => (
              <Chip key={k} tone={v ? "emerald" : "red"}>
                {k.replace(/_/g, " ")}
              </Chip>
            ))}
          </div>
          {check.shuffle_flag_risk && (
            <p className="mt-2 text-[#E5B63F]">
              Warning: this would be a repeated related-party move. It will be flagged and the player's morale will drop.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function Market() {
  const [params] = useSearchParams();
  const { clubs, active } = useActiveClub();
  const { data: club, refetch } = useClub(active?.club_id);
  const position = params.get("position") || "";
  const tabParam = params.get("tab");
  const [activeTab, setActiveTab] = useState<"transfers" | "shares" | "sister" | "club-sales">(
    tabParam === "club-sales" ? "club-sales" : "transfers"
  );

  return (
    <div data-testid="market-page" className="space-y-6">
      <PageHeader
        eyebrow="Marketplace & Player Transfers"
        title="Squad Signings & Share Trading"
        sub={`Managing acquisitions for ${active?.club_name || "GTEX Universe"}. Direct signings register players onto your team sheet; Player Shares represent fractional investment stakes.`}
        action={
          <div className="flex items-center gap-2">
            <Link
              to="/app/transfer-hub"
              className="gx-btn gx-btn-primary flex items-center gap-1.5"
            >
              <ArrowLeftRight size={14} /> Official Transfer Hub
            </Link>
          </div>
        }
      />

      {/* Distinction Callout Banner */}
      <div className="rounded-2xl border border-[#42B9EC]/30 bg-gradient-to-r from-[#0E1A2C] via-[#14243A] to-[#080F1C] p-4 shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[#42B9EC]/15 border border-[#42B9EC]/30 text-[#42B9EC]">
            <Info size={18} />
          </div>
          <div className="text-xs">
            <span className="font-bold text-white uppercase tracking-wider">Direct Player Signings vs Investment Shares</span>
            <p className="text-slate-300 mt-0.5">
              Direct transfers register the athlete to your club roster using club cash. Player Shares are tradable liquid shares that pay dividends.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Club Cash:</span>
          <span className="gx-mono font-bold text-[#00E8A8]">{fmt(club?.economy?.cash_gtex)} GTX</span>
        </div>
      </div>

      {position && <Chip tone="cyan" testid="manager-request-filter">Manager request: {position}</Chip>}

      {/* Navigation Sub-Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-[#25354B] pb-3">
        {[
          { id: "transfers", label: "Buy Players", icon: ArrowLeftRight },
          { id: "shares", label: "Player Shares", icon: ShoppingBag },
          { id: "club-sales", label: "Club Sale Market", icon: Building2 },
          { id: "sister", label: "Sister-Club Transfers", icon: Users },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all ${
                isActive
                  ? "bg-[#00C991] text-slate-950 font-black shadow-[0_0_14px_rgba(0,201,145,0.4)]"
                  : "border border-[#25354B] bg-[#14243A]/80 text-slate-300 hover:border-[#00C991]/50 hover:text-white"
              }`}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Panel 1: World Market / Direct Player Acquisition */}
      <div className={activeTab === "transfers" ? "block" : "hidden"}>
        <Panel eyebrow="World market · live player universe" title="Available players" testid="world-market-panel">
          <MarketTable
            clubId={active?.club_id}
            initialPosition={position}
            signedRefs={(club?.squad || []).map((p: any) => p.player_ref)}
            onSigned={() => refetch()}
            clubCash={club?.economy?.cash_gtex}
          />
        </Panel>
      </div>

      {/* Panel 2: Player Shares */}
      <div className={activeTab === "shares" ? "block" : "hidden"}>
        <Panel eyebrow="Player catalogue · live" title="Available players" testid="share-market-panel">
          <ShareMarket />
        </Panel>
      </div>

      {/* Panel 3: Sister-Club Transfers */}
      <div className={activeTab === "sister" ? "block" : "hidden"}>
        <Panel eyebrow="Related-party · anti-collusion" title="Sister-club transfer" testid="sister-transfer-panel">
          <SisterTransfer clubs={clubs} club={club} />
        </Panel>
      </div>

      {/* Panel 4: Club Sale & Acquisition Market */}
      <div className={activeTab === "club-sales" ? "block" : "hidden"}>
        <Panel eyebrow="Club equity market · verified ownership" title="Club Sale & Acquisition Market" testid="club-sale-market-panel">
          <ClubSaleMarket />
        </Panel>
      </div>
    </div>
  );
}
