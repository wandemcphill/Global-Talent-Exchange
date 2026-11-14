import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, ExternalLink, Inbox } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useRealtimeTopics } from "@/lib/realtime";

type NotificationItem = {
  notification_id: string;
  topic: string;
  message: string;
  metadata?: Record<string, any>;
  created_at: string;
  is_read: boolean;
};

function resolveNotificationRoute(n: NotificationItem, hasActiveClub: boolean): string {
  const explicit = n.metadata?.deep_link_route;
  if (typeof explicit === "string" && explicit.startsWith("/")) return explicit;
  const topic = (n.topic || "").toLowerCase();
  if (topic.startsWith("owner_") && hasActiveClub) return "/app/inbox";
  if (topic.includes("community") || topic.includes("competition") || topic.includes("pm")) {
    return "/app/community";
  }
  return hasActiveClub ? "/app/inbox" : "/app/community";
}

export function NotificationBell({
  ownerUnreadCount = 0,
  hasActiveClub = false,
}: {
  ownerUnreadCount?: number;
  hasActiveClub?: boolean;
}) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const q = useQuery({
    queryKey: ["notifications-me"],
    enabled: Boolean(user?.id),
    staleTime: 15_000,
    queryFn: async () => {
      const { data } = await api.get("/notifications/me", { params: { limit: 25 } });
      return (Array.isArray(data) ? data : []) as NotificationItem[];
    },
  });

  useRealtimeTopics(
    ["user"],
    () => {
      qc.invalidateQueries({ queryKey: ["notifications-me"] });
    },
    () => {
      qc.invalidateQueries({ queryKey: ["notifications-me"] });
    },
    Boolean(user?.id)
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const items = q.data || [];
  const unreadPlatform = items.filter((n) => !n.is_read).length;
  const totalBadge = unreadPlatform + (hasActiveClub ? ownerUnreadCount : 0);

  const openNotification = async (n: NotificationItem) => {
    try {
      if (!n.is_read) {
        await api.post(`/notifications/${n.notification_id}/read`);
        qc.invalidateQueries({ queryKey: ["notifications-me"] });
      }
      setOpen(false);
      navigate(resolveNotificationRoute(n, hasActiveClub));
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const markAllRead = async () => {
    try {
      await api.post("/notifications/read-all");
      qc.invalidateQueries({ queryKey: ["notifications-me"] });
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        data-testid="notification-bell-btn"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label="Notifications"
        onClick={() => setOpen((v) => !v)}
        className="relative flex size-8 items-center justify-center rounded-xl border border-[#25354B] bg-[#14243A] text-slate-300 transition hover:border-[#00C991]/40 hover:text-white"
        title="Notifications"
      >
        <Bell size={14} />
        {totalBadge > 0 && (
          <span
            data-testid="notification-badge"
            className="absolute -right-1 -top-1 flex min-w-4 h-4 items-center justify-center rounded-full bg-[#E5B63F] px-1 text-[9px] font-black text-slate-950"
          >
            {totalBadge > 99 ? "99+" : totalBadge}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          data-testid="notification-popover"
          className="fixed right-4 top-14 z-50 w-[min(22rem,calc(100vw-2rem))] rounded-2xl border border-[#25354B] bg-[#0E1A2C] p-3 shadow-2xl"
        >
          <div className="mb-2 flex items-center justify-between border-b border-white/10 pb-2">
            <span className="text-xs font-black uppercase tracking-wider text-white">Notifications</span>
            <div className="flex items-center gap-2">
              {unreadPlatform > 0 && (
                <button
                  type="button"
                  onClick={markAllRead}
                  className="inline-flex items-center gap-1 text-[11px] font-bold text-[#00C991] hover:underline"
                >
                  <CheckCheck size={12} /> Mark all read
                </button>
              )}
            </div>
          </div>

          {hasActiveClub && (
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                navigate("/app/inbox");
              }}
              className="mb-2 flex w-full items-center justify-between rounded-xl border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-left text-xs text-amber-200 hover:bg-amber-500/15"
            >
              <span className="flex items-center gap-2 font-bold">
                <Inbox size={13} /> Owner Inbox ({ownerUnreadCount} open)
              </span>
              <ExternalLink size={12} />
            </button>
          )}

          <div className="max-h-72 space-y-1.5 overflow-y-auto">
            {q.isLoading ? (
              <p className="py-4 text-center text-xs text-slate-400">Loading alerts...</p>
            ) : items.length === 0 ? (
              <p className="py-4 text-center text-xs text-slate-400">You are all caught up.</p>
            ) : (
              items.map((n) => (
                <button
                  key={n.notification_id}
                  type="button"
                  onClick={() => openNotification(n)}
                  className={`block w-full rounded-xl border px-3 py-2 text-left text-xs transition ${
                    n.is_read
                      ? "border-white/5 bg-slate-950/50 text-slate-400"
                      : "border-[#00C991]/40 bg-[#00C991]/10 text-slate-100"
                  }`}
                >
                  <p className="font-semibold leading-snug">{n.message}</p>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {(n.topic || "alert").replace(/_/g, " ")} ·{" "}
                    {n.created_at ? new Date(n.created_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" }) : ""}
                  </p>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
