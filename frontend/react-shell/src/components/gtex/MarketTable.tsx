import React, { useEffect, useMemo, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowUpDown, Crown, DollarSign, Search, Sparkles } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, useRefreshOwner } from "@/lib/owner";
import { Btn, Coin, Empty, Loading } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";
import { MarketTableView } from "@/components/gtex/MarketTableView";
import { useSkin } from "@/lib/skin-engine";

const POSITIONS = ["", "goalkeeper", "defender", "midfielder", "forward"];

const TIER_FILTERS = [
  { id: "", label: "All Tiers" },
  { id: "legend", label: "★ Legends" },
  { id: "marquee", label: "World Stars" },
  { id: "wonderkid", label: "Wonderkids" },
  { id: "regen", label: "Regens" },
];

export function marketLane(player: any): "welcome" | "paid" {
  const quoted = player?.quote?.lane;
  if (quoted === "welcome" || quoted === "paid") return quoted;
  const rawRating = player?.quote?.rating ?? player?.rating ?? player?.overall_rating;
  const rating = rawRating == null || rawRating === "" ? null : Number(rawRating);
  const tierNorm = String(player?.real_player_tier || "").toLowerCase();
  const isLegend = tierNorm === "legend" || tierNorm === "icon";
  const isRegen =
    Boolean(player?.is_regen) || player?.is_real_player === false || tierNorm === "regen";
  return isLegend || isRegen || rating == null || rating >= 75 ? "paid" : "welcome";
}

const PRICE_PRESETS = [
  { label: "All Prices", value: 0 },
  { label: "≤ 60 GTX", value: 60 },
  { label: "≤ 180 GTX", value: 180 },
  { label: "≤ 350 GTX", value: 350 },
  { label: "≤ 1.5k GTX", value: 1500 },
];

async function fetchPage(
  position: string,
  tier: string,
  q: string,
  nationality: string,
  minAge: string,
  maxAge: string,
  foot: string,
  minHeight: string,
  maxHeight: string,
  cursor?: string,
) {
  const params: any = { limit: 48 };
  if (position) params.position = position;
  if (tier) params.tier = tier;
  if (nationality) params.nationality = nationality;
  if (q) params.search = q;
  if (minAge) params.min_age = Number(minAge);
  if (maxAge) params.max_age = Number(maxAge);
  if (foot) params.foot = foot;
  if (minHeight) params.min_height = Number(minHeight);
  if (maxHeight) params.max_height = Number(maxHeight);
  if (cursor) params.cursor = cursor;
  const page = (await api.get("/v2/players", { params })).data;
  const ids = (page.players || []).map((p: any) => p.player_id).join(",");
  const quotes = ids
    ? (await api.get("/owner/market/quote", { params: { player_ids: ids } })).data.quotes
    : {};
  return {
    ...page,
    players: (page.players || []).map((p: any) => ({ ...p, quote: quotes[p.player_id] })),
  };
}

