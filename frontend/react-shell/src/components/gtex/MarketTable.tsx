import React, { useMemo, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowUpDown, DollarSign, Filter, Search } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, useRefreshOwner } from "@/lib/owner";
import { Btn, Coin, Empty, Loading } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";

const POSITIONS = ["", "goalkeeper", "defender", "midfielder", "forward"];

const PRICE_PRESETS = [
  { label: "All Prices", value: 0 },
  { label: "≤ 1k GTX", value: 1000 },
  { label: "≤ 2.5k GTX", value: 2500 },
  { label: "≤ 5k GTX", value: 5000 },
  { label: "≤ 11k GTX", value: 11000 },
];

async function fetchPage(position: string, q: string, cursor?: string) {
  const params: any = { limit: 48 };
  if (position) params.position = position;
  if (q) params.search = q;
  if (cursor) params.cursor = cursor;
  const page = (await api.get("/v2/players", { params })).data;
  const ids = (page.players || []).map((p: any) => p.player_id).join(",");
  const quotes = ids ? (await api.get("/owner/market/quote", { params: { player_ids: ids } })).data.quotes : {};
  return { ...page, players: (page.players || []).map((p: any) => ({ ...p, quote: quotes[p.player_id] })) };
}

export function MarketTable({ clubId, initialPosition = "", onSigned, signedRefs = [], clubCash }: any) {
  const [position, setPosition] = useState(initialPosition);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [maxPrice, setMaxPrice] = useState<number>(0);
  const [sortBy, setSortBy] = useState<string>("price_asc");
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
  const rawPlayers = useMemo(() => pages.flatMap((p) => p.players), [pages]);

  const filteredPlayers = useMemo(() => {
    let list = [...rawPlayers];

    if (maxPrice > 0) {
      list = list.filter((p) => {
        const price = p.quote?.price ?? Infinity;
        return price <= maxPrice;
      });
    }

    if (sortBy === "price_asc") {
      list.sort((a, b) => (a.quote?.price ?? Infinity) - (b.quote?.price ?? Infinity));
    } else if (sortBy === "price_desc") {
      list.sort((a, b) => (b.quote?.price ?? 0) - (a.quote?.price ?? 0));
    } else if (sortBy === "rating_desc") {
      list.sort((a, b) => (b.quote?.rating ?? 0) - (a.quote?.rating ?? 0));
    }

    return list;
  }, [rawPlayers, maxPrice, sortBy]);

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

  const cashNum = Number(clubCash || 0);

  return (
    <div data-testid="market-table" className="space-y-4">
      {/* Search and Main Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <form onSubmit={(e) => { e.preventDefault(); setQ(search); }} className="relative min-w-[220px] flex-1">
          <Search size={14} className="absolute left-3 top-3 text-slate-500" />
          <input
            data-testid="market-search-input"
            className="gx-input pl-9"
            placeholder="Search players, e.g. Osimhen"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </form>
        <div className="flex flex-wrap gap-1">
          {POSITIONS.map((p) => (
            <button
              key={p || "all"}
              data-testid={`market-filter-${p || "all"}`}
              onClick={() => setPosition(p)}
              className={`gx-btn capitalize ${position === p ? "gx-btn-primary" : "gx-btn-secondary"}`}
            >
              {p || "All"}
            </button>
          ))}
        </div>
      </div>

      {/* Secondary Bar: Price Filter & Sort Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 bg-slate-950/40 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <DollarSign size={13} className="text-emerald-400" /> Buying Price:
          </span>
          <div className="flex flex-wrap gap-1">
            {PRICE_PRESETS.map((preset) => (
              <button
                key={preset.value}
                onClick={() => setMaxPrice(preset.value)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  maxPrice === preset.value
                    ? "bg-emerald-500 text-black font-semibold"
                    : "border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                }`}
              >
                {preset.label}
              </button>
            ))}
            {cashNum > 0 && (
              <button
                onClick={() => setMaxPrice(cashNum)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  maxPrice === cashNum
                    ? "bg-emerald-500 text-black font-semibold"
                    : "border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                }`}
                title="Show only players you can afford with current club cash"
              >
                Affordable (≤ {fmt(cashNum, 0)} GTX)
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 text-xs font-semibold text-slate-400">
            <ArrowUpDown size={13} /> Sort:
          </span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="gx-input py-1 text-xs max-w-[170px]"
          >
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="rating_desc">Rating: High to Low</option>
            <option value="default">Default Discovery</option>
          </select>
        </div>
      </div>

      {/* Player Count Indicator */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Showing {filteredPlayers.length} players {maxPrice > 0 ? `(filtered by price ≤ ${fmt(maxPrice)})` : ""}</span>
        {pages[0] && <span className="gx-mono" data-testid="market-total">{fmt(pages[0].total)} total in universe</span>}
      </div>

      {/* Grid or Empty State */}
      {isLoading ? (
        <Loading label="Scouting the world market" />
      ) : filteredPlayers.length === 0 ? (
        <Empty
          title="No players match the price / position filters"
          body={maxPrice > 0 ? "Try selecting 'All Prices' or increasing your price filter." : "Try another name or position."}
        />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6">
          {filteredPlayers.map((p: any) => {
            const owned = signedRefs.includes(p.player_id);
            const price = p.quote?.price ?? 0;
            const unaffordable = cashNum > 0 && price > cashNum && !owned;

            return (
              <PlayerCard
                key={p.player_id}
                testid={`market-card-${p.player_id}`}
                name={p.player_name}
                rating={p.quote?.rating}
                position={p.position}
                age={p.age}
                nationality={p.nationality}
                club={p.current_club_name}
                image={p.image_url}
                onClick={() => setOpen(p.player_id)}
                stats={[
                  { k: "Fee", v: price ? `${fmt(price)}` : "-" },
                  { k: "Value", v: fmt(p.current_value_credits, 1) },
                  { k: "Form", v: p.average_rating ?? "-" },
                ]}
                footer={
                  <Btn
                    className="w-full justify-center"
                    variant={owned ? "ghost" : unaffordable ? "outline" : "secondary"}
                    disabled={owned || busy === p.player_id || !clubId || unaffordable}
                    onClick={() => sign(p)}
                    data-testid={`sign-player-${p.player_id}`}
                  >
                    {owned ? (
                      "In squad"
                    ) : busy === p.player_id ? (
                      "Signing…"
                    ) : unaffordable ? (
                      <span className="text-slate-400">Needs <Coin amount={price} /></span>
                    ) : (
                      <>Sign · <Coin amount={price} /></>
                    )}
                  </Btn>
                }
              />
            );
          })}
        </div>
      )}

      {hasNextPage && (
        <div className="mt-5 text-center">
          <Btn
            variant="secondary"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            data-testid="market-load-more"
          >
            {isFetchingNextPage ? "Loading…" : "Load more players"}
          </Btn>
        </div>
      )}

      <PlayerDrawer playerId={open} onClose={() => setOpen(null)} />
    </div>
  );
}
