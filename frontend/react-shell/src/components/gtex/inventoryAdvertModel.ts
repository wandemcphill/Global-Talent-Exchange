export const INVENTORY_ROTATE_MS = 8000;

export type InventoryKind = "legend" | "regen" | "active";
export type InventoryLine = "GK" | "DEF" | "MID" | "FWD";

export interface ShowcasePlayer {
  id: string;
  name: string;
  position: string;
  rating: number;
  image: string | null;
  nationality: string | null;
  club: string | null;
  age: number | null;
  kind: InventoryKind;
  priority: number;
}

export interface FormationSlot {
  role: string;
  x: number;
  y: number;
  line: InventoryLine;
}

export interface InventoryManager {
  name: string;
  formation: string;
  style: string;
  portrait: string;
}

export const INVENTORY_MANAGERS: InventoryManager[] = [
  {
    name: "Sir Alex Ferguson",
    formation: "4-4-2",
    style: "Direct control",
    portrait: "/staff-portraits/real/sir-alex-ferguson.jpg",
  },
  {
    name: "Arsène Wenger",
    formation: "4-2-3-1",
    style: "Technical build-up",
    portrait: "/staff-portraits/real/arsene-wenger.jpg",
  },
  {
    name: "Marcello Lippi",
    formation: "4-4-2",
    style: "Tournament shape",
    portrait: "/staff-portraits/real/marcello-lippi.jpg",
  },
  {
    name: "Pep Guardiola",
    formation: "4-3-3",
    style: "Positional control",
    portrait: "/staff-portraits/real/pep-guardiola.jpg",
  },
  {
    name: "José Mourinho",
    formation: "4-2-3-1",
    style: "Compact counter",
    portrait: "/staff-portraits/real/jose-mourinho.jpg",
  },
  {
    name: "Arrigo Sacchi",
    formation: "4-4-2",
    style: "Collective press",
    portrait: "/staff-portraits/real/arrigo-sacchi.jpg",
  },
  {
    name: "Johan Cruyff",
    formation: "3-4-3",
    style: "Total football",
    portrait: "/staff-portraits/real/johan-cruyff.jpg",
  },
  {
    name: "Jürgen Klopp",
    formation: "4-3-3",
    style: "High press",
    portrait: "/staff-portraits/real/jurgen-klopp.jpg",
  },
  {
    name: "Carlo Ancelotti",
    formation: "4-3-3",
    style: "Star management",
    portrait: "/staff-portraits/real/carlo-ancelotti.jpg",
  },
  {
    name: "Vicente del Bosque",
    formation: "4-2-3-1",
    style: "Calm authority",
    portrait: "/staff-portraits/real/vicente-del-bosque.jpg",
  },
];

const FORMATIONS: Record<string, FormationSlot[]> = {
  "4-4-2": [
    { role: "GK", x: 50, y: 90, line: "GK" },
    { role: "LB", x: 12, y: 68, line: "DEF" },
    { role: "CB", x: 36, y: 72, line: "DEF" },
    { role: "CB", x: 64, y: 72, line: "DEF" },
    { role: "RB", x: 88, y: 68, line: "DEF" },
    { role: "LM", x: 12, y: 44, line: "MID" },
    { role: "CM", x: 36, y: 48, line: "MID" },
    { role: "CM", x: 64, y: 48, line: "MID" },
    { role: "RM", x: 88, y: 44, line: "MID" },
    { role: "ST", x: 36, y: 18, line: "FWD" },
    { role: "ST", x: 64, y: 18, line: "FWD" },
  ],
  "4-3-3": [
    { role: "GK", x: 50, y: 90, line: "GK" },
    { role: "LB", x: 12, y: 68, line: "DEF" },
    { role: "CB", x: 36, y: 72, line: "DEF" },
    { role: "CB", x: 64, y: 72, line: "DEF" },
    { role: "RB", x: 88, y: 68, line: "DEF" },
    { role: "CM", x: 26, y: 46, line: "MID" },
    { role: "CM", x: 50, y: 50, line: "MID" },
    { role: "CM", x: 74, y: 46, line: "MID" },
    { role: "LW", x: 16, y: 18, line: "FWD" },
    { role: "ST", x: 50, y: 14, line: "FWD" },
    { role: "RW", x: 84, y: 18, line: "FWD" },
  ],
  "4-2-3-1": [
    { role: "GK", x: 50, y: 90, line: "GK" },
    { role: "LB", x: 12, y: 70, line: "DEF" },
    { role: "CB", x: 36, y: 74, line: "DEF" },
    { role: "CB", x: 64, y: 74, line: "DEF" },
    { role: "RB", x: 88, y: 70, line: "DEF" },
    { role: "DM", x: 34, y: 52, line: "MID" },
    { role: "DM", x: 66, y: 52, line: "MID" },
    { role: "LW", x: 16, y: 30, line: "FWD" },
    { role: "AM", x: 50, y: 28, line: "MID" },
    { role: "RW", x: 84, y: 30, line: "FWD" },
    { role: "ST", x: 50, y: 12, line: "FWD" },
  ],
  "3-4-3": [
    { role: "GK", x: 50, y: 90, line: "GK" },
    { role: "CB", x: 26, y: 70, line: "DEF" },
    { role: "CB", x: 50, y: 74, line: "DEF" },
    { role: "CB", x: 74, y: 70, line: "DEF" },
    { role: "LM", x: 10, y: 46, line: "MID" },
    { role: "CM", x: 34, y: 50, line: "MID" },
    { role: "CM", x: 66, y: 50, line: "MID" },
    { role: "RM", x: 90, y: 46, line: "MID" },
    { role: "LW", x: 20, y: 18, line: "FWD" },
    { role: "ST", x: 50, y: 12, line: "FWD" },
    { role: "RW", x: 80, y: 18, line: "FWD" },
  ],
};

