import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { InboxItem } from "@/components/gtex/InboxItem";
import { Empty, Loading, PageHeader } from "@/components/gtex/ui";
import { api } from "@/lib/api";
import { useActiveClub, useRefreshOwner } from "@/lib/owner";
import {
  Inbox,
  Clock,
  Users,
  AlertTriangle,
  Search,
  Handshake,
  Calendar,
  Archive,
  CheckCheck,
  Filter,
} from "lucide-react";

const CATEGORIES = [
  { key: "all", label: "All Items", icon: Inbox },
  { key: "requests", label: "Requests", icon: Users },
  { key: "deadlines", label: "Deadlines", icon: Clock },
  { key: "staff_recommendations", label: "Staff", icon: Users },
  { key: "player_issues", label: "Player Matters", icon: AlertTriangle },
  { key: "scouting_reports", label: "Scouting", icon: Search },
  { key: "negotiations", label: "Negotiations", icon: Handshake },
  { key: "scheduling", label: "Scheduling", icon: Calendar },
  { key: "archive", label: "Archive", icon: Archive },
];

export default function InboxPage() {
  const [status, setStatus] = useState("open");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const { clubs, active, select } = useActiveClub();
  const [selectedClubId, setSelectedClubId] = useState<string>("all");
  const refresh = useRefreshOwner();

  const isArchiveCategory = selectedCategory === "archive";
  const effectiveStatus = isArchiveCategory ? "archived" : status;

  const { data, isLoading } = useQuery({
    queryKey: ["inbox", effectiveStatus, selectedCategory, selectedClubId],
    queryFn: async () => {
      const params: any = {
        status: effectiveStatus,
      };
      if (selectedClubId !== "all") {
        params.club_id = selectedClubId;
      }
      if (selectedCategory !== "all" && selectedCategory !== "archive") {
        params.category = selectedCategory;
      }
      const res = await api.get("/owner/inbox", { params });
      return res.data;
    },
  });

  const items: any[] = data?.items || [];
  const counts = data?.counts || {};

  return (
    <div data-testid="inbox-page" className="space-y-6">
      <PageHeader
        eyebrow="Personal Owner Inbox"
        title="Command & Decisions"
        sub="Authoritative correspondence scoped to your ownership context. Review managerial recommendations, urgent deadlines, and squad issues."
        action={
          <div className="flex items-center gap-2">
            {/* Club Filter */}
            {clubs.length > 1 && (
              <select
                value={selectedClubId}
                onChange={(e) => setSelectedClubId(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-xs text-white rounded px-2.5 py-1.5 focus:outline-none focus:border-amber-400"
              >
                <option value="all">All Clubs</option>
                {clubs.map((c) => (
                  <option key={c.club_id} value={c.club_id}>
                    {c.club_name}
                  </option>
                ))}
              </select>
            )}

            {/* Status Toggles (hidden in archive view) */}
            {!isArchiveCategory && (
              <div className="flex gap-1 bg-slate-900/60 p-1 rounded-lg border border-slate-800">
                {["open", "resolved", "all"].map((s) => (
                  <button
                    key={s}
                    data-testid={`inbox-filter-${s}`}
                    onClick={() => setStatus(s)}
                    className={`px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-colors ${
                      status === s
                        ? "bg-amber-500 text-slate-950 font-bold shadow"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        }
      />

      {/* Category Tabs */}
      <div className="flex items-center space-x-1 border-b border-slate-800 pb-2 overflow-x-auto no-scrollbar">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isActive = selectedCategory === cat.key;
          return (
            <button
              key={cat.key}
              onClick={() => setSelectedCategory(cat.key)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                isActive
                  ? "bg-slate-800 text-amber-400 font-bold border border-amber-500/30"
                  : "text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{cat.label}</span>
              {cat.key === "deadlines" && counts.deadlines > 0 && (
                <span className="bg-red-500/20 text-red-400 text-[10px] px-1.5 rounded-full font-mono">
                  {counts.deadlines}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Inbox Items Feed */}
      {isLoading ? (
        <Loading />
      ) : items.length === 0 ? (
        <Empty
          title="No Messages"
          body={
            isArchiveCategory
              ? "No archived messages found."
              : "Advance the world day from the Control Center or review active matches to generate new correspondence."
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((i: any) => (
            <InboxItem key={i.id} item={i} />
          ))}
        </div>
      )}
    </div>
  );
}
