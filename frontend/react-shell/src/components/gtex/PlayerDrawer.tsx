import React from "react";
import { createPortal } from "react-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { X } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Loading, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";

function PlayerAcquisition({ playerId }: { playerId: string }) {
  const qc = useQueryClient();
  const { data: market, isError } = useQuery({
    queryKey: ["player-acquisition", playerId],
    queryFn: async () => (await api.get(`/v2/players/${playerId}/shares/market`)).data,
    retry: false,
  });
  const { data: holdings = [] } = useQuery({
    queryKey: ["my-player-acquisitions"],
    queryFn: async () => (await api.get("/v2/players/me/shares/holdings")).data,
    retry: false,
  });
  if (isError) return <p className="text-xs text-slate-500" data-testid="drawer-no-acquisition">This player is not currently available to acquire.</p>;
  if (!market) return null;

  const owned = Array.isArray(holdings) && holdings.some((holding: any) =>
    holding.player_id === playerId && Number(holding.share_count) > 0
  );
  const available = Math.max(0, Number(market.released_shares ?? market.total_shares) - Number(market.circulating_shares || 0));
  const buy = async () => {
    if (owned || available < 1) return;
    try {
      const { data: result } = await api.post(`/v2/players/${playerId}/shares/buy`, { share_count: 1 });
      toast.success(`Player acquired · ${fmt(result.net_amount_coin ?? result.gross_amount_coin, 2)} GTX`);
      await qc.invalidateQueries({ queryKey: ["player-acquisition", playerId] });
      await qc.invalidateQueries({ queryKey: ["my-player-acquisitions"] });
    } catch (error) {
      toast.error(errMsg(error));
      await qc.invalidateQueries({ queryKey: ["my-player-acquisitions"] });
    }
  };

  return (
    <div className="rounded-sm border border-white/10 p-4" data-testid="drawer-player-acquisition">
      <p className="gx-eyebrow mb-2">Player acquisition</p>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><p className="gx-label">Acquisition price</p><p className="gx-mono text-white">{fmt(market.share_price_coin, 2)} GTX</p></div>
        <div><p className="gx-label">Units available</p><p className="gx-mono text-white">{available}</p></div>
      </div>
      <p className="mt-3 text-xs text-slate-400">Each account may acquire one complete unit of this player. Units cannot be resold or traded.</p>
      <div className="mt-3">
        <Btn onClick={buy} disabled={owned || available < 1} data-testid="drawer-acquire-player">
          {owned ? "Already acquired" : available < 1 ? "No units available" : "Acquire player"}
        </Btn>
      </div>
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
      <PlayerAcquisition playerId={playerId} />
    </div>
  );
}

export function PlayerDrawer({ playerId, onClose, extra }: { playerId: string | null; onClose: () => void; extra?: React.ReactNode }) {
  const { data: p, isLoading, isError } = useQuery({ queryKey: ["real-player", playerId], queryFn: async () => (await api.get(`/v2/players/real-universe/${playerId}`)).data, enabled: !!playerId, retry: false });
  const { data: form } = useQuery({ queryKey: ["player-form", playerId], queryFn: async () => (await api.get(`/v2/players/${playerId}/form`, { params: { include_performances: false } })).data, enabled: !!playerId });
  const { data: quote } = useQuery({ queryKey: ["player-quote", playerId], queryFn: async () => (await api.get("/owner/market/quote", { params: { player_ids: playerId } })).data.quotes[playerId as string], enabled: !!playerId });
  if (!playerId) return null;
  const signals = p?.normalized_signals || {};
  const isLegend = String(p?.real_player_tier || "").toLowerCase() === "legend";
  const honors: string[] = Array.isArray(p?.metadata_json?.honors) ? p.metadata_json.honors : [];
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
              <PlayerCard
                name={p.canonical_display_name || p.player_name}
                rating={quote?.rating}
                position={p.position}
                age={p.age}
                nationality={p.nationality}
                club={p.current_club_name}
                image={p.image_url}
                tier={isLegend ? "legendary" : undefined}
                badge={isLegend ? "ICON · 1 OF 1" : undefined}
                stats={[
                  { k: "Fee", v: fmt(quote?.price) },
                  { k: "Value", v: p.current_value_credits != null ? fmt(p.current_value_credits, 1) : fmt(quote?.price, 1) },
                  { k: "Interest", v: p.market_interest_score ?? "-" },
                ]}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Chip tone="cyan">{p.primary_position || p.position}</Chip>
              {p.current_league_name && <Chip>{p.current_league_name}</Chip>}
              {p.real_player_tier && <Chip tone="gold">{label(p.real_player_tier)}</Chip>}
              {p.lifecycle_status_label && <Chip tone="emerald">{p.lifecycle_status_label}</Chip>}
              {p.height_cm && <Chip>{p.height_cm} cm</Chip>}
            </div>
            {honors.length > 0 && (
              <div className="rounded-sm border border-amber-400/20 bg-amber-500/[0.04] p-3.5 text-xs space-y-1">
                <p className="gx-eyebrow text-amber-300 mb-1">Career Honors</p>
                {honors.map((h, i) => (
                  <p key={i} className="text-slate-300">• {h}</p>
                ))}
              </div>
            )}
            <div className="space-y-2.5" data-testid="drawer-signals">
              {Object.entries(signals)
                .filter(([, v]) => !Number.isNaN(Number(v)))
                .map(([k, v]: any) => (
                  <TraitBar key={k} label={label(k.replace(/_(score|signal)$/, ""))} value={Math.round(Number(v))} max={100} />
                ))}
            </div>
            <div className="rounded-sm border border-white/10 p-4 text-sm" data-testid="drawer-form">
              <p className="gx-eyebrow mb-2">GTEX form</p>
              {form?.has_sample ? <p className="text-slate-300">Avg rating {form.average_rating} · {form.matches_counted} matches · trend {form.trend}</p> : <p className="text-slate-500">No GTEX competition minutes yet. Form builds once he plays.</p>}
            </div>
            <PlayerAcquisition playerId={playerId} />
            {extra}
          </div>
        )}
      </aside>
    </div>,
    document.body,
  );
}