const KINDS: InventoryKind[] = ["legend", "regen", "active"];

export function lineOf(position?: string | null): InventoryLine {
  const raw = String(position || "").toLowerCase();
  if (/gk|goalkeep/.test(raw)) return "GK";
  if (/st|striker|centre-forward|center-forward|\bcf\b|\bfw\b|forward|winger|\blw\b|\brw\b/.test(raw)) {
    return "FWD";
  }
  if (/def|back|\bcb\b|\blb\b|\brb\b|\bwb\b/.test(raw)) return "DEF";
  return "MID";
}

export function legendWindow(legends: ShowcasePlayer[], index: number): ShowcasePlayer[] {
  if (legends.length === 0) return [];
  const count = Math.min(3, legends.length);
  const start = legends.length <= 3 ? 0 : (index * 3) % legends.length;
  return Array.from({ length: count }, (_, step) => legends[(start + step) % legends.length]);
}

function pick(
  players: ShowcasePlayer[],
  line: InventoryLine,
  prefer: InventoryKind,
  used: Set<string>,
  offset: number,
): ShowcasePlayer | null {
  const open = players.filter((player) => !used.has(player.id));
  const onLine = open.filter((player) => lineOf(player.position) === line);
  const preferred = onLine.filter((player) => player.kind === prefer);
  const list = preferred.length > 0 ? preferred : onLine.length > 0 ? onLine : open;
  if (list.length === 0) return null;
  const ranked = [...list].sort((left, right) => right.priority - left.priority);
  return ranked[Math.abs(offset) % ranked.length];
}

export interface FormationSheet {
  manager: InventoryManager;
  xi: Array<{ slot: FormationSlot; player: ShowcasePlayer }>;
  bench: ShowcasePlayer[];
}

export function buildFormationSheet(
  players: ShowcasePlayer[],
  index: number,
  managers: InventoryManager[] = INVENTORY_MANAGERS,
): FormationSheet | null {
  if (managers.length === 0 || players.length < 11) return null;
  const manager = managers[Math.abs(index) % managers.length];
  const slots = FORMATIONS[manager.formation];
  if (!slots) return null;
  const used = new Set<string>();
  const xi: FormationSheet["xi"] = [];
  for (let slotIndex = 0; slotIndex < slots.length; slotIndex += 1) {
    const slot = slots[slotIndex];
    const player = pick(players, slot.line, KINDS[(slotIndex + index) % KINDS.length], used, index + slotIndex);
    if (!player) return null;
    used.add(player.id);
    xi.push({ slot, player });
  }
  const bench: ShowcasePlayer[] = [];
  const benchLines: InventoryLine[] = ["GK", "DEF", "MID", "FWD", "DEF", "MID", "FWD"];
  for (let benchIndex = 0; benchIndex < benchLines.length; benchIndex += 1) {
    const player = pick(
      players,
      benchLines[benchIndex],
      KINDS[(benchIndex + index + 1) % KINDS.length],
      used,
      index + 11 + benchIndex,
    );
    if (!player) break;
    used.add(player.id);
    bench.push(player);
  }
  return { manager, xi, bench };
}

export function mapMarketPlayer(raw: Record<string, unknown> | null | undefined): ShowcasePlayer | null {
  if (!raw) return null;
  const tier = String(raw.real_player_tier || "").toLowerCase();
  if (tier === "archived_duplicate") return null;
  const id = String(raw.player_id || raw.id || "").trim();
  const name = String(raw.player_name || raw.full_name || raw.name || "").trim();
  if (!id || !name) return null;
  const regen = Boolean(raw.is_regen) || tier === "regen";
  const legend = Boolean(raw.is_legend) || tier === "legend";
  const marquee = tier === "marquee";
  const ratingValue = Number(raw.rating ?? raw.overall ?? 0);
  const rating = Number.isFinite(ratingValue) ? ratingValue : 0;
  return {
    id,
    name,
    position: String(raw.position || "MID"),
    rating,
    image: typeof raw.image_url === "string" ? raw.image_url : typeof raw.portrait_url === "string" ? raw.portrait_url : null,
    nationality: raw.nationality ? String(raw.nationality) : null,
    club: raw.current_club_name ? String(raw.current_club_name) : null,
    age: raw.age == null ? null : Number(raw.age),
    kind: legend ? "legend" : regen ? "regen" : "active",
    priority: rating + (legend ? 400 : marquee ? 250 : regen ? 80 : 120),
  };
}
