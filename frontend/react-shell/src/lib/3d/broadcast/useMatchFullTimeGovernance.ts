/**
 * Matchday end-whistle -> Owner Authority bridge.
 *
 * When the authoritative spectator stream reports `full_time` or the match live state completes,
 * ask the backend to route any gift income and post-match bonuses for the signed-in user's clubs
 * into Owner Authority governance. The client is only a trigger: the backend verifies completion
 * against the canonical match record, enforces club ownership and is idempotent, so replays,
 * reconnects and duplicate events are harmless.
 */
import { useEffect, useRef } from "react";
import { api, tokens } from "@/lib/api";
import type { SpectatorSafeEventView } from "./spectatorContract";

const FULL_TIME_TYPES = new Set(["full_time", "fulltime"]);
const MAX_ATTEMPTS = 3;
const RETRY_DELAY_MS = 4000;

export function hasFullTimeEvent(events: readonly Pick<SpectatorSafeEventView, "event_type">[] | undefined): boolean {
  return Array.isArray(events) && events.some((e) => FULL_TIME_TYPES.has(String(e?.event_type ?? "").toLowerCase()));
}

export function useMatchFullTimeGovernance(
  matchId: string | undefined,
  events: readonly Pick<SpectatorSafeEventView, "event_type">[] | undefined,
  enabled: boolean = true,
  isFullTime?: boolean,
  onGovernanceSettled?: () => void
): void {
  const settledRef = useRef<string | null>(null);
  const fullTime = Boolean(isFullTime || hasFullTimeEvent(events));

  useEffect(() => {
    if (!enabled || !matchId || !fullTime || settledRef.current === matchId || !tokens.get()) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const attempt = async (n: number): Promise<void> => {
      try {
        await api.post(`/owner/matches/${encodeURIComponent(matchId)}/full-time-governance`);
        settledRef.current = matchId;
        onGovernanceSettled?.();
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status;
        // 409: canonical record not yet completed — retry briefly. Anything else is terminal.
        if (status === 409 && n + 1 < MAX_ATTEMPTS && !cancelled) {
          timer = setTimeout(() => void attempt(n + 1), RETRY_DELAY_MS);
        } else {
          settledRef.current = matchId;
        }
      }
    };

    void attempt(0);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [matchId, fullTime, enabled, onGovernanceSettled]);
}
