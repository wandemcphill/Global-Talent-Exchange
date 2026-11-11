import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Activity, Coins, Lock, RefreshCw, ShieldCheck, Sliders, Trophy } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";
import { CompetitionsTab, EconomyTab, GameClockPanel, NamedCupPrizePanel, PlayersTab, QueuesTab, RailsAndTreasuryTab, UsersTab } from "./AdminControls";

function GodModeControlDesk() {
  const qc = useQueryClient();
  const { data: godMode } = useQuery({
    queryKey: ["admin-god-mode-bootstrap"],
    queryFn: async () => {
      try {
        return (await api.get("/admin/god-mode/bootstrap")).data;
      } catch {
        return null;
      }
    },
  });

  const [buyBps, setBuyBps] = useState("250");
  const [sellBps, setSellBps] = useState("250");
  const [withdrawalBps, setWithdrawalBps] = useState("150");
  const [topupPct, setTopupPct] = useState("15");
  const [reason, setReason] = useState("Scheduled GTEX treasury & ecosystem calibration");
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    if (godMode?.commissions) {
      setBuyBps(String(godMode.commissions.buy_commission_bps ?? 250));
      setSellBps(String(godMode.commissions.sell_commission_bps ?? 250));
      setWithdrawalBps(String(godMode.commissions.withdrawal_fee_bps ?? 150));
    }
    if (godMode?.competition_controls) {
      setTopupPct(String(godMode.competition_controls.prize_pool_topup_pct ?? 15));
    }
  }, [godMode]);

  const updateCommissions = async () => {
    setSaving("commissions");
    try {
      await api.put("/admin/god-mode/commissions", {
        buy_commission_bps: Number(buyBps),
        sell_commission_bps: Number(sellBps),
        instant_sell_fee_bps: Number(godMode?.commissions?.instant_sell_fee_bps ?? 500),
        withdrawal_fee_bps: Number(withdrawalBps),
        minimum_withdrawal_fee_credits: String(godMode?.commissions?.minimum_withdrawal_fee_credits ?? "10.0000"),
        reason: reason.trim() || "Commission calibration",
      });
      toast.success("Fees saved.");
      await qc.invalidateQueries({ queryKey: ["admin-god-mode-bootstrap"] });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSaving(null);
    }
  };

  const updateCompetitionTopup = async () => {
    setSaving("competition");
    try {
      await api.put("/admin/god-mode/competition-controls", {
        prize_pool_topup_pct: String(Number(topupPct || 0)),
        reason: reason.trim() || "Prize pool top-up adjustment",
      });
      toast.success("Extra prize money saved.");
      await qc.invalidateQueries({ queryKey: ["admin-god-mode-bootstrap"] });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSaving(null);
    }
  };

  const triggerSeasonAction = async (endpoint: string, labelText: string) => {
    setSaving(endpoint);
    try {
      await api.post(endpoint);
      toast.success(`${labelText} completed.`);
      await qc.invalidateQueries({ queryKey: ["leaderboard-season-current"] });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSaving(null);
    }
  };

  const td = godMode?.treasury_dashboard;
  const auditEvents: any[] = godMode?.audit_events || [];
  const rails: any[] = godMode?.payment_rails || [];

  return (
    <div className="space-y-6" data-testid="admin-godmode-section">
      {/* Treasury & Ecosystem Telemetry */}
      <Panel
        eyebrow="Money and prizes"
        title="Fees, prize money, and the season"
        testid="admin-godmode-treasury"
      >
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat
            label={Number(td?.platform_coin_balance ?? 0) < 0 ? "Coin already given out" : "Coin the platform still holds"}
            value={<Coin amount={Math.abs(Number(td?.platform_coin_balance ?? 0))} />}
            tone="good"
          />
          <Stat
            label="Player sales, total"
            value={<Coin amount={Number(td?.manager_trade_volume_credits ?? 0)} />}
          />
          <Stat
            label="Fees kept from those sales"
            value={<Coin amount={Number(td?.manager_trade_fee_revenue_credits ?? 0)} />}
            tone="good"
          />
          <Stat
            label="Sales still open / sales finished"
            value={`${fmt(td?.open_manager_listing_count ?? 0)} / ${fmt(td?.settled_manager_trade_count ?? 0)}`}
          />
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {/* Commissions Control */}
          <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-300 flex items-center gap-1.5">
                <Sliders size={14} /> Fees on buying, selling, and cashing out
              </span>
              <Chip tone="emerald">100 = 1%</Chip>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="gx-label">Buy fee</label>
                <input
                  type="number"
                  min={0}
                  max={5000}
                  className="gx-input"
                  value={buyBps}
                  onChange={(e) => setBuyBps(e.target.value)}
                  data-testid="admin-buy-bps-input"
                />
              </div>
              <div>
                <label className="gx-label">Sell fee</label>
                <input
                  type="number"
                  min={0}
                  max={5000}
                  className="gx-input"
                  value={sellBps}
                  onChange={(e) => setSellBps(e.target.value)}
                  data-testid="admin-sell-bps-input"
                />
              </div>
              <div>
                <label className="gx-label">Cash-out fee</label>
                <input
                  type="number"
                  min={0}
                  max={5000}
                  className="gx-input"
                  value={withdrawalBps}
                  onChange={(e) => setWithdrawalBps(e.target.value)}
                  data-testid="admin-withdraw-bps-input"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                className="gx-input flex-1"
                placeholder="Why you changed this"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <Btn onClick={updateCommissions} disabled={saving === "commissions"} data-testid="admin-save-commissions-btn">
                {saving === "commissions" ? "Saving…" : "Save fees"}
              </Btn>
            </div>
          </div>

          {/* Competition Prize Pool Top-Up & Season Lifecycle */}
          <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                <Trophy size={14} /> Extra prize money GTEX adds
              </span>
              <Chip tone="gold">Free to enter</Chip>
            </div>
            <p className="text-xs leading-relaxed text-slate-400">
              This is not an entry fee. Type 15 to add 15% more coin on top of a competition&apos;s prize. GTEX pays that extra. Players do not.
            </p>
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <label className="gx-label">Extra prize money (%)</label>
                <input
                  type="number"
                  min={0}
                  max={500}
                  className="gx-input"
                  value={topupPct}
                  onChange={(e) => setTopupPct(e.target.value)}
                  data-testid="admin-topup-pct-input"
                />
              </div>
              <Btn variant="gold" onClick={updateCompetitionTopup} disabled={saving === "competition"} data-testid="admin-save-topup-btn">
                {saving === "competition" ? "Saving…" : "Save extra prize money"}
              </Btn>
            </div>

            <div className="flex flex-wrap gap-2 pt-2 border-t border-white/10">
              <Btn
                variant="secondary"
                onClick={() => triggerSeasonAction("/admin/leaderboard/season/archive", "Season archive & reward distribution")}
                disabled={Boolean(saving)}
                data-testid="admin-archive-season-btn"
              >
                <RefreshCw size={13} /> Close the season and pay the prizes
              </Btn>
              <Btn
                variant="ghost"
                onClick={() => triggerSeasonAction("/admin/leaderboard/season/reset", "Leaderboard soft reset")}
                disabled={Boolean(saving)}
                data-testid="admin-reset-season-btn"
              >
                Clear the rankings, keep the history
              </Btn>
            </div>
          </div>
        </div>

        {/* Payment Rails & Audit Log */}
        {(rails.length > 0 || auditEvents.length > 0) && (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-xs space-y-2">
              <p className="font-bold uppercase tracking-wider text-slate-300">Pay-in and pay-out switches</p>
              {rails.length === 0 ? (
                <p className="text-slate-500">Bank payments are on.</p>
              ) : (
                rails.map((r: any) => (
                  <div key={r.provider} className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="font-semibold text-white uppercase">{r.provider}</span>
                    <div className="flex gap-1.5">
                      <Chip tone={r.deposits_enabled ? "emerald" : "red"}>Deposits {r.deposits_enabled ? "ON" : "OFF"}</Chip>
                      <Chip tone={r.withdrawals_enabled ? "emerald" : "red"}>Payouts {r.withdrawals_enabled ? "ON" : "OFF"}</Chip>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-xs space-y-2 max-h-44 overflow-y-auto">
              <p className="font-bold uppercase tracking-wider text-slate-300">Recent admin changes</p>
              {auditEvents.length === 0 ? (
                <p className="text-slate-500">No admin changes in this window.</p>
              ) : (
                auditEvents.slice(0, 6).map((ev: any, i: number) => (
                  <div key={ev.event_id || i} className="border-b border-white/5 pb-1.5">
                    <span className="text-emerald-300 font-semibold">{label(ev.event_type || "admin_action")}</span>
                    <span className="text-slate-400 ml-2">{ev.summary || ev.reason || ""}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}

const ADMIN_TABS = [
  { id: "overview", label: "Fees and prizes" },
  { id: "rails", label: "Bank and payouts" },
  { id: "queues", label: "Money in, ID checks, disputes" },
  { id: "players", label: "Players and photos" },
  { id: "competitions", label: "Competitions and jackpot" },
  { id: "economy", label: "Coin supply and switches" },
  { id: "users", label: "People and admin log" },
] as const;

export default function Admin() {
  const [tab, setTab] = useState<(typeof ADMIN_TABS)[number]["id"]>("overview");
  const { user } = useAuth();
  const qc = useQueryClient();
  const isAdmin = ["admin", "super_admin"].includes(String(user?.role).toLowerCase());
  const { data, isLoading } = useQuery({ queryKey: ["admin-queue"], queryFn: async () => (await api.get("/owner/admin/review-queue")).data, enabled: isAdmin });
  if (!isAdmin) return <Navigate to="/app" replace />;
  if (isLoading || !data) return <Loading />;
  const act = async (path: string, body?: any) => {
    try {
      await api.post(path, body);
      toast.success("Recorded");
      qc.invalidateQueries({ queryKey: ["admin-queue"] });
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div data-testid="admin-page" className="space-y-6">
      <PageHeader eyebrow="Admin desk" title="Run the platform" sub="Plain controls for the game clock, coin, the jackpot, and competition prizes. Entry to GTEX competitions stays free." />
      <Panel eyebrow="Start here" title="What each job actually does" testid="admin-plain-guide">
        <div className="grid gap-4 text-sm leading-relaxed text-slate-300 md:grid-cols-2">
          <div>
            <p className="font-bold text-white">The game clock is already running</p>
            <p className="mt-1">One season is about 11 weeks. The game year still has 365 game days and 12 career months. You can start the clock once. After that it cannot be paused or sped up. Matches begin when this clock reaches their kickoff. A young player ages one year when a new season opens. Real players and legends age with the human calendar.</p>
          </div>
          <div>
            <p className="font-bold text-white">How to create coin</p>
            <p className="mt-1">This page does not print coin. On the admin desk, use Give someone coin. That creates the coin and puts it in their wallet. Coin is also created when a prize or the jackpot is paid. The number on this page is coin already in wallets, or coin the platform still holds.</p>
          </div>
          <div>
            <p className="font-bold text-white">Put money in the jackpot</p>
            <p className="mt-1">Open Competitions and jackpot. Type the new pot total and press &quot;Set the pot to this amount&quot;. That moves coin from the platform into the jackpot. A smaller number moves the difference back. Players do not pay into it. &quot;Pay the jackpot now&quot; sends the current pot to the winners.</p>
          </div>
          <div>
            <p className="font-bold text-white">Set a competition and fund it</p>
            <p className="mt-1">GTEX cups are free to enter. Under this note, pick the cup and press Put this prize into this cup. That sets 1st, 2nd and 3rd and holds the coin for that cup. Extra prize money on this page is a percent added on top. It is not a ticket price.</p>
          </div>
        </div>
      </Panel>
      <GameClockPanel />
      <NamedCupPrizePanel />
      <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3" data-testid="admin-tabs">
        {ADMIN_TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            data-testid={`admin-tab-${t.id}-btn`}
            className={`rounded-sm px-3 py-1.5 text-xs font-bold transition-all ${
              tab === t.id ? "border border-emerald-500/50 bg-emerald-500/10 text-emerald-300" : "border border-transparent text-slate-400 hover:border-white/10 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "rails" && <RailsAndTreasuryTab />}
      {tab === "queues" && <QueuesTab />}
      {tab === "players" && <PlayersTab />}
      {tab === "competitions" && <CompetitionsTab />}
      {tab === "economy" && <EconomyTab />}
      {tab === "users" && <UsersTab />}
      {tab === "overview" && <>
      <GodModeControlDesk />
      <Panel eyebrow="Cash-outs waiting" title={`Withdrawals (${data.withdrawals.length})`} testid="admin-withdrawals">
        {data.withdrawals.length === 0 ? <Empty title="Queue clear" /> : data.withdrawals.map((w: any) => (
          <div key={w.id} className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 p-4" data-testid={`admin-withdrawal-${w.id}`}>
            <div>
              <p className="text-white">{fmt(w.amount_coin)} GTX (₦{fmt(w.amount_ngn)}) → {w.bank_name} ****{w.account_last4} · {w.account_name}</p>
              <div className="mt-1 flex flex-wrap gap-1">{Object.entries(w.checks?.risk || {}).map(([k, v]: any) => <Chip key={k} tone={v ? "red" : "slate"}>{label(k)}</Chip>)}<Chip tone="blue">Integrity {w.checks?.integrity_score}</Chip><Chip>{label(w.status)}</Chip></div>
            </div>
            <div className="flex gap-2">
              <Btn onClick={() => act(`/owner/admin/withdrawals/${w.id}/review`, { decision: "approve" })} data-testid={`approve-withdrawal-${w.id}`}>Approve</Btn>
              <Btn variant="secondary" onClick={() => act(`/owner/admin/withdrawals/${w.id}/review`, { decision: "hold" })} data-testid={`hold-withdrawal-${w.id}`}>Hold</Btn>
              <Btn variant="danger" onClick={() => act(`/owner/admin/withdrawals/${w.id}/review`, { decision: "reject" })} data-testid={`reject-withdrawal-${w.id}`}>Reject</Btn>
            </div>
          </div>
        ))}
      </Panel>
      <Panel eyebrow="Cheating checks" title={`Warnings (${data.flags.length})`} testid="admin-flags">
        {data.flags.length === 0 ? <Empty title="No open flags" /> : data.flags.map((f: any) => (
          <div key={f.id} className="mb-2 flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 p-3">
            <p className="text-sm text-slate-200"><Chip tone={f.severity === "high" ? "red" : "gold"}>{f.severity}</Chip> <b className="capitalize">{label(f.flag_type)}</b> · {f.detail}</p>
            <div className="flex gap-2"><Btn variant="secondary" onClick={() => act(`/owner/admin/flags/${f.id}/clear`)} data-testid={`clear-flag-${f.id}`}>Clear</Btn><Btn variant="danger" onClick={() => act(`/owner/admin/flags/${f.id}/action`)} data-testid={`action-flag-${f.id}`}>Uphold</Btn></div>
          </div>
        ))}
      </Panel>
      <Panel eyebrow="Prizes on hold" title={`Held payouts (${data.held_payouts.length})`} testid="admin-held-payouts">
        {data.held_payouts.length === 0 ? <Empty title="Nothing held" /> : data.held_payouts.map((e: any) => (
          <div key={e.id} className="mb-2 flex items-center justify-between rounded-sm border border-white/10 p-3 text-sm">
            <span>{label(e.event_type)} · {fmt(e.net_amount)} GTX · {e.memo}</span>
            <Btn onClick={() => act(`/owner/admin/payouts/${e.id}/release`)} data-testid={`release-payout-${e.id}`}>Release</Btn>
          </div>
        ))}
      </Panel>
      </>}
    </div>
  );
}
