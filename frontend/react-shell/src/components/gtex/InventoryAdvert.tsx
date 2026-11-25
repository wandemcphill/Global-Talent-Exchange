import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { publicUrl } from "@/lib/publicPath";
import { PlayerCard, sanitizeRealPlayerImage } from "@/components/gtex/PlayerCard";
import {
  INVENTORY_ROTATE_MS,
  ShowcasePlayer,
  buildFormationSheet,
  legendWindow,
  mapMarketPlayer,
} from "@/components/gtex/inventoryAdvertModel";

let cachedPlayers: ShowcasePlayer[] | null = null;
let inflight: Promise<ShowcasePlayer[]> | null = null;

function rowsFrom(payload: unknown): Record<string, unknown>[] {
  if (Array.isArray(payload)) return payload as Record<string, unknown>[];
  if (payload && typeof payload === "object" && Array.isArray((payload as { items?: unknown[] }).items)) {
    return (payload as { items: Record<string, unknown>[] }).items;
  }
  return [];
}

const CANONICAL_MARKETS = "https://gtex-api-2gtu.onrender.com/api/v2/players/markets";

function marketParams(source: "legend" | "real" | "regen") {
  return {
    source,
    sort: source === "regen" ? "wonderkid" : "value",
    page: 1,
    per_page: 36,
  };
}

function collectPlayers(payloads: unknown[]): ShowcasePlayer[] {
  const seen = new Set<string>();
  const players: ShowcasePlayer[] = [];
  payloads.forEach((payload) => {
    rowsFrom(payload).forEach((row) => {
      const player = mapMarketPlayer(row);
      if (!player || seen.has(player.id)) return;
      seen.add(player.id);
      players.push(player);
    });
  });
  return players;
}

function unwrapMarket(body: unknown): unknown {
  if (body && typeof body === "object" && (body as { success?: boolean }).success === true && "data" in body) {
    return (body as { data: unknown }).data;
  }
  return body;
}

async function loadInventory(): Promise<ShowcasePlayer[]> {
  if (cachedPlayers && cachedPlayers.length > 0) return cachedPlayers;
  if (!inflight) {
    inflight = (async () => {
      const sources = ["legend", "real", "regen"] as const;
      const local = Promise.all(
        sources.map((source) => api.get("/v2/players/markets", { params: marketParams(source), timeout: 20000 })),
      ).then((responses) => collectPlayers(responses.map((response) => response.data)));
      const canonical = Promise.all(
        sources.map((source) => axios.get(CANONICAL_MARKETS, { params: marketParams(source), timeout: 45000 })),
      ).then((responses) => collectPlayers(responses.map((response) => unwrapMarket(response.data))));
      const players = await new Promise<ShowcasePlayer[]>((resolve, reject) => {
        const attempts = [local, canonical];
        let pending = attempts.length;
        attempts.forEach((attempt) => {
          attempt
            .then((rows) => {
              if (rows.filter((player) => player.kind === "legend").length >= 3) resolve(rows);
              else if (--pending === 0) reject(new Error("Market inventory is not ready."));
            })
            .catch(() => {
              if (--pending === 0) reject(new Error("Market inventory is not ready."));
            });
        });
      });
      cachedPlayers = players;
      return players;
    })().catch((error) => {
      inflight = null;
      throw error;
    });
  }
  return inflight;
}

function useInventory(provided?: ShowcasePlayer[]): ShowcasePlayer[] | null {
  const [players, setPlayers] = useState<ShowcasePlayer[] | null>(provided ?? null);
  useEffect(() => {
    if (provided) {
      setPlayers(provided);
      return;
    }
    let live = true;
    loadInventory()
      .then((rows) => {
        if (live) setPlayers(rows);
      })
      .catch(() => {
        if (!live) return;
        window.setTimeout(() => {
          if (live) {
            loadInventory()
              .then((rows) => {
                if (live) setPlayers(rows);
              })
              .catch(() => {
                if (live) setPlayers([]);
              });
          }
        }, 4000);
      });
    return () => {
      live = false;
    };
  }, [provided]);
  return players;
}

