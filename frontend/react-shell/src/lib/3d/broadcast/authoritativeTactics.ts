/**
 * Maps the authoritative applied-tactics payload of `GET /matches/{id}/tactics`
 * (backend/app/live_matches/router.py `read_match_v2_tactics`) to the renderer's
 * `TacticalVisualConfig`.
 *
 * Contract (UpdateMatchTacticsRequest / hub.get_tactics):
 *   - press_intensity, defensive_line, tempo, risk_level: numeric 0..100
 *   - formation: string such as "4-3-3"
 *   - there is NO width field; `risk_level` is NOT tactical width and is never mapped to it.
 *
 * Only values the backend reports as applied are passed on. Unsupplied or malformed
 * fields are omitted so the renderer never fabricates a tactical effect.
 */
import type { TacticalVisualConfig } from "./SpatialInterpolator";

const FORMATION_RE = /^\d(-\d){2,4}$/;

function numeric0to100(value: unknown): number | undefined {
  const n = typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
  if (!Number.isFinite(n)) return undefined;
  return Math.min(100, Math.max(0, n));
}

function formationLabel(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const v = value.trim();
  return FORMATION_RE.test(v) ? v : undefined;
}

export function mapAuthoritativeTactics(payload: unknown): TacticalVisualConfig | null {
  const p = (payload as any)?.data ?? payload;
  if (!p || typeof p !== "object") return null;
  const cfg: Record<string, string | number> = {};
  for (const side of ["home", "away"] as const) {
    const t = (p as any)[side];
    if (!t || typeof t !== "object") continue;
    const cap = side === "home" ? "home" : "away";
    const f = formationLabel(t.formation);
    const press = numeric0to100(t.press_intensity);
    const line = numeric0to100(t.defensive_line);
    const tempo = numeric0to100(t.tempo);
    if (f !== undefined) cfg[`${cap}Formation`] = f;
    if (press !== undefined) cfg[`${cap}Pressing`] = press;
    if (line !== undefined) cfg[`${cap}DefensiveLine`] = line;
    if (tempo !== undefined) cfg[`${cap}Tempo`] = tempo;
  }
  return Object.keys(cfg).length > 0 ? (cfg as TacticalVisualConfig) : null;
}
