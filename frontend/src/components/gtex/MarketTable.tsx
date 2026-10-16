import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Search } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, useRefreshOwner } from "@/lib/owner";
import { Btn, Coin, Loading } from "@/components/gtex/ui";

const POSITIONS = ["", "goalkeeper", "defender", "midfielder", "forward"];

export function MarketTable({ clubId, initialPosition = "", onSigned, signedRefs = [] }: any) {
  const [position, setPosition] = useState(initialPosition);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const refresh = useRefreshOwner();
  const { data, isLoading } = useQuery({
    queryKey: ["market", position, q],
    queryFn: async () => {
      const params: any = { limit: 40 };
      if (position) params.position = position;
      if (q) params.search = q;
      const items = (await api.get("/market/players", { params })).data.items || [];
      const ids = items.map((p: any) => p.player_id).join(",");
      const quotes = ids ? (await api.get("/owner/market/quote", { params: { player_ids: ids } })).data.quotes : {};
      return items.map((p: any) => ({ ...p, quote: quotes[p.player_id] }));
    },
  });
  const sign = async (p: any) => {
    setBusy(p.player_id);
    try {
      const { data: res } = await api.post(`/owner/clubs/${clubId}/sign`, { player_id: p.player_id });
      toast.success(`${res.player.name} signed. Club cash: ${fmt(res.cash)} GTX`);
      refresh();
      onSigned?.(res);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <div data-testid="market-table">
      <div className="mb-4 flex flex-wrap gap-2">
        <form onSubmit={(e) => { e.preventDefault(); setQ(search); }} className="relative min-w-[220px] flex-1">
          <Search size={14} className="absolute left-3 top-3 text-slate-500" />
          <input data-testid="market-search-input" className="gx-input pl-9" placeholder="Search players" value={search} onChange={(e) => setSearch(e.target.value)} />
        </form>
        <div className="flex flex-wrap gap-1">
          {POSITIONS.map((p) => (
            <button key={p || "all"} data-testid={`market-filter-${p || "all"}`} onClick={() => setPosition(p)} className={`gx-btn ${position === p ? "gx-btn-primary" : "gx-btn-secondary"}`}>
              {p || "All"}
            </button>
          ))}
        </div>
      </div>
      {isLoading ? (
        <Loading label="Scouting the world market" />
      ) : (
        <div className="gx-scroll overflow-x-auto">
          <table className="gx-table w-full min-w-[720px]">
            <thead>
              <tr>
                <th>Player</th><th>Pos</th><th>Age</th><th>Club / League</th><th>GTEX rating</th><th>Fee</th><th />
              </tr>
            </thead>
            <tbody>
              {(data || []).map((p: any) => {
                const owned = signedRefs.includes(p.player_id);
                return (
                  <tr key={p.player_id} data-testid={`market-row-${p.player_id}`}>
                    <td className="font-medium text-white">{p.player_name}<span className="block text-xs text-slate-500">{p.nationality}</span></td>
                    <td className="capitalize">{p.position}</td>
                    <td className="gx-mono">{p.age ?? "-"}</td>
                    <td className="text-xs text-slate-400">{p.current_club_name}<span className="block">{p.current_competition_name}</span></td>
                    <td className="gx-mono text-emerald-300">{p.quote?.rating ?? "-"}</td>
                    <td><Coin amount={p.quote?.price} /></td>
                    <td className="text-right">
                      <Btn variant={owned ? "ghost" : "secondary"} disabled={owned || busy === p.player_id || !clubId} onClick={() => sign(p)} data-testid={`sign-player-${p.player_id}`}>
                        {owned ? "In squad" : busy === p.player_id ? "…" : "Sign"}
                      </Btn>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
