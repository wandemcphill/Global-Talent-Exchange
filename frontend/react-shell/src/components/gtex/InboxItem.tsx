import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";
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
};

export function InboxItem({ item, compact = false }: any) {
  const [busy, setBusy] = useState<string | null>(null);
  const refresh = useRefreshOwner();
  const navigate = useNavigate();
  const decide = async (key: string) => {
    setBusy(key);
    try {
      const { data } = await api.post(`/owner/inbox/${item.id}/decide`, { action: key });
      toast.success(data.outcome || "Decision recorded");
      refresh();
      if (item.kind === "manager_request" && key === "approve") navigate(`/app/market?position=${item.payload?.position || ""}`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <article data-testid={`inbox-item-${item.id}`} className={`gx-rise rounded-sm border bg-slate-950/40 p-4 ${item.priority === "high" && item.status === "open" ? "border-amber-500/30" : "border-white/[0.07]"}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Chip tone={KIND_TONE[item.kind] || "slate"}>{label(item.kind)}</Chip>
        {item.priority === "high" && item.status === "open" && <Chip tone="gold">Priority</Chip>}
        <span className="text-[11px] text-slate-500">from {item.sender}</span>
      </div>
      <h4 className="font-semibold text-white">{item.title}</h4>
      <p className="mt-1 text-sm text-slate-300">
        <span className="gx-mono mr-1 text-[10px] uppercase text-slate-500">What</span>
        {item.what}
      </p>
      {!compact && (
        <p className="mt-1 text-sm text-slate-400">
          <span className="gx-mono mr-1 text-[10px] uppercase text-slate-500">Why</span>
          {item.why}
        </p>
      )}
      {item.body && !compact && (
        <blockquote data-testid="inbox-item-message" className="mt-3 border-l-2 border-emerald-500/50 pl-3 text-sm italic text-slate-300">
          {item.body}
          {item.ai_generated && (
            <span className="ml-2 inline-flex items-center gap-1 align-middle text-[10px] not-italic text-slate-500">
              <Sparkles size={10} /> AI-voiced
            </span>
          )}
        </blockquote>
      )}
      {item.status === "open" && item.actions?.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {item.actions.map((a: any) => (
            <Btn key={a.key} variant={a.style === "primary" ? "primary" : a.style === "secondary" ? "secondary" : "ghost"} disabled={!!busy} onClick={() => decide(a.key)} data-testid={`inbox-action-${a.key}-${item.id}`}>
              {busy === a.key ? "…" : a.label}
            </Btn>
          ))}
        </div>
      )}
      {item.status !== "open" && item.outcome && (
        <p data-testid="inbox-item-outcome" className="mt-3 rounded-sm bg-emerald-500/5 p-2 text-sm text-emerald-200">
          <span className="gx-mono mr-1 text-[10px] uppercase text-emerald-500">Outcome</span>
          {item.outcome}
        </p>
      )}
    </article>
  );
}
