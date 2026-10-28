import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

/**
 * Typed client for the authoritative GTEX world clock.
 *
 * Contract: `GET /api/world/clock` (Global-Talent-Exchange PR #347, backend/app/world_simulation).
 * The browser/device clock is NEVER used to derive game time. The UI renders only the snapshot the
 * server returned and refreshes it by re-reading the endpoint.
 */
export const WORLD_CLOCK_PATH = "/world/clock";

export type WorldClock = {
  clockId: string;
  /** Server-issued virtual UTC instant, ISO-8601 with an explicit offset. */
  worldTime: string;
  /** Server-issued virtual calendar date, YYYY-MM-DD. */
  worldDate: string;
  isPaused: boolean;
  progressionRate: number;
  virtualMonthsPerSeason: number;
  currentSeasonLabel?: string;
  currentSeasonNumber?: number;
  gtexYearsRunning?: number;
};

export class WorldClockContractError extends Error {
  constructor(message: string) {
    super(`world_clock_contract_violation: ${message}`);
    this.name = "WorldClockContractError";
  }
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const ISO_DATETIME_WITH_OFFSET = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/;

/** Validate the raw response strictly; anything outside the published schema is rejected, not guessed. */
export function parseWorldClock(raw: unknown): WorldClock {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new WorldClockContractError("response is not an object");
  }
  const r = raw as Record<string, unknown>;
  if (typeof r.clock_id !== "string" || !r.clock_id.trim()) {
    throw new WorldClockContractError("clock_id missing");
  }
  if (typeof r.world_time !== "string" || !ISO_DATETIME_WITH_OFFSET.test(r.world_time)) {
    throw new WorldClockContractError("world_time must be an ISO timestamp with an explicit UTC offset");
  }
  const instant = new Date(r.world_time);
  if (Number.isNaN(instant.getTime())) {
    throw new WorldClockContractError("world_time is not a valid instant");
  }
  if (typeof r.world_date !== "string" || !ISO_DATE.test(r.world_date)) {
    throw new WorldClockContractError("world_date must be YYYY-MM-DD");
  }
  if (instant.toISOString().slice(0, 10) !== r.world_date) {
    throw new WorldClockContractError("world_date does not match the UTC date of world_time");
  }
  if (typeof r.is_paused !== "boolean") {
    throw new WorldClockContractError("is_paused must be a boolean");
  }
  if (typeof r.progression_rate !== "number" || !Number.isFinite(r.progression_rate) || r.progression_rate <= 0) {
    throw new WorldClockContractError("progression_rate must be a positive number");
  }
  if (
    typeof r.virtual_months_per_season !== "number" ||
    !Number.isInteger(r.virtual_months_per_season) ||
    r.virtual_months_per_season < 1
  ) {
    throw new WorldClockContractError("virtual_months_per_season must be an integer >= 1");
  }
  const res: WorldClock = {
    clockId: r.clock_id,
    worldTime: r.world_time,
    worldDate: r.world_date,
    isPaused: r.is_paused,
    progressionRate: r.progression_rate,
    virtualMonthsPerSeason: r.virtual_months_per_season,
  };
  if (typeof r.current_season_label === "string" && r.current_season_label.trim()) {
    res.currentSeasonLabel = r.current_season_label.trim();
  }
  if (typeof r.current_season_number === "number") {
    res.currentSeasonNumber = r.current_season_number;
  }
  if (typeof r.gtex_years_running === "number") {
    res.gtexYearsRunning = r.gtex_years_running;
  }
  return res;
}

export async function fetchWorldClock(): Promise<WorldClock> {
  const { data } = await api.get(WORLD_CLOCK_PATH);
  return parseWorldClock(data);
}

/** Format the server's virtual date in UTC so the viewer's timezone cannot shift it. */
export function formatWorldDate(worldDate: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    weekday: "short",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(`${worldDate}T00:00:00Z`));
}

/** Format the server's virtual time-of-day, always in UTC. */
export function formatWorldTime(worldTime: string): string {
  return `${new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(worldTime))} UTC`;
}

export function formatProgressionRate(rate: number): string {
  return `${Number(rate.toFixed(4))}x`;
}

export const WORLD_CLOCK_QUERY_KEY = ["world-clock"] as const;

/**
 * Reads the server snapshot. The interval only re-reads the server; it never advances or
 * extrapolates time locally.
 */
export function useWorldClock() {
  return useQuery({
    queryKey: WORLD_CLOCK_QUERY_KEY,
    queryFn: fetchWorldClock,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}
