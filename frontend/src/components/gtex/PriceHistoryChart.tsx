import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { fmt } from "@/lib/owner";

const RANGES = ["7d", "30d", "all"] as const;

function ChartTip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-sm border border-white/10 bg-[#070B11] px-2 py-1 text-[11px]">
      <p className="gx-mono text-white">{fmt(p.price, 4)} GTX</p>
      <p className="text-slate-500">{new Date(p.at).toLocaleDateString()} · {p.kind.replace("_", " ")}</p>
    </div>
  );
}

export function PriceHistoryChart({ playerId }: { playerId: string }) {
  const [range, setRange] = useState<(typeof RANGES)[number]>("30d");
  const { data, isLoading } = useQuery({ queryKey: ["share-price-history", playerId, range], queryFn: async () => (await api.get(`/v2/players/${playerId}/shares/price-history`, { params: { range } })).data, retry: false });
  const points = (data?.points || []).map((p: any) => ({ ...p, price: Number(p.price), t: new Date(p.at).getTime() }));
  const change = Number(data?.change_pct || 0);
  const tone = change > 0 ? "text-emerald-300" : change < 0 ? "text-rose-300" : "text-slate-400";
  const stroke = change < 0 ? "#fb7185" : "#34d399";
  return (
    <div className="mt-4 border-t border-white/10 pt-3" data-testid="drawer-price-history">
      <div className="mb-2 flex items-center justify-between">
        <p className="gx-label">Price history</p>
        <div className="flex gap-1">
          {RANGES.map((r) => (
            <button key={r} type="button" data-testid={`price-history-range-${r}`} onClick={() => setRange(r)} className={`rounded-sm px-2 py-0.5 text-[10px] font-bold uppercase transition-colors ${range === r ? "bg-emerald-500/20 text-emerald-300" : "text-slate-500 hover:text-white"}`}>{r}</button>
          ))}
        </div>
      </div>
      <div className="flex items-baseline gap-2 text-xs">
        <span className={`gx-mono font-bold ${tone}`} data-testid="price-history-change">{change > 0 ? "+" : ""}{change.toFixed(2)}%</span>
        <span className="text-slate-500" data-testid="price-history-meta">{data ? `H ${fmt(data.high_price, 4)} · L ${fmt(data.low_price, 4)} · ${data.trade_count} trades` : ""}</span>
      </div>
      <div className="mt-2 h-28" data-testid="price-history-chart">
        {isLoading ? <div className="h-full animate-pulse rounded-sm bg-white/[0.03]" /> : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`ph-${playerId}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} hide />
              <YAxis domain={["auto", "auto"]} hide />
              <Tooltip content={<ChartTip />} />
              <Area type="stepAfter" dataKey="price" stroke={stroke} strokeWidth={1.5} fill={`url(#ph-${playerId})`} isAnimationActive />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
      {data && data.trade_count === 0 && <p className="mt-1 text-[11px] text-slate-500" data-testid="price-history-untraded">No trades yet. Daily closes are recorded from here on.</p>}
    </div>
  );
}