function useRotateIndex(): number {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setIndex((current) => current + 1), INVENTORY_ROTATE_MS);
    return () => window.clearInterval(timer);
  }, []);
  return index;
}

function portraitOf(player: ShowcasePlayer): string | null {
  return sanitizeRealPlayerImage(player.image, player.kind === "regen");
}

export function LegendInventoryReel({
  players: provided,
  context = "owner",
}: {
  players?: ShowcasePlayer[];
  context?: "signup" | "owner";
}) {
  const players = useInventory(provided);
  const index = useRotateIndex();
  const legends = (players || [])
    .filter((player) => player.kind === "legend")
    .sort((left, right) => right.priority - left.priority);
  const windowed = legendWindow(legends, index);
  if (!players) {
    return <section data-testid="legend-inventory-reel" className="h-28 animate-pulse rounded-2xl border border-[#E5B63F]/20 bg-[#120E08]" />;
  }
  if (windowed.length === 0) return null;
  return (
    <section
      data-testid="legend-inventory-reel"
      aria-live="polite"
      className="rounded-2xl border border-[#E5B63F]/40 bg-[#120E08] p-3 shadow-[0_16px_40px_rgba(229,182,63,0.12)]"
    >
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[#E5B63F]">On the market now</p>
          <h2 className="text-lg font-black uppercase text-white">Legendary cards</h2>
          <p className="text-[11px] leading-4 text-slate-400">
            One of one. These three change every 8 seconds.
          </p>
        </div>
        {context === "owner" ? (
          <Link to="/app/market" className="shrink-0 text-[10px] font-black uppercase tracking-wider text-[#E5B63F]">
            Open market
          </Link>
        ) : (
          <span className="shrink-0 text-[10px] font-black uppercase tracking-wider text-slate-500">Advert</span>
        )}
      </div>
      <div className="flex gap-3 overflow-x-auto pb-1 md:grid md:grid-cols-3 md:overflow-visible">
        {windowed.map((player) => (
          <div key={`${index}-${player.id}`} className="w-[210px] shrink-0 md:w-auto" data-testid="legend-inventory-card">
            <p className="mb-1 text-[10px] font-black uppercase tracking-[0.16em] text-[#E5B63F]">ICON · 1 OF 1</p>
            <PlayerCard
              className="w-full"
              variant="compact"
              name={player.name}
              rating={player.rating || undefined}
              position={player.position}
              nationality={player.nationality || undefined}
              club={player.club || undefined}
              age={player.age || undefined}
              image={player.image}
              regen={player.kind === "regen"}
              tier="legendary"
              badge="ICON · 1 OF 1"
            />
          </div>
        ))}
      </div>
    </section>
  );
}

function FaceToken({
  player,
  x,
  y,
  role,
  testid,
}: {
  player: ShowcasePlayer;
  x?: number;
  y?: number;
  role?: string;
  testid: string;
}) {
  const [failed, setFailed] = useState(false);
  const image = portraitOf(player);
  const surname = player.name.split(" ").slice(-1)[0];
  const ring =
    player.kind === "legend" ? "border-[#E5B63F]" : player.kind === "regen" ? "border-emerald-300" : "border-white";
  return (
    <div
      data-testid={testid}
      className={x == null ? "w-[68px] shrink-0 text-center" : "absolute w-[68px] -translate-x-1/2 -translate-y-1/2 text-center"}
      style={x == null ? undefined : { left: `${x}%`, top: `${y}%` }}
    >
      <div className={`mx-auto h-9 w-9 overflow-hidden rounded-full border-2 ${ring} bg-slate-950 shadow-lg`}>
        {image && !failed ? (
          <img
            src={image}
            alt=""
            className="h-full w-full object-cover object-top"
            onError={() => setFailed(true)}
          />
        ) : (
          <span className="flex h-full items-center justify-center text-[10px] font-black text-white">
            {surname.slice(0, 2).toUpperCase()}
          </span>
        )}
      </div>
      <p className="mt-0.5 truncate text-[10px] font-black text-white drop-shadow">{surname}</p>
      <p className="text-[9px] font-bold uppercase text-amber-100">
        {role || player.position} · {player.rating || "—"}
      </p>
    </div>
  );
}

export function FormationInventoryAdvert({ players: provided }: { players?: ShowcasePlayer[] }) {
  const players = useInventory(provided);
  const index = useRotateIndex();
  const sheet = players ? buildFormationSheet(players, index) : null;
  if (!players) {
    return (
      <section
        data-testid="formation-inventory-advert"
        className="mx-auto my-6 max-w-7xl px-4 sm:px-6 lg:px-8"
      >
        <div className="h-40 animate-pulse rounded-3xl border border-white/10 bg-slate-900/70" />
      </section>
    );
  }
  if (!sheet) return null;
  const mix = [
    sheet.xi.some((row) => row.player.kind === "legend") ? "legends" : null,
    sheet.xi.some((row) => row.player.kind === "regen") ? "regens" : null,
    sheet.xi.some((row) => row.player.kind === "active") ? "active players" : null,
  ]
    .filter(Boolean)
    .join(", ");
  return (
    <section
      data-testid="formation-inventory-advert"
      aria-live="polite"
      className="mx-auto my-6 max-w-7xl px-4 sm:px-6 lg:px-8"
    >
      <div className="overflow-hidden rounded-3xl border border-emerald-400/30 bg-[#07140F] shadow-2xl">
        <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div className="flex items-center gap-3">
            <img
              src={publicUrl(sheet.manager.portrait)}
              alt=""
              className="h-16 w-16 rounded-full border-2 border-[#E5B63F] object-cover"
            />
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.22em] text-emerald-300">Squad advert</p>
              <h2 className="text-xl font-black uppercase text-white sm:text-2xl" data-testid="formation-inventory-manager">
                {sheet.manager.name}
              </h2>
              <p className="text-sm text-slate-300">
                {sheet.manager.formation} · {sheet.manager.style}
              </p>
            </div>
          </div>
          <div className="max-w-md text-sm leading-5 text-slate-300">
            <p>
              {mix || "Players"} from the GTEX market, arranged by {sheet.manager.name}. This sheet
              changes every 8 seconds.
            </p>
            <Link
              to="/signup"
              className="mt-2 inline-flex text-xs font-black uppercase tracking-wider text-emerald-300"
            >
              Create a club and sign from this market
            </Link>
          </div>
        </div>
        <div
          data-testid="formation-inventory-pitch"
          className="relative mx-4 mb-4 h-[520px] overflow-hidden rounded-2xl border border-white/15 sm:mx-6"
          style={{
            background:
              "repeating-linear-gradient(90deg, #147845 0 8%, #0e6438 8% 16%)",
          }}
        >
          <div className="pointer-events-none absolute inset-x-0 top-1/2 border-t border-white/40" />
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/40" />
          <div className="pointer-events-none absolute inset-x-[22%] top-0 h-16 border-x border-b border-white/40" />
          <div className="pointer-events-none absolute inset-x-[22%] bottom-0 h-16 border-x border-t border-white/40" />
          {sheet.xi.map(({ slot, player }) => (
            <FaceToken
              key={`${sheet.manager.name}-${slot.role}-${player.id}`}
              player={player}
              x={slot.x}
              y={slot.y}
              role={slot.role}
              testid="formation-face"
            />
          ))}
        </div>
        <div className="px-4 pb-5 sm:px-6" data-testid="formation-inventory-bench">
          <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Bench</p>
          <div className="flex gap-2 overflow-x-auto">
            {sheet.bench.map((player) => (
              <FaceToken key={player.id} player={player} testid="formation-bench-face" />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
