import React, { useState } from "react";
import { createPortal } from "react-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { X } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Loading, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PriceHistoryChart } from "@/components/gtex/PriceHistoryChart";

function ShareBox({ playerId }: { playerId: string }) {
  const [count, setCount] = useState("1");
  const qc = useQueryClient();
  const { data, refetch, isError } = useQuery({ queryKey: ["share-market", playerId], queryFn: async () => (await api.get(`/v2/players/${playerId}/shares/market`)).data, retry: false });
  if (isError) return <p className="text-xs text-slate-500" data-testid="drawer-no-share-market">No share market issued for this player yet.</p>;
  if (!data) return null;
  const buy = async () => {
    try {
      const { data: res } = await api.post(`/v2/players/${playerId}/shares/buy`, { share_count: Number(count) });
      toast.success(`Bought ${count} shares · ${fmt(res.gross_amount_coin, 4)} GTX`);
      refetch();
      qc.invalidateQueries({ queryKey: ["share-price-history", playerId] });
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div className="rounded-sm border border-white/10 p-4" data-testid="drawer-share-market">
      <p className="gx-eyebrow mb-2">Player share market</p>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div><p className="gx-label">Price</p><p className="gx-mono text-white">{fmt(data.share_price_coin, 4)}</p></div>
        <div><p className="gx-label">Circulating</p><p className="gx-mono text-white">{data.circulating_shares}/{data.total_shares}</p></div>
        <div><p className="gx-label">Liquidity</p><p className="gx-mono text-white">{fmt(data.liquidity_coin, 2)}</p></div>
      </div>
      <div className="mt-3 flex gap-2">
        <input data-testid="drawer-share-count" className="gx-input w-24" value={count} onChange={(e) => setCount(e.target.value.replace(/\D/g, ""))} />
        <Btn onClick={buy} disabled={!Number(count)} data-testid="drawer-buy-shares">Buy shares</Btn>
      </div>
      <PriceHistoryChart playerId={playerId} />
    </div>
  );
}

function RegenDossier({ playerId }: { playerId: string }) {
  const { data: m, isLoading } = useQuery({ queryKey: ["market-player", playerId], queryFn: async () => (await api.get(`/market/players/${playerId}`)).data });
  if (isLoading || !m) return <Loading label="Pulling the academy file" />;
  const id = m.identity || {};
  const a = m.attributes || {};
  return (
    <div className="space-y-5" data-testid="drawer-regen-dossier">
      <div className="mx-auto max-w-[240px]">
        <PlayerCard testid="drawer-regen-card" name={id.player_name} rating={a.overall} potential={a.potential} position={id.normalized_position || id.position} age={id.age} nationality={id.nationality} club={id.current_club_name} image={id.image_url} regen
          badge={a.potential - a.overall >= 15 ? "Wonderkid" : "Regen"} stats={[{ k: "Ceiling", v: `+${Math.max(0, (a.potential || 0) - (a.overall || 0))}` }, { k: "Nation", v: id.nationality_code || "-" }, { k: "Age", v: id.age ?? "-" }]} />
      </div>
      <div className="flex flex-wrap gap-2"><Chip tone="emerald">Pre-seeded national regen</Chip>{id.position && <Chip tone="cyan">{id.position}</Chip>}</div>
      <div className="space-y-2.5" data-testid="drawer-regen-attributes">
        {["pace", "shooting", "passing", "dribbling", "defending", "physical"].map((k) => <TraitBar key={k} label={label(k)} value={a[k] ?? 0} max={99} />)}
      </div>
      <ShareBox playerId={playerId} />
    </div>
  );
}

export function PlayerDrawer({ playerId, onClose, extra }: { playerId: string | null; onClose: () => void; extra?: React.ReactNode }) {
  const { data: p, isLoading, isError } = useQuery({ queryKey: ["real-player", playerId], queryFn: async () => (await api.get(`/v2/players/real-universe/${playerId}`)).data, enabled: !!playerId, retry: false });
  const { data: form } = useQuery({ queryKey: ["player-form", playerId], queryFn: async () => (await api.get(`/v2/players/${playerId}/form`, { params: { include_performances: false } })).data, enabled: !!playerId });
  const { data: quote } = useQuery({ queryKey: ["player-quote", playerId], queryFn: async () => (await api.get("/owner/market/quote", { params: { player_ids: playerId } })).data.quotes[playerId as string], enabled: !!playerId });
  if (!playerId) return null;
  const signals = p?.normalized_signals || {};
  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm" onClick={onClose} data-testid="player-drawer">
      <aside className="gx-scroll h-full w-full max-w-md overflow-y-auto border-l border-white/10 bg-[#070B11] p-6" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <p className="gx-eyebrow">Scouting report</p>
          <button onClick={onClose} data-testid="player-drawer-close" className="text-slate-400 transition-colors hover:text-white"><X size={18} /></button>
        </div>
        {isError ? <RegenDossier playerId={playerId} /> : isLoading || !p ? <Loading label="Pulling the dossier" /> : (
          <div className="space-y-5">
            <div className="mx-auto max-w-[240px]">
              <PlayerCard name={p.player_name} rating={quote?.rating} position={p.position} age={p.age} nationality={p.nationality} club={p.current_club_name} image={p.image_url}
                stats={[{ k: "Fee", v: fmt(quote?.price) }, { k: "Value", v: fmt(p.current_value_credits, 1) }, { k: "Interest", v: p.market_interest_score ?? "-" }]} />
            </div>
            <div className="flex flex-wrap gap-2">
              <Chip tone="cyan">{p.primary_position || p.position}</Chip>
              {p.current_league_name && <Chip>{p.current_league_name}</Chip>}
              {p.real_player_tier && <Chip tone="gold">{label(p.real_player_tier)}</Chip>}
              {p.lifecycle_status_label && <Chip tone="emerald">{p.lifecycle_status_label}</Chip>}
              {p.height_cm && <Chip>{p.height_cm} cm</Chip>}
            </div>
            <div className="space-y-2.5" data-testid="drawer-signals">
              {Object.entries(signals).map(([k, v]: any) => <TraitBar key={k} label={label(k.replace(/_(score|signal)$/, ""))} value={Math.round(Number(v))} max={100} />)}
            </div>
            <div className="rounded-sm border border-white/10 p-4 text-sm" data-testid="drawer-form">
              <p className="gx-eyebrow mb-2">GTEX form</p>
              {form?.has_sample ? <p className="text-slate-300">Avg rating {form.average_rating} · {form.matches_counted} matches · trend {form.trend}</p> : <p className="text-slate-500">No GTEX competition minutes yet. Form builds once he plays.</p>}
            </div>
            <ShareBox playerId={playerId} />
            {extra}
          </div>
        )}
      </aside>
    </div>,
    document.body,
  );
}
