import React from "react";

type TouchlinePlayer = {
  player_id?: string;
  id?: string;
  playerId?: string;
  name?: string;
  player_name?: string;
  role?: string;
  line?: string;
  shirt_number?: number;
  shirtNumber?: number;
  stamina_pct?: number | null;
  staminaPct?: number | null;
  rating?: number | null;
};

function surname(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts[parts.length - 1] || name).toUpperCase();
}

function roleTag(role?: string, line?: string): string {
  const raw = `${role || ""} ${line || ""}`.toLowerCase();
  if (/gk|goal/.test(raw)) return "GK";
  if (/wing.?back|wb/.test(raw)) return "WB";
  if (/full.?back|fb|left back|right back/.test(raw)) return "FB";
  if (/centre.?back|center.?back|cb|def/.test(raw)) return "CB";
  if (/attacking mid|am\b|number 10|10/.test(raw)) return "AM";
  if (/defensive mid|dm\b|holding/.test(raw)) return "DM";
  if (/mid/.test(raw)) return "CM";
  if (/wing|wide/.test(raw)) return "W";
  if (/str|forward|att/.test(raw)) return "ST";
  return "XI";
}

function heartColor(stamina: number | null): string {
  if (stamina == null) return "#94a3b8";
  if (stamina >= 70) return "#34d399";
  if (stamina >= 45) return "#fbbf24";
  return "#fb7185";
}

export function ClassicTouchline({
  players,
  kitColor,
}: {
  players: TouchlinePlayer[];
  kitColor: string;
}) {
  const row = players.slice(0, 11);
  if (row.length === 0) return null;
  return (
    <div
      data-testid="classic-touchline"
      className="mt-2 flex gap-1 overflow-x-auto rounded-md border border-white/10 bg-[#0c1222] px-2 py-2"
    >
      {row.map((player, index) => {
        const name = String(player.player_name || player.name || "").trim();
        const shirt = Number(player.shirt_number || player.shirtNumber || 0);
        const staminaRaw = player.stamina_pct ?? player.staminaPct;
        const stamina = typeof staminaRaw === "number" && Number.isFinite(staminaRaw) ? staminaRaw : null;
        const rating = typeof player.rating === "number" && Number.isFinite(player.rating) ? player.rating : null;
        const key = String(player.player_id || player.playerId || player.id || `${shirt}-${index}`);
        return (
          <div key={key} className="flex w-[92px] shrink-0 flex-col items-center gap-0.5 text-center">
            <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">
              {roleTag(player.role, player.line)}
            </span>
            <span className="w-full truncate text-[10px] font-black uppercase text-slate-100">
              {name ? surname(name) : shirt ? `#${shirt}` : "Player"}
            </span>
            <span
              className="mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-sm text-[9px] font-black text-slate-950"
              style={{ backgroundColor: kitColor }}
            >
              {shirt || "•"}
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-300">
              <span aria-hidden="true" style={{ color: heartColor(stamina) }}>
                ♥
              </span>
              {stamina == null ? "—" : Math.round(stamina)}
            </span>
            <span className="text-[11px] font-black text-white">{rating == null ? "—" : rating.toFixed(1)}</span>
          </div>
        );
      })}
    </div>
  );
}
