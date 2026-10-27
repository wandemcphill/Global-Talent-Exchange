import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, Clock, Archive, ArchiveRestore, Check, Mail, MailOpen } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { label, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip } from "@/components/gtex/ui";

const KIND_TONE: any = {
  transfer_bid: "blue",
  player_unrest: "red",
  regen_breakthrough: "emerald",
  sponsor_opportunity: "gold",
  regen_endorsement: "gold",
  competition_invite: "cyan",
  facility_request: "red",
  manager_request: "cyan",
  manager_meeting: "red",
  contract_negotiation: "blue",
  scouting_lead: "emerald",
};

export function InboxItem({ item, compact = false }: any) {
  const [busy, setBusy] = useState<string | null>(null);
  const refresh = useRefreshOwner();
  const navigate = useNavigate();

  const isArchived = Boolean(item.archived_at);
  const isRead = Boolean(item.is_read);

  const decide = async (key: string) => {
    setBusy(key);
    try {
      const { data } = await api.post(`/owner/inbox/${item.id}/decide`, { action: key });
      toast.success(data.outcome || "Decision recorded");
      refresh();
      if (item.kind === "manager_request" && key === "approve") {
        navigate(`/app/market?position=${item.payload?.position || ""}`);
      }
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };

  const toggleRead = async () => {
    try {
      await api.post(`/owner/inbox/${item.id}/read`, { is_read: !isRead });
      refresh();
    } catch (e) {
      toast.error("Failed to update read status");
    }
  };

  const toggleArchive = async () => {
    try {
      await api.post(`/owner/inbox/${item.id}/archive`, { archive: !isArchived });
      toast.success(isArchived ? "Item restored to inbox" : "Item archived");
      refresh();
    } catch (e) {
      toast.error("Failed to update archive status");
    }
  };

  return (
    <article
      data-testid={`inbox-item-${item.id}`}
      className={`gx-rise rounded-xl border p-5 transition-all ${
        !isRead && item.status === "open"
          ? "bg-slate-900/90 border-amber-500/40 shadow-sm"
          : "bg-slate-950/40 border-white/[0.07]"
      }`}
    >
      <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Unread indicator */}
          {!isRead && item.status === "open" && (
            <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" title="Unread" />
          )}

          <Chip tone={KIND_TONE[item.kind] || "slate"}>{label(item.category || item.kind)}</Chip>
          {item.priority === "high" && item.status === "open" && <Chip tone="gold">Priority</Chip>}
          <span className="text-[11px] text-slate-500">from {item.sender}</span>
        </div>

        {/* Quick Read/Archive Actions */}
        <div className="flex items-center space-x-1">
          <button
            onClick={toggleRead}
            className="p-1 rounded text-slate-500 hover:text-slate-300 transition-colors"
            title={isRead ? "Mark unread" : "Mark read"}
          >
            {isRead ? <MailOpen className="w-3.5 h-3.5" /> : <Mail className="w-3.5 h-3.5 text-amber-400" />}
          </button>
          <button
            onClick={toggleArchive}
            className="p-1 rounded text-slate-500 hover:text-slate-300 transition-colors"
            title={isArchived ? "Restore to inbox" : "Archive item"}
          >
            {isArchived ? <ArchiveRestore className="w-3.5 h-3.5 text-emerald-400" /> : <Archive className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      <div className="flex items-start justify-between gap-4">
        <h4 className="font-semibold text-white text-base leading-snug">{item.title}</h4>

        {/* Deadline Badge */}
        {item.deadline_at && item.status === "open" && (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-mono shrink-0">
            <Clock className="w-3 h-3" />
            <span>Deadline Active</span>
          </span>
        )}
      </div>

      <p className="mt-2 text-sm text-slate-300">
        <span className="gx-mono mr-1.5 text-[10px] uppercase font-bold text-slate-500">What</span>
        {item.what}
      </p>

      {!compact && item.why && (
        <p className="mt-1 text-sm text-slate-400">
          <span className="gx-mono mr-1.5 text-[10px] uppercase font-bold text-slate-500">Why</span>
          {item.why}
        </p>
      )}

      {item.body && !compact && (
        <blockquote
          data-testid="inbox-item-message"
          className="mt-3 border-l-2 border-emerald-500/50 pl-3 text-sm italic text-slate-300 bg-slate-900/40 py-1.5 pr-2 rounded-r"
        >
          {item.body}
          {item.ai_generated && (
            <span className="ml-2 inline-flex items-center gap-1 align-middle text-[10px] not-italic text-slate-500">
              <Sparkles size={10} /> AI-voiced
            </span>
          )}
        </blockquote>
      )}

      {item.status === "open" && item.actions?.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2 pt-2 border-t border-slate-900">
          {item.actions.map((a: any) => (
            <Btn
              key={a.key}
              variant={a.style === "primary" ? "primary" : a.style === "secondary" ? "secondary" : "ghost"}
              disabled={!!busy}
              onClick={() => decide(a.key)}
              data-testid={`inbox-action-${a.key}-${item.id}`}
            >
              {busy === a.key ? "…" : a.label}
            </Btn>
          ))}
        </div>
      )}

      {item.status !== "open" && item.outcome && (
        <p
          data-testid="inbox-item-outcome"
          className="mt-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-2.5 text-xs text-emerald-200"
        >
          <span className="gx-mono mr-1.5 text-[10px] uppercase font-bold text-emerald-400">Outcome</span>
          {item.outcome}
        </p>
      )}
    </article>
  );
}
