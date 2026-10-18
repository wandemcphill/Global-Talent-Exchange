import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useControlCenter() {
  return useQuery({ queryKey: ["cc"], queryFn: async () => (await api.get("/owner/control-center")).data, staleTime: 15_000 });
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
  return useQuery({ queryKey: ["club", clubId], queryFn: async () => (await api.get(`/owner/clubs/${clubId}`)).data, enabled: !!clubId });
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
  };
}

export const fmt = (n: any, digits = 0) => Number(n || 0).toLocaleString("en-NG", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
export const label = (s: string) => (s || "").replace(/_/g, " ");
