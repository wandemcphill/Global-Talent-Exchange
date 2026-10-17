import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { fmt } from "@/lib/owner";
import { Btn, Loading } from "@/components/gtex/ui";
import { posShort } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";

export function ShareMarket() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    const t = setTimeout(() => {
      setPage(1);
      setQ(search.trim());
    }, 450);
    return () => clearTimeout(t);
  }, [search]);
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["share-markets", page, q],
    queryFn: async () => (await api.get("/v2/players/markets", { params: { page, per_page: 15, ...(q ? { search: q } : {}) } })).data,
  });
  const pg = data?.pagination;
  return (
    <div data-testid="share-market">
      <form onSubmit={(e) => { e.preventDefault(); setPage(1); setQ(search); }} className="relative mb-4 max-w-md">
        <Search size={14} className="absolute left-3 top-3 text-slate-500" />
        <input data-testid="share-market-search" className="gx-input pl-9" placeholder="Search issued player markets" value={search} onChange={(e) => setSearch(e.target.value)} />
      </form>
      {isLoading ? <Loading label={q ? `Searching “${q}”…` : "Loading share markets"} /> : (
        <div className={`gx-scroll overflow-x-auto transition-opacity ${isFetching ? "opacity-50" : ""}`} data-testid="share-market-results">
          <table className="gx-table w-full min-w-[640px]">
            <thead><tr><th>Player</th><th>Pos</th><th>Club</th><th>Share price</th><th>Circulating</th><th>Liquidity</th></tr></thead>
            <tbody>
              {(data?.items || []).map((m: any) => (
                <tr key={m.player_id} data-testid={`share-row-${m.player_id}`} onClick={() => setOpen(m.player_id)} className="cursor-pointer transition-colors hover:bg-white/[0.03]">
                  <td className="font-medium text-white">{m.player_name}<span className="block text-xs text-slate-500">{m.nationality}</span></td>
                  <td className="gx-mono">{posShort(m.position)}</td>
                  <td className="text-xs text-slate-400">{m.current_club_name}</td>
                  <td className="gx-mono text-emerald-300">{fmt(m.share_price_coin, 4)}</td>
                  <td className="gx-mono">{m.circulating_shares}/{m.total_shares}</td>
                  <td className="gx-mono">{fmt(m.liquidity_coin, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
