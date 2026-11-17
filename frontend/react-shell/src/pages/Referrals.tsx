import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Copy, Share2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Loading, Panel } from "@/components/gtex/ui";

const LANE_LABEL: Record<string, string> = {
  user: "Member",
  creator: "Creator",
  coin_trader: "Coin trader",
  club_owner: "Club owner",
};

function money(record: Record<string, string> | undefined): string {
  const entries = Object.entries(record || {});
  if (entries.length === 0) return "0";
  return entries.map(([currency, amount]) => `${currency} ${amount}`).join(" · ");
}

export default function Referrals() {
  const { user } = useAuth();
  const accountType = String(user?.account_type || user?.accountType || "user").toLowerCase();
  const clubs = useQuery({
    queryKey: ["referral-owned-clubs", user?.id],
    queryFn: async () => (await api.get("/owner/onboarding")).data,
    enabled: Boolean(user?.id) && accountType === "user",
    retry: false,
  });
  const ownsClub = accountType === "user" && Array.isArray(clubs.data?.clubs) && clubs.data.clubs.length > 0;
  const lane = ownsClub ? "Club owner" : (LANE_LABEL[accountType] || "Member");
  const [copied, setCopied] = useState<"code" | "link" | null>(null);
  const query = useQuery({
    queryKey: ["my-affiliate", user?.id],
    queryFn: async () => (await api.get("/referrals/me/affiliate")).data,
    enabled: Boolean(user?.id),
    retry: false,
  });

  const copy = async (value: string, kind: "code" | "link") => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(kind);
      toast.success(kind === "code" ? "Referral code copied" : "Referral link copied");
    } catch {
      toast.error("Could not copy. Select the code and copy it manually.");
    }
  };

  if (query.isLoading) return <Loading label="Loading your referral programme..." />;

  const data = query.data;
  return (
    <div className="space-y-6 p-4 sm:p-8" data-testid="referrals-screen">
      <section className="rounded-3xl border border-cyan-400/20 bg-[#101522] p-6">
        <p className="gx-eyebrow text-cyan-300" data-testid="referrals-account-lane">{lane}</p>
        <h1 className="mt-2 text-3xl font-black text-white">Your referral programme</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          Members, club owners, creators, and coin traders share the same first-deposit programme.
          Someone who registers with your code receives a 10% bonus on their first qualifying deposit.
          You earn a 10% commission on that same deposit after review.
        </p>
      </section>

      {query.isError && (
        <Panel eyebrow="Referral programme" title="Could not load your referral record">
          <p className="text-sm text-red-300" data-testid="referrals-error">{errMsg(query.error)}</p>
        </Panel>
      )}

      {data && (
        <>
          <Panel eyebrow="Share" title="Your code and link">
            <p className="text-sm text-slate-300">{data.explanation}</p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <code className="rounded-lg bg-black/40 px-3 py-2 text-lg font-bold text-white" data-testid="referrals-code">
                {data.code}
              </code>
              <button type="button" className="gx-btn-primary" onClick={() => copy(data.code, "code")} data-testid="referrals-copy-code">
                <Copy size={14} /> {copied === "code" ? "Copied" : "Copy code"}
              </button>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <span className="break-all text-sm text-cyan-200" data-testid="referrals-link">{data.link}</span>
              <button type="button" className="gx-btn-secondary" onClick={() => copy(data.link, "link")} data-testid="referrals-copy-link">
                <Share2 size={14} /> {copied === "link" ? "Copied" : "Copy link"}
              </button>
            </div>
          </Panel>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Panel eyebrow="Registrations" title={String(data.registrations)}><p className="text-xs text-slate-400">Accounts attributed to you</p></Panel>
            <Panel eyebrow="Qualifying deposits" title={String(data.qualifying_deposits)}><p className="text-xs text-slate-400">First deposits only</p></Panel>
            <Panel eyebrow="Referred volume" title={money(data.referred_deposit_volume)}><p className="text-xs text-slate-400">Gross verified fiat, not wallet credit</p></Panel>
            <Panel eyebrow="Pending" title={money(data.pending_commission)}><p className="text-xs text-slate-400">Held for review</p></Panel>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Panel eyebrow="Approved" title={money(data.approved_commission)}><p className="text-xs text-slate-400">Eligible for the weekly payout</p></Panel>
            <Panel eyebrow="Paid" title={money(data.paid_commission)}><p className="text-xs text-slate-400">Recorded after a real payment reference</p></Panel>
            <Panel eyebrow="Reversed" title={money(data.reversed_commission)}><p className="text-xs text-slate-400">Deposit reversed before payment</p></Panel>
          </div>
          <Panel eyebrow="Payout history" title="Payments recorded for you">
            {(data.payouts || []).length === 0 && <p className="text-sm text-slate-400">No payouts yet.</p>}
            <ul className="space-y-2" data-testid="referrals-payouts">
              {(data.payouts || []).map((payout: any) => (
                <li key={payout.id} className="flex flex-wrap justify-between gap-2 text-sm text-slate-200">
                  <span>{payout.currency} {payout.total}</span>
                  <span>{payout.status}</span>
                  <span>{payout.reference || "Reference pending"}</span>
                </li>
              ))}
            </ul>
          </Panel>
        </>
      )}
    </div>
  );
}
