import React, { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Search } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, useRefreshOwner } from "@/lib/owner";
import { Btn, Coin, Empty, Loading } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";

const POSITIONS = ["", "goalkeeper", "defender", "midfielder", "forward"];

async function fetchPage(position: string, q: string, cursor?: string) {
  const params: any = { limit: 24 };
  if (position) params.position = position;
  if (q) params.search = q;
  if (cursor) params.cursor = cursor;
  const page = (await api.get("/v2/players", { params })).data;
  const ids = (page.players || []).map((p: any) => p.player_id).join(",");
  const quotes = ids ? (await api.get("/owner/market/quote", { params: { player_ids: ids } })).data.quotes : {};
  return { ...page, players: (page.players || []).map((p: any) => ({ ...p, quote: quotes[p.player_id] })) };
}

export function MarketTable({ clubId, initialPosition = "", onSigned, signedRefs = [] }: any) {
  const [position, setPosition] = useState(initialPosition);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const refresh = useRefreshOwner();
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ["market", position, q],
    queryFn: ({ pageParam }: any) => fetchPage(position, q, pageParam),
    initialPageParam: undefined,
    getNextPageParam: (last: any) => (last.has_more ? last.next_cursor : undefined),
  } as any);
  const pages: any[] = (data as any)?.pages || [];
  const players = pages.flatMap((p) => p.players);
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
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <form onSubmit={(e) => { e.preventDefault(); setQ(search); }} className="relative min-w-[220px] flex-1">
          <Search size={14} className="absolute left-3 top-3 text-slate-500" />
          <input data-testid="market-search-input" className="gx-input pl-9" placeholder="Search players, e.g. Osimhen" value={search} onChange={(e) => setSearch(e.target.value)} />
        </form>
        <div className="flex flex-wrap gap-1">
          {POSITIONS.map((p) => (
            <button key={p || "all"} data-testid={`market-filter-${p || "all"}`} onClick={() => setPosition(p)} className={`gx-btn capitalize ${position === p ? "gx-btn-primary" : "gx-btn-secondary"}`}>{p || "All"}</button>
          ))}
        </div>
        {pages[0] && <span className="gx-mono text-xs text-slate-500" data-testid="market-total">{fmt(pages[0].total)} live players</span>}
      </div>
      {isLoading ? <Loading label="Scouting the world market" /> : players.length === 0 ? <Empty title="No players found" body="Try another name or position." /> : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6">
          {players.map((p: any) => {
            const owned = signedRefs.includes(p.player_id);
            return (
              <PlayerCard key={p.player_id} testid={`market-card-${p.player_id}`} name={p.player_name} rating={p.quote?.rating} position={p.position} age={p.age} nationality={p.nationality} club={p.current_club_name} image={p.image_url} onClick={() => setOpen(p.player_id)}
                stats={[{ k: "Fee", v: fmt(p.quote?.price) }, { k: "Value", v: fmt(p.current_value_credits, 1) }, { k: "Form", v: p.average_rating ?? "-" }]}
                footer={<Btn className="w-full justify-center" variant={owned ? "ghost" : "secondary"} disabled={owned || busy === p.player_id || !clubId} onClick={() => sign(p)} data-testid={`sign-player-${p.player_id}`}>{owned ? "In squad" : busy === p.player_id ? "Signing…" : <>Sign · <Coin amount={p.quote?.price} /></>}</Btn>} />
            );
          })}
        </div>
      )}
      {hasNextPage && <div className="mt-5 text-center"><Btn variant="secondary" onClick={() => fetchNextPage()} disabled={isFetchingNextPage} data-testid="market-load-more">{isFetchingNextPage ? "Loading…" : "Load more players"}</Btn></div>}
      <PlayerDrawer playerId={open} onClose={() => setOpen(null)} />
    </div>
  );
}
