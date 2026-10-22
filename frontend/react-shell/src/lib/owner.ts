import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function useControlCenter() {
  const { user, loading } = useAuth();
  const userId = user?.id ? String(user.id) : null;
  const accountType = String(user?.account_type || user?.accountType || "user").toLowerCase();
  return useQuery({
    queryKey: ["cc", userId],
    queryFn: async () => (await api.get("/owner/control-center")).data,
    enabled: !loading && Boolean(userId) && accountType === "user",
    staleTime: 15_000,
  });
}

export function useActiveClub() {
  const { data } = useControlCenter();
  const [stored, setStored] = useState<string | null>(() => localStorage.getItem("gtex_active_club"));
  const clubs: any[] = data?.clubs || [];
  const active = clubs.find((c) => c.club_id === stored) || clubs[0] || null;
  useEffect(() => {
    if (active && active.club_id !== stored) localStorage.setItem("gtex_active_club", active.club_id);
  }, [active, stored]);
  const select = (id: string) => {
    localStorage.setItem("gtex_active_club", id);
    setStored(id);
  };
  return { clubs, active, select };
}

export function useClub(clubId?: string) {
  return useQuery({
    queryKey: ["club", clubId],
    queryFn: async () => (await api.get(`/owner/clubs/${clubId}`)).data,
    enabled: !!clubId,
  });
}

export function useGlobalTicker(clubId?: string, limit = 20) {
  return useQuery({
    queryKey: ["ticker", clubId, limit],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (clubId) params.set("club_id", clubId);
      params.set("limit", String(limit));
      return (await api.get(`/owner/ticker?${params.toString()}`)).data;
    },
    refetchInterval: 10_000,
  });
}

export function useNewsroom(clubId?: string, category?: string, limit = 20) {
  return useQuery({
    queryKey: ["newsroom", clubId, category, limit],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (clubId) params.set("club_id", clubId);
      if (category && category !== "all") params.set("category", category);
      params.set("limit", String(limit));
      return (await api.get(`/owner/newsroom?${params.toString()}`)).data;
    },
    staleTime: 20_000,
  });
}

export function useClubStory(clubId?: string) {
  return useQuery({
    queryKey: ["story", clubId],
    queryFn: async () => (await api.get(`/owner/clubs/${clubId}/story`)).data,
    enabled: !!clubId,
  });
}

export function useClubShowroom(clubId?: string) {
  return useQuery({
    queryKey: ["showroom", clubId],
    queryFn: async () => (await api.get(`/owner/clubs/${clubId}/showroom`)).data,
    enabled: !!clubId,
  });
}

export function useWatchlist(clubId?: string) {
  return useQuery({
    queryKey: ["watchlist", clubId],
    queryFn: async () => (await api.get(`/owner/clubs/${clubId}/watchlist`)).data,
    enabled: !!clubId,
  });
}

export function useRefreshOwner() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["cc"] });
    qc.invalidateQueries({ queryKey: ["club"] });
    qc.invalidateQueries({ queryKey: ["finance"] });
    qc.invalidateQueries({ queryKey: ["inbox"] });
    qc.invalidateQueries({ queryKey: ["competition"] });
    qc.invalidateQueries({ queryKey: ["competitions"] });
    qc.invalidateQueries({ queryKey: ["ticker"] });
    qc.invalidateQueries({ queryKey: ["newsroom"] });
    qc.invalidateQueries({ queryKey: ["story"] });
    qc.invalidateQueries({ queryKey: ["showroom"] });
    qc.invalidateQueries({ queryKey: ["watchlist"] });
  };
}

export const fmt = (n: any, digits = 0) =>
  Number(n || 0).toLocaleString("en-NG", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
export const label = (s: string) => (s || "").replace(/_/g, " ");
