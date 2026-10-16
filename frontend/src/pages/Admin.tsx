import React from "react";
import { Navigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Empty, Loading, PageHeader, Panel } from "@/components/gtex/ui";

export default function Admin() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const isAdmin = ["admin", "super_admin"].includes(String(user?.role));
  const { data, isLoading } = useQuery({ queryKey: ["admin-queue"], queryFn: async () => (await api.get("/owner/admin/review-queue")).data, enabled: isAdmin });
  if (!isAdmin) return <Navigate to="/app" replace />;
  if (isLoading || !data) return <Loading />;
  const act = async (path: string, body?: any) => {
    try {
      await api.post(path, body);
      toast.success("Recorded");
      qc.invalidateQueries({ queryKey: ["admin-queue"] });
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div data-testid="admin-page" className="space-y-6">
      <PageHeader eyebrow="Admin review" title="Trust & payouts desk" sub="Manual review path for withdrawals, integrity flags and held competition payouts." />
      <Panel eyebrow="Fraud review" title={`Withdrawals (${data.withdrawals.length})`} testid="admin-withdrawals">
        {data.withdrawals.length === 0 ? <Empty title="Queue clear" /> : data.withdrawals.map((w: any) => (
          <div key={w.id} className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 p-4" data-testid={`admin-withdrawal-${w.id}`}>
            <div>
              <p className="text-white">{fmt(w.amount_coin)} GTX (₦{fmt(w.amount_ngn)}) → {w.bank_name} ****{w.account_last4} · {w.account_name}</p>
              <div className="mt-1 flex flex-wrap gap-1">{Object.entries(w.checks?.risk || {}).map(([k, v]: any) => <Chip key={k} tone={v ? "red" : "slate"}>{label(k)}</Chip>)}<Chip tone="blue">Integrity {w.checks?.integrity_score}</Chip><Chip>{label(w.status)}</Chip></div>
            </div>
            <div className="flex gap-2">
              <Btn onClick={() => act(`/owner/admin/withdrawals/${w.id}/review`, { decision: "approve" })} data-testid={`approve-withdrawal-${w.id}`}>Approve</Btn>
              <Btn variant="secondary" onClick={() => act(`/owner/admin/withdrawals/${w.id}/review`, { decision: "hold" })} data-testid={`hold-withdrawal-${w.id}`}>Hold</Btn>
              <Btn variant="danger" onClick={() => act(`/owner/admin/withdrawals/${w.id}/review`, { decision: "reject" })} data-testid={`reject-withdrawal-${w.id}`}>Reject</Btn>
            </div>
          </div>
        ))}
      </Panel>
      <Panel eyebrow="Anti-collusion" title={`Integrity flags (${data.flags.length})`} testid="admin-flags">
        {data.flags.length === 0 ? <Empty title="No open flags" /> : data.flags.map((f: any) => (
          <div key={f.id} className="mb-2 flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 p-3">
            <p className="text-sm text-slate-200"><Chip tone={f.severity === "high" ? "red" : "gold"}>{f.severity}</Chip> <b className="capitalize">{label(f.flag_type)}</b> · {f.detail}</p>
            <div className="flex gap-2"><Btn variant="secondary" onClick={() => act(`/owner/admin/flags/${f.id}/clear`)} data-testid={`clear-flag-${f.id}`}>Clear</Btn><Btn variant="danger" onClick={() => act(`/owner/admin/flags/${f.id}/action`)} data-testid={`action-flag-${f.id}`}>Uphold</Btn></div>
          </div>
        ))}
      </Panel>
      <Panel eyebrow="Payout holds" title={`Held payouts (${data.held_payouts.length})`} testid="admin-held-payouts">
        {data.held_payouts.length === 0 ? <Empty title="Nothing held" /> : data.held_payouts.map((e: any) => (
          <div key={e.id} className="mb-2 flex items-center justify-between rounded-sm border border-white/10 p-3 text-sm">
            <span>{label(e.event_type)} · {fmt(e.net_amount)} GTX · {e.memo}</span>
            <Btn onClick={() => act(`/owner/admin/payouts/${e.id}/release`)} data-testid={`release-payout-${e.id}`}>Release</Btn>
          </div>
        ))}
      </Panel>
    </div>
  );
}