export function MarketTable({
  clubId,
  initialPosition = "",
  onSigned,
  signedRefs = [],
  clubCash,
  queuedIds = [],
  onQueue,
}: any) {
  const [position, setPosition] = useState(initialPosition);
  const [tier, setTier] = useState("");
  const [nation, setNation] = useState("");
  const [nationQuery, setNationQuery] = useState("");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [minAge, setMinAge] = useState("");
  const [maxAge, setMaxAge] = useState("");
  const [foot, setFoot] = useState("");
  const [minHeight, setMinHeight] = useState("");
  const [maxHeight, setMaxHeight] = useState("");
  const [maxPrice, setMaxPrice] = useState<number>(0);
  const [sortBy, setSortBy] = useState<string>("default");
  const [busy, setBusy] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const refresh = useRefreshOwner();
  const { getModuleView, setModuleView } = useSkin();
  const marketView = getModuleView("market");
  const queueMode = typeof onQueue === "function";

  useEffect(() => {
    const handle = window.setTimeout(() => setQ(search.trim()), 280);
    return () => window.clearTimeout(handle);
  }, [search]);

  useEffect(() => {
    const handle = window.setTimeout(() => setNationQuery(nation.trim()), 280);
    return () => window.clearTimeout(handle);
  }, [nation]);

  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ["market", position, tier, q, nationQuery, minAge, maxAge, foot, minHeight, maxHeight],
    queryFn: ({ pageParam }: any) =>
      fetchPage(position, tier, q, nationQuery, minAge, maxAge, foot, minHeight, maxHeight, pageParam),
    initialPageParam: undefined,
    getNextPageParam: (last: any) => (last.has_more ? last.next_cursor : undefined),
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
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
      const { data: res } = await api.post(`/owner/clubs/${clubId}/sign`, {
        player_id: p.player_id,
      });
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
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setQ(search);
          }}
          className="relative min-w-[220px] flex-1"
        >
          <Search size={14} className="absolute left-3 top-3 text-slate-500" />
          <input
            data-testid="market-search-input"
            className="gx-input pl-9"
            placeholder="Name, club, nation, or position"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </form>
        <div className="flex flex-wrap gap-1">
          {TIER_FILTERS.map((t) => {
            const active = tier === t.id;
            const isLegendBtn = t.id === "legend";
            return (
              <button
                key={t.id || "all-tiers"}
                type="button"
                data-testid={`market-tier-${t.id || "all"}`}
                onClick={() => setTier(t.id)}
                className={`gx-btn ${
                  active
                    ? isLegendBtn
                      ? "border-amber-400 bg-amber-500 text-black font-bold"
                      : "gx-btn-primary"
                    : isLegendBtn
                      ? "border-amber-400/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
                      : "gx-btn-secondary"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>
        <form
          className="flex min-w-[180px] gap-1"
          onSubmit={(event) => {
            event.preventDefault();
            setNationQuery(nation.trim());
          }}
        >
          <input
            data-testid="market-nation-input"
            className="gx-input py-1 text-xs"
            placeholder="Nation, e.g. Spain"
            value={nation}
            onChange={(event) => setNation(event.target.value)}
          />
          <button type="submit" className="gx-btn gx-btn-secondary">
            Nation
          </button>
        </form>
        <div className="flex flex-wrap gap-1">
          {POSITIONS.map((p) => (
            <button
              key={p || "all"}
              type="button"
              data-testid={`market-filter-${p || "all"}`}
              onClick={() => setPosition(p)}
              className={`gx-btn capitalize ${position === p ? "gx-btn-primary" : "gx-btn-secondary"}`}
            >
              {p || "All Positions"}
            </button>
          ))}
        </div>
      </div>

      {/* Secondary Bar: Price Filter & Sort Controls */}
      <div className="flex flex-wrap items-end gap-3 rounded-sm border border-white/10 bg-slate-950/40 p-3">
        <label className="flex flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Age
          <span className="flex items-center gap-1">
            <input
              data-testid="market-min-age"
              className="gx-input w-16 py-1 text-xs"
              inputMode="numeric"
              placeholder="Min"
              value={minAge}
              onChange={(event) => setMinAge(event.target.value.replace(/\D/g, "").slice(0, 2))}
            />
            <input
              data-testid="market-max-age"
              className="gx-input w-16 py-1 text-xs"
              inputMode="numeric"
              placeholder="Max"
              value={maxAge}
              onChange={(event) => setMaxAge(event.target.value.replace(/\D/g, "").slice(0, 2))}
            />
          </span>
        </label>
        <label className="flex flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Foot
          <select
            data-testid="market-foot"
            className="gx-input py-1 text-xs"
            value={foot}
            onChange={(event) => setFoot(event.target.value)}
          >
            <option value="">Any</option>
            <option value="left">Left</option>
            <option value="right">Right</option>
            <option value="both">Both</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Height cm
          <span className="flex items-center gap-1">
            <input
              data-testid="market-min-height"
              className="gx-input w-16 py-1 text-xs"
              inputMode="numeric"
              placeholder="Min"
              value={minHeight}
              onChange={(event) => setMinHeight(event.target.value.replace(/\D/g, "").slice(0, 3))}
            />
            <input
              data-testid="market-max-height"
              className="gx-input w-16 py-1 text-xs"
              inputMode="numeric"
              placeholder="Max"
              value={maxHeight}
              onChange={(event) => setMaxHeight(event.target.value.replace(/\D/g, "").slice(0, 3))}
            />
          </span>
        </label>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 bg-slate-950/40 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <DollarSign size={13} className="text-emerald-400" /> Buying Price:
          </span>
          <div className="flex flex-wrap gap-1">
            {PRICE_PRESETS.map((preset) => (
              <button
                key={preset.value}
                type="button"
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
                type="button"
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
          {/* Layer 3: Football Display Mode Switcher */}
          <div
            className="flex items-center gap-1 rounded-lg border border-white/10 bg-black/40 p-0.5"
            data-testid="market-view-toggle"
          >
            <button
              type="button"
              onClick={() => setModuleView("market", "cards")}
              data-testid="market-view-cards"
              className={`rounded px-2.5 py-1 text-xs font-bold transition ${
                marketView === "cards"
                  ? "bg-emerald-500 text-black shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              FC Cards
            </button>
            <button
              type="button"
              onClick={() => setModuleView("market", "table")}
              data-testid="market-view-table"
              className={`rounded px-2.5 py-1 text-xs font-bold transition ${
                marketView === "table"
                  ? "bg-emerald-500 text-black shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              FM Table
            </button>
          </div>

          <span className="flex items-center gap-1 text-xs font-semibold text-slate-400">
            <ArrowUpDown size={13} /> Sort:
          </span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="gx-input py-1 text-xs max-w-[190px]"
          >
            <option value="default">Value / GSI: High to Low</option>
            <option value="rating_desc">Rating: High to Low</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
          </select>
        </div>
      </div>

      {/* Player Count Indicator */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          Showing {filteredPlayers.length} players{" "}
          {maxPrice > 0 ? `(filtered by price ≤ ${fmt(maxPrice)})` : ""}
        </span>
        {pages[0] && (
          <span className="gx-mono" data-testid="market-total">
            {fmt(pages[0].total)} total in universe
          </span>
        )}
      </div>

      {/* Grid or Empty State */}
      {isLoading ? (
        <Loading label="Scouting the world market" />
      ) : filteredPlayers.length === 0 ? (
        <Empty
          title="No players match the current filters"
          body={
            maxPrice > 0
              ? "Try selecting 'All Prices' or increasing your price filter."
              : "Search a surname, a club, a nation, or a position such as winger."
          }
        />
      ) : marketView === "table" ? (
        <MarketTableView
          players={filteredPlayers}
          signedRefs={signedRefs}
          clubId={clubId}
          clubCash={clubCash}
          busyPlayerId={busy}
          onSign={queueMode ? (player: any) => onQueue(player, marketLane(player)) : sign}
          queueMode={queueMode}
          queuedIds={queuedIds}
          onOpenDossier={(id) => setOpen(id)}
        />
      ) : (
        <div
          className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6"
          data-testid="market-cards-grid"
        >
          {filteredPlayers.map((p: any) => {
            const owned = signedRefs.includes(p.player_id);
            const price = p.quote?.price ?? 0;
            const rating = p.quote?.rating ?? p.overall_rating ?? null;
            const unaffordable = cashNum > 0 && price > cashNum && !owned;
            const tierNorm = String(p.real_player_tier || "").toLowerCase();
            const isLegend = tierNorm === "legend";
            const isRegen = p.is_regen || p.is_real_player === false || tierNorm === "regen";
            const lane = marketLane(p);
            const isRestricted = lane === "paid";
            const isWonderkid = tierNorm === "wonderkid";
            const queued = queuedIds.includes(p.player_id);

            return (
              <PlayerCard
                key={p.player_id}
                testid={`market-card-${p.player_id}`}
                name={p.canonical_display_name || p.player_name}
                rating={rating ?? undefined}
                position={p.position}
                age={p.age}
                heightCm={p.height_cm}
                foot={p.dominant_foot || p.preferred_foot}
                nationality={p.nationality}
                club={p.current_club_name}
                image={p.image_url}
                facebank={isRegen}
                tier={isLegend ? "legendary" : undefined}
                archetype={p.playstyle}
                traits={p.traits}
                badge={
                  isLegend
                    ? "ICON · 1 OF 1"
                    : isWonderkid
                      ? isRestricted
                        ? "WONDERKID · PAID ONLY"
                        : "WONDERKID"
                      : isRestricted
                        ? "PAID GTX ONLY"
                        : "WELCOME GRANT"
                }
                onClick={() => setOpen(p.player_id)}
                stats={[
                  { k: "Fee", v: price ? `${fmt(price)}` : "-" },
                  { k: "Funding", v: isRestricted ? "Top up" : "Grant" },
                  {
                    k: "Value",
                    v:
                      p.current_value_credits != null
                        ? fmt(p.current_value_credits, 1)
                        : price
                          ? fmt(price, 1)
                          : "-",
                  },
                  { k: "Form", v: p.average_rating ?? "-" },
                ]}
                footer={
                  <Btn
                    className="w-full justify-center"
                    variant={
                      owned || queued
                        ? "ghost"
                        : !queueMode && unaffordable
                          ? "outline"
                          : "secondary"
                    }
                    disabled={
                      owned ||
                      queued ||
                      busy === p.player_id ||
                      !clubId ||
                      (!queueMode && unaffordable)
                    }
                    onClick={() => (queueMode ? onQueue(p, lane) : sign(p))}
                    data-testid={`sign-player-${p.player_id}`}
                  >
                    {owned ? (
                      "In squad"
                    ) : busy === p.player_id ? (
                      "Signing…"
                    ) : queued ? (
                      "In basket"
                    ) : queueMode ? (
                      <>
                        {lane === "welcome" ? "Welcome basket" : "Paid basket"} ·{" "}
                        <Coin amount={price} />
                      </>
                    ) : unaffordable ? (
                      <span className="text-slate-400">
                        Needs <Coin amount={price} />
                      </span>
                    ) : (
                      <>
                        Sign · <Coin amount={price} />
                      </>
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
