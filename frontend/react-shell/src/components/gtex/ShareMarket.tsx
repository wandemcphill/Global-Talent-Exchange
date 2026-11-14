import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Crown, Search, Sparkles, Star } from "lucide-react";
import { api } from "@/lib/api";
import { fmt } from "@/lib/owner";
import { Btn, Loading } from "@/components/gtex/ui";
import { posShort, sanitizeRealPlayerImage } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";

function Thumb({ src, name, regen, legend }: { src?: string | null; name: string; regen?: boolean; legend?: boolean }) {
  const [broken, setBroken] = useState(false);
  const cleanSrc = sanitizeRealPlayerImage(src, regen);
  const ring = legend
    ? "border-amber-400/70 bg-amber-950/60"
    : regen
    ? "border-emerald-400/60 bg-emerald-950/60"
    : "border-white/15 bg-slate-900";
  if (cleanSrc && !broken) return <img src={cleanSrc} alt="" loading="lazy" onError={() => setBroken(true)} className={`h-10 w-10 shrink-0 rounded-sm border object-cover ${ring}`} />;
  return <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-sm border text-xs font-bold text-white/60 ${ring}`}>{name.split(" ").map((s) => s[0]).slice(0, 2).join("")}</span>;
}

function Filters({ sourceMode, setSourceMode, nation, setNation, sort, setSort }: any) {
  const source = sourceMode || undefined;
  const { data: nations } = useQuery({
    queryKey: ["share-market-nations", source],
    queryFn: async () => (await api.get("/v2/players/markets/nations", { params: source ? { source } : {} })).data,
    staleTime: 300_000,
  });
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        data-testid="share-market-legend-toggle"
        onClick={() => setSourceMode(sourceMode === "legend" ? "" : "legend")}
        className={`gx-btn ${
          sourceMode === "legend"
            ? "border-amber-400 bg-amber-500 text-black font-bold"
            : "border-amber-400/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
        }`}
      >
        <Crown size={13} />Legends
      </button>
      <button
        type="button"
        data-testid="share-market-regen-toggle"
        onClick={() => setSourceMode(sourceMode === "regen" ? "" : "regen")}
        className={`gx-btn ${sourceMode === "regen" ? "gx-btn-primary" : "gx-btn-secondary"}`}
      >
        <Sparkles size={13} />Regens only
      </button>
      <select data-testid="share-market-nation-select" className="gx-input w-56" value={nation} onChange={(e) => setNation(e.target.value)}>
        <option value="">All nations</option>
        {(nations || []).map((n: any) => <option key={n.name} value={n.name}>{`${n.name} (${fmt(n.count)})`}</option>)}
      </select>
      <select data-testid="share-market-sort-select" className="gx-input w-48" value={sort} onChange={(e) => setSort(e.target.value)}>
        <option value="value">Sort: GSI</option>
        <option value="name">Sort: Name</option>
        <option value="wonderkid">Sort: Wonderkid</option>
      </select>
    </div>
  );
}

function WonderkidSpotlight({ nation, onOpen }: { nation: string; onOpen: (id: string) => void }) {
  const { data, isLoading } = useQuery({ queryKey: ["wonderkid-spotlight", nation], queryFn: async () => (await api.get("/v2/players/markets", { params: { page: 1, per_page: 5, sort: "wonderkid", nation } })).data, staleTime: 120_000 });
  const items = data?.items || [];
  if (!isLoading && items.length === 0) return null;
  return (
    <section className="mb-5 rounded-sm border border-amber-400/20 bg-amber-500/[0.04] p-4" data-testid="wonderkid-spotlight">
      <p className="gx-eyebrow mb-3 flex items-center gap-2 text-amber-300"><Star size={13} />Wonderkid spotlight · {nation}</p>
      {isLoading ? <Loading label="Scouting the brightest prospects" /> : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {items.map((m: any, i: number) => (
            <button key={m.player_id} type="button" data-testid={`wonderkid-card-${m.player_id}`} onClick={() => onOpen(m.player_id)} style={{ animationDelay: `${i * 60}ms` }}
              className="flex animate-in fade-in slide-in-from-bottom-1 items-center gap-2 rounded-sm border border-white/10 bg-black/30 p-2 text-left transition-colors hover:border-amber-400/50">
              <Thumb src={m.image_url} name={m.player_name} regen />
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-white">{m.player_name}</p>
                <p className="gx-mono text-[11px] text-amber-300">GSI {m.rating ?? "-"} <span className="text-slate-500">· {m.age ?? "-"}y · {posShort(m.position)}</span></p>
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export function ShareMarket() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [sourceMode, setSourceMode] = useState<"" | "regen" | "legend">("");
  const [nation, setNation] = useState("");
  const [sort, setSort] = useState("value");
  const [open, setOpen] = useState<string | null>(null);
  const wonder = sort === "wonderkid";
  const effectiveSource = wonder ? "regen" : sourceMode;

  useEffect(() => {
    const t = setTimeout(() => {
      setPage(1);
      setQ(search.trim());
    }, 450);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [sourceMode, nation, sort]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["share-markets", page, q, effectiveSource, nation, sort],
    queryFn: async () =>
      (
        await api.get("/v2/players/markets", {
          params: {
            page,
            per_page: 15,
            ...(q ? { search: q } : {}),
            ...(effectiveSource ? { source: effectiveSource } : {}),
            ...(nation ? { nation } : {}),
            ...(sort ? { sort } : {}),
          },
        })
      ).data,
    placeholderData: (prev: any) => prev,
  });
  const pg = data?.pagination;
  return (
    <div data-testid="share-market">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] max-w-md flex-1">
          <Search size={14} className="absolute left-3 top-3 text-slate-500" />
          <input data-testid="share-market-search" className="gx-input pl-9" placeholder="Search players" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Filters sourceMode={effectiveSource} setSourceMode={setSourceMode} nation={nation} setNation={setNation} sort={sort} setSort={setSort} />
      </div>
      {nation && <WonderkidSpotlight nation={nation} onOpen={setOpen} />}
      {isLoading ? <Loading label={q ? `Searching “${q}”…` : "Loading player catalogue"} /> : (
        <div className={`gx-scroll overflow-x-auto transition-opacity ${isFetching ? "opacity-50" : ""}`} data-testid="share-market-results">
          <table className="gx-table w-full min-w-[700px]">
            <thead><tr><th>Player</th><th>Pos</th><th>GSI</th><th>Club</th><th>Acquisition price</th><th>Units available</th></tr></thead>
            <tbody>
              {(data?.items || []).map((m: any) => {
                const isLegend = Boolean(m.is_legend) || String(m.real_player_tier || "").toLowerCase() === "legend";
                return (
                  <tr key={m.player_id} data-testid={`share-row-${m.player_id}`} onClick={() => setOpen(m.player_id)} className="cursor-pointer transition-colors hover:bg-white/[0.03]">
                    <td>
                      <div className="flex items-center gap-3">
                        <Thumb src={m.image_url} name={m.player_name} regen={m.is_regen} legend={isLegend} />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-white">
                            {m.player_name}
                            {isLegend && (
                              <span className="ml-2 rounded-sm bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase text-amber-300" data-testid={`share-row-legend-${m.player_id}`}>
                                Legend
                              </span>
                            )}
                            {!isLegend && m.is_regen && (
                              <span className="ml-2 rounded-sm bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-bold uppercase text-emerald-300" data-testid={`share-row-regen-${m.player_id}`}>
                                Regen
                              </span>
                            )}
                          </p>
                          <p className="truncate text-xs text-slate-500">
                            {m.nationality}
                            {m.playstyle && (
                              <span className="ml-1.5 text-cyan-400/90">· {m.playstyle}</span>
                            )}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="gx-mono">{posShort(m.position)}</td>
                    <td className="gx-mono text-xs" data-testid={`share-row-potential-${m.player_id}`}>
                      {m.rating ?? "-"} <span className="text-amber-300">→ {m.potential ?? m.rating ?? "-"}</span>
                      {m.age != null && <span className="ml-1 text-slate-500">· {m.age}y</span>}
                    </td>
                    <td className="text-xs text-slate-400">{m.current_club_name}</td>
                    <td className="gx-mono text-emerald-300">{fmt(m.share_price_coin, 2)} GTX</td>
                    <td className="gx-mono">{Math.max(0, Number(m.released_shares ?? m.total_shares) - Number(m.circulating_shares || 0))}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {data?.items?.length === 0 && <p className="py-6 text-center text-sm text-slate-500" data-testid="share-market-empty">No players match these filters.</p>}
        </div>
      )}
      {pg && (
        <div className="mt-4 flex items-center gap-3 text-xs text-slate-500">
          <Btn variant="secondary" disabled={!pg.has_previous} onClick={() => setPage(page - 1)} data-testid="share-market-prev">Prev</Btn>
          <span className="gx-mono" data-testid="share-market-page">Page {pg.page} / {fmt(pg.total_pages)} · {fmt(pg.total)} players</span>
          <Btn variant="secondary" disabled={!pg.has_next} onClick={() => setPage(page + 1)} data-testid="share-market-next">Next</Btn>
        </div>
      )}
      <PlayerDrawer playerId={open} onClose={() => setOpen(null)} />
    </div>
  );
}
