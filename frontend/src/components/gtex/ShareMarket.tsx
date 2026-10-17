import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { fmt } from "@/lib/owner";
import { Btn, Loading } from "@/components/gtex/ui";
import { posShort } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";

function Thumb({ src, name, regen }: { src?: string | null; name: string; regen?: boolean }) {
  const [broken, setBroken] = useState(false);
  const ring = regen ? "border-emerald-400/60 bg-emerald-950/60" : "border-white/15 bg-slate-900";
  if (src && !broken) return <img src={src} alt="" loading="lazy" onError={() => setBroken(true)} className={`h-10 w-10 shrink-0 rounded-sm border object-cover ${ring}`} />;
  return <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-sm border text-xs font-bold text-white/60 ${ring}`}>{name.split(" ").map((s) => s[0]).slice(0, 2).join("")}</span>;
}

function Filters({ regenOnly, setRegenOnly, nation, setNation }: any) {
  const source = regenOnly ? "regen" : undefined;
  const { data: nations } = useQuery({ queryKey: ["share-market-nations", source], queryFn: async () => (await api.get("/v2/players/markets/nations", { params: source ? { source } : {} })).data, staleTime: 300_000 });
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" data-testid="share-market-regen-toggle" onClick={() => setRegenOnly(!regenOnly)} className={`gx-btn ${regenOnly ? "gx-btn-primary" : "gx-btn-secondary"}`}>
        <Sparkles size={13} />Regens only
      </button>
      <select data-testid="share-market-nation-select" className="gx-input w-56" value={nation} onChange={(e) => setNation(e.target.value)}>
        <option value="">All nations</option>
        {(nations || []).map((n: any) => <option key={n.name} value={n.name}>{`${n.name} (${fmt(n.count)})`}</option>)}
      </select>
    </div>
  );
}

export function ShareMarket() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [regenOnly, setRegenOnly] = useState(false);
  const [nation, setNation] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    const t = setTimeout(() => {
      setPage(1);
      setQ(search.trim());
    }, 450);
    return () => clearTimeout(t);
  }, [search]);
  useEffect(() => {
    setPage(1);
  }, [regenOnly, nation]);
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["share-markets", page, q, regenOnly, nation],
    queryFn: async () => (await api.get("/v2/players/markets", { params: { page, per_page: 15, ...(q ? { search: q } : {}), ...(regenOnly ? { source: "regen" } : {}), ...(nation ? { nation } : {}) } })).data,
    placeholderData: (prev: any) => prev,
  });
  const pg = data?.pagination;
  return (
    <div data-testid="share-market">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] max-w-md flex-1">
          <Search size={14} className="absolute left-3 top-3 text-slate-500" />
          <input data-testid="share-market-search" className="gx-input pl-9" placeholder="Search issued player markets" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Filters regenOnly={regenOnly} setRegenOnly={setRegenOnly} nation={nation} setNation={setNation} />
      </div>
      {isLoading ? <Loading label={q ? `Searching “${q}”…` : "Loading share markets"} /> : (
        <div className={`gx-scroll overflow-x-auto transition-opacity ${isFetching ? "opacity-50" : ""}`} data-testid="share-market-results">
          <table className="gx-table w-full min-w-[680px]">
            <thead><tr><th>Player</th><th>Pos</th><th>Club</th><th>Share price</th><th>Circulating</th><th>Liquidity</th></tr></thead>
            <tbody>
              {(data?.items || []).map((m: any) => (
                <tr key={m.player_id} data-testid={`share-row-${m.player_id}`} onClick={() => setOpen(m.player_id)} className="cursor-pointer transition-colors hover:bg-white/[0.03]">
                  <td>
                    <div className="flex items-center gap-3">
                      <Thumb src={m.image_url} name={m.player_name} regen={m.is_regen} />
                      <div className="min-w-0">
                        <p className="truncate font-medium text-white">{m.player_name}{m.is_regen && <span className="ml-2 rounded-sm bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-bold uppercase text-emerald-300" data-testid={`share-row-regen-${m.player_id}`}>Regen</span>}</p>
                        <p className="truncate text-xs text-slate-500">{m.nationality}</p>
                      </div>
                    </div>
                  </td>
                  <td className="gx-mono">{posShort(m.position)}</td>
                  <td className="text-xs text-slate-400">{m.current_club_name}</td>
                  <td className="gx-mono text-emerald-300">{fmt(m.share_price_coin, 4)}</td>
                  <td className="gx-mono">{m.circulating_shares}/{m.total_shares}</td>
                  <td className="gx-mono">{fmt(m.liquidity_coin, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.items?.length === 0 && <p className="py-6 text-center text-sm text-slate-500" data-testid="share-market-empty">No markets match these filters.</p>}
        </div>
      )}
      {pg && (
        <div className="mt-4 flex items-center gap-3 text-xs text-slate-500">
          <Btn variant="secondary" disabled={!pg.has_previous} onClick={() => setPage(page - 1)} data-testid="share-market-prev">Prev</Btn>
          <span className="gx-mono" data-testid="share-market-page">Page {pg.page} / {fmt(pg.total_pages)} · {fmt(pg.total)} markets</span>
          <Btn variant="secondary" disabled={!pg.has_next} onClick={() => setPage(page + 1)} data-testid="share-market-next">Next</Btn>
        </div>
      )}
      <PlayerDrawer playerId={open} onClose={() => setOpen(null)} />
    </div>
  );
}
