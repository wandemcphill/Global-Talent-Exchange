import axios from "axios";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { GtexLiveWorldPulse } from "./landingModels";

function readCount(data: Record<string, unknown>, ...keys: string[]): number | null {
  for (const key of keys) {
    const value = data[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

export function mapLiveWorldPulse(payload: unknown): GtexLiveWorldPulse | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  const envelope = payload as Record<string, unknown>;
  const nested =
    envelope.data && typeof envelope.data === "object" && !Array.isArray(envelope.data)
      ? (envelope.data as Record<string, unknown>)
      : null;
  const data = nested ?? envelope;
  const hasPulse =
    data.clubs_on_gtex != null ||
    data.clubsOnGtex != null ||
    data.users_online != null ||
    data.usersOnline != null ||
    data.visitors_today != null ||
    data.visitorsToday != null;
  if (!hasPulse) return null;

  const visitorsToday = readCount(data, "visitors_today", "visitorsToday");
  const pageViewsToday = readCount(data, "page_views_today", "pageViewsToday");
  const generatedAt = data.generated_at ?? data.generatedAt;
  const labels = data.labels;

  return {
    clubsOnGtex: readCount(data, "clubs_on_gtex", "clubsOnGtex") ?? 0,
    usersOnline: readCount(data, "users_online", "usersOnline") ?? 0,
    playersOnline: readCount(data, "players_online", "playersOnline") ?? 0,
    visitorsToday,
    pageViewsToday,
    visitors: {
      today: visitorsToday,
      last7Days: readCount(data, "visitors_last_7_days", "visitorsLast7Days"),
      last30Days: readCount(data, "visitors_last_30_days", "visitorsLast30Days"),
      allTime: readCount(data, "visitors_all_time", "visitorsAllTime"),
    },
    pageViews: {
      today: pageViewsToday,
      last7Days: readCount(data, "page_views_last_7_days", "pageViewsLast7Days"),
      last30Days: readCount(data, "page_views_last_30_days", "pageViewsLast30Days"),
      allTime: readCount(data, "page_views_all_time", "pageViewsAllTime"),
    },
    registeredUsers: readCount(data, "registered_users", "registeredUsers"),
    usersOnlineWindowSeconds: readCount(data, "users_online_window_seconds", "usersOnlineWindowSeconds") ?? 90,
    generatedAt: typeof generatedAt === "string" ? generatedAt : undefined,
    labels: labels && typeof labels === "object" && !Array.isArray(labels) ? (labels as Record<string, string>) : undefined,
  };
}

export function useLiveWorldPulse(): GtexLiveWorldPulse | null {
  const [pulse, setPulse] = useState<GtexLiveWorldPulse | null>(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await axios.get(`${API}/public/live-stats`, { timeout: 3000 });
        const mapped = mapLiveWorldPulse(res.data);
        if (mounted && mapped) setPulse(mapped);
      } catch {
        // Never invent public numbers when the live stats request fails.
      }
    };
    void load();
    const interval = window.setInterval(() => void load(), 30_000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  return pulse;
}
