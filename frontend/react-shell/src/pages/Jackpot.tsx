import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Coins, Flame, Sparkles, Trophy, Tv, Users, Zap } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";

export default function Jackpot() {
  const qc = useQueryClient();
  const [contribution, setContribution] = useState("250");
  const [submitting, setSubmitting] = useState(false);

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["jackpot-status"],
    queryFn: async () => {
      try {
        return (await api.get("/jackpot/status")).data;
      } catch {
        return null;
      }
    },
  });

  const { data: history = [] } = useQuery({
    queryKey: ["jackpot-history"],
    queryFn: async () => {
      try {
        const res = await api.get("/jackpot/history");
        return Array.isArray(res.data) ? res.data : res.data?.items || res.data?.rounds || [];
      } catch {
        return [];
      }
    },
  });

  const { data: waterfall } = useQuery({
    queryKey: ["economy-waterfall"],
    queryFn: async () => {
      try {
        return (await api.get("/owner/economy/waterfall")).data;
      } catch {
        return null;
      }
    },
  });

  const contribute = async () => {
    const amount = Number(contribution || 0);
    if (!amount || amount <= 0) {
      toast.error("Enter a valid GTEX Coin contribution amount.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/jackpot/contribute", {
        amount: String(amount),
        source_type: "owner_console_contribution",
        source_id: `manual-${Date.now()}`,
      });
      toast.success(`Contributed ${fmt(amount)} GTX into the Global Jackpot Pool!`);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["jackpot-status"] }),
        qc.invalidateQueries({ queryKey: ["jackpot-history"] }),
        qc.invalidateQueries({ queryKey: ["economy-waterfall"] }),
      ]);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (statusLoading && !waterfall) {
    return <Loading label="Loading GTEX Global Jackpot & Ecosystem Pool" />;
  }

  const jackpotBalance = Number(
    status?.current_balance ?? waterfall?.jackpot_ecosystem_pool_gtex ?? 25000
  );
  const thresholdAmount = Number(status?.threshold_amount ?? 100000);
  const progressPct = Math.min(100, Math.round((jackpotBalance / Math.max(1, thresholdAmount)) * 100));
  const roundNumber = status?.round_number ?? 1;
  const distributionMode = status?.distribution_mode ?? "top_split";

  return (
    <div className="space-y-6" data-testid="jackpot-page">
      <PageHeader
        eyebrow="GTEX Real Economy · Revenue Recycling"
        title="Global Jackpot & Ecosystem Hub"
        sub="Platform fees from player sales, regen transfers, and gifting rakes are poured directly back into the GTEX hub: 40% TV Broadcast Rights, 35% Competition Prize Pools, and 25% into the Global Jackpot."
      />

      <div className="grid gap-6 lg:grid-cols-12">
        <Panel
          eyebrow={`Round #${roundNumber} · ${label(distributionMode)}`}
          title="Live GTEX Jackpot Pool"
          testid="jackpot-live-pool-panel"
          className="lg:col-span-8"
        >
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat
              label="Current Jackpot Pool"
              value={<Coin amount={jackpotBalance} />}
              tone="good"
              testid="jackpot-current-balance"
            />
            <Stat
              label="Trigger Threshold"
              value={<Coin amount={thresholdAmount} />}
              testid="jackpot-threshold"
            />
            <Stat
              label="Recycled from Platform Fees (25%)"
              value={<Coin amount={waterfall?.jackpot_ecosystem_pool_gtex ?? jackpotBalance} />}
              testid="jackpot-recycled-share"
            />
          </div>

          <div className="mt-6">
            <div className="flex items-center justify-between text-xs text-slate-300 mb-2">
              <span className="flex items-center gap-1.5 font-semibold text-amber-300">
                <Flame size={14} /> Progress to Next Jackpot Trigger
              </span>
              <span className="gx-mono font-bold">{progressPct}%</span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800 border border-white/10">
              <div
                className="h-full bg-gradient-to-r from-amber-500 via-emerald-400 to-cyan-400 transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-400">
              Every transfer, regen sale, competition entry, and fan gift feeds the global jackpot automatically.
            </p>
          </div>
        </Panel>

        <Panel
          eyebrow="Participate & Boost"
          title="Enter / Boost Jackpot Pool"
          testid="jackpot-contribute-panel"
          className="lg:col-span-4"
        >
          <p className="text-xs text-slate-300 mb-3">
            Club owners can directly boost the active round to accelerate the threshold trigger and register participation weight.
          </p>
          <label className="gx-label">Contribution Amount (GTX)</label>
          <input
            type="number"
            min={10}
            value={contribution}
            onChange={(e) => setContribution(e.target.value)}
            className="gx-input mt-1"
            data-testid="jackpot-contribute-input"
          />
          <Btn
            variant="gold"
            className="mt-4 w-full"
            disabled={submitting}
            onClick={contribute}
            data-testid="jackpot-contribute-button"
          >
            <Zap size={14} className="mr-1.5 inline" />
            {submitting ? "Contributing..." : `Contribute ${fmt(Number(contribution || 0))} GTX`}
          </Btn>
        </Panel>

        <Panel
          eyebrow="Ecosystem Waterfall · Giving Back to Club Owners"
          title="Where Platform Revenue Goes"
          testid="jackpot-ecosystem-waterfall-panel"
          className="lg:col-span-12"
        >
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-white/10 bg-black/40 p-4">
              <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-400">
                <Coins size={14} className="text-slate-300" /> Total Fees Collected
              </div>
              <p className="gx-mono text-2xl font-black text-white mt-2">
                {fmt(waterfall?.total_platform_fees_gtex ?? 0)} <span className="text-xs text-blue-400">GTX</span>
              </p>
              <p className="text-xs text-slate-500 mt-1">From transfers, regen sales & gifting rakes</p>
            </div>

            <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/15 p-4">
              <div className="flex items-center gap-2 text-xs font-bold uppercase text-cyan-300">
                <Tv size={14} /> 40% TV & Broadcast Pool
              </div>
              <p className="gx-mono text-2xl font-black text-cyan-200 mt-2">
                {fmt(waterfall?.tv_broadcast_pool_gtex ?? 0)} <span className="text-xs">GTX</span>
              </p>
              <p className="text-xs text-slate-400 mt-1">Paid to clubs on every completed matchday</p>
            </div>

            <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/15 p-4">
              <div className="flex items-center gap-2 text-xs font-bold uppercase text-emerald-300">
                <Trophy size={14} /> 35% Competition Grants & Prizes
              </div>
              <p className="gx-mono text-2xl font-black text-emerald-200 mt-2">
                {fmt(waterfall?.competition_prize_pool_gtex ?? 0)} <span className="text-xs">GTX</span>
              </p>
              <p className="text-xs text-slate-400 mt-1">Entry grants + matchday win & placement prizes</p>
            </div>

            <div className="rounded-xl border border-amber-500/20 bg-amber-950/15 p-4">
              <div className="flex items-center gap-2 text-xs font-bold uppercase text-amber-300">
                <Sparkles size={14} /> 25% Global Jackpot Pool
              </div>
              <p className="gx-mono text-2xl font-black text-amber-200 mt-2">
                {fmt(waterfall?.jackpot_ecosystem_pool_gtex ?? jackpotBalance)} <span className="text-xs">GTX</span>
              </p>
              <p className="text-xs text-slate-400 mt-1">Triggered when pool crosses threshold</p>
            </div>
          </div>
        </Panel>

        <Panel
          eyebrow="Verified Payout Ledger"
          title="Recent Jackpot Rounds & Settlements"
          testid="jackpot-history-panel"
          className="lg:col-span-12"
        >
          {history.length === 0 ? (
            <Empty
              title="Round #1 is currently building"
              sub="Once the jackpot pool crosses the trigger threshold, verified winner payouts appear here."
            />
          ) : (
            <div className="space-y-3">
              {history.map((round: any, idx: number) => (
                <div
                  key={round.id || idx}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-black/30 p-3.5 text-sm"
                >
                  <div>
                    <p className="font-bold text-white">
                      Round #{round.round_number ?? idx + 1} · <Coin amount={round.balance_at_trigger ?? round.current_balance ?? 0} />
                    </p>
                    <p className="text-xs text-slate-400">
                      Trigger: {label(round.trigger_reason || round.status || "threshold")}
                    </p>
                  </div>
                  <Chip tone={round.status === "settled" ? "emerald" : "gold"}>
                    {label(round.status || "open")}
                  </Chip>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
