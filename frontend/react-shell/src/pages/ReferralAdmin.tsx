import React, { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Link2, Plus, RefreshCw, ShieldCheck, Wallet } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";

type Partner = {
  partner_id: string;
  display_name: string;
  contact_email?: string | null;
  social_handle?: string | null;
  campaign_name?: string | null;
  payout_method: string;
  payout_destination_reference?: string | null;
  is_active: boolean;
  share_code?: string | null;
  referral_path?: string | null;
  current_uses: number;
  max_uses: number;
  attributed_signups: number;
  pending_commission: string | number;
  approved_commission: string | number;
  paid_commission: string | number;
};

type ReferralReward = {
  reward_id: string;
  beneficiary_name?: string | null;
  beneficiary_email?: string | null;
  payout_method?: string | null;
  payout_destination_reference?: string | null;
  share_code?: string | null;
  deposit_reference?: string | null;
  deposit_amount_fiat?: string | number | null;
  amount?: string | number | null;
  unit?: string | null;
  status: string;
  hold_until?: string | null;
  label: string;
  review_reason?: string | null;
};

const money = (value: unknown, currency = "NGN") =>
  new Intl.NumberFormat("en-NG", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value || 0));

export default function ReferralAdmin() {
  const qc = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [payoutSaving, setPayoutSaving] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [paymentReference, setPaymentReference] = useState("");
  const [createdLink, setCreatedLink] = useState("");
  const [form, setForm] = useState({
    display_name: "",
    contact_email: "",
    social_handle: "",
    campaign_name: "",
    payout_method: "bank_transfer",
    payout_destination_reference: "",
    vanity_code: "",
    max_uses: "100000",
    notes: "",
  });

  const partnersQuery = useQuery<Partner[]>({
    queryKey: ["admin-referral-partners"],
    queryFn: async () => (await api.get("/admin/referrals/partners")).data,
  });
  const pendingQuery = useQuery<ReferralReward[]>({
    queryKey: ["admin-referral-pending"],
    queryFn: async () => (await api.get("/admin/referrals/rewards/pending")).data,
  });
  const approvedQuery = useQuery<ReferralReward[]>({
    queryKey: ["admin-referral-approved"],
    queryFn: async () => (await api.get("/admin/referrals/rewards/approved")).data,
  });

  const selectedTotal = useMemo(
    () => (approvedQuery.data || []).filter((reward) => selected.includes(reward.reward_id)),
    [approvedQuery.data, selected],
  );
  const selectedCurrencies = Array.from(new Set(selectedTotal.map((item) => String(item.unit || "").toUpperCase())));
  const invalidate = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["admin-referral-partners"] }),
      qc.invalidateQueries({ queryKey: ["admin-referral-pending"] }),
      qc.invalidateQueries({ queryKey: ["admin-referral-approved"] }),
    ]);
  };

  const createPartner = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setCreatedLink("");
    try {
      const response = await api.post("/admin/referrals/partners", {
        ...form,
        max_uses: Number(form.max_uses || 100000),
        contact_email: form.contact_email.trim() || null,
        social_handle: form.social_handle.trim() || null,
        campaign_name: form.campaign_name.trim() || null,
        payout_destination_reference: form.payout_destination_reference.trim() || null,
        vanity_code: form.vanity_code.trim() || null,
        notes: form.notes.trim() || null,
      });
      const partner = response.data as Partner;
      const url = partner.referral_path
        ? window.location.origin + partner.referral_path
        : "";
      setCreatedLink(url);
      setForm({
        display_name: "",
        contact_email: "",
        social_handle: "",
        campaign_name: "",
        payout_method: "bank_transfer",
        payout_destination_reference: "",
        vanity_code: "",
        max_uses: "100000",
        notes: "",
      });
      toast.success("Referral partner and link created.");
      await invalidate();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  const setPartnerActive = async (partner: Partner) => {
    try {
      await api.patch(`/admin/referrals/partners/${partner.partner_id}/status`, {
        is_active: !partner.is_active,
        reason: partner.is_active ? "Admin disabled referral partner campaign" : "Admin re-enabled referral partner campaign",
      });
      toast.success(partner.is_active ? "Referral link disabled." : "Referral link re-enabled.");
      await invalidate();
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  const reviewReward = async (rewardId: string, action: "approve" | "block") => {
    try {
      await api.post(`/admin/referrals/rewards/${rewardId}/review`, {
        action,
        reason: action === "approve" ? "First-deposit referral passed admin review" : "Referral commission blocked after admin review",
      });
      toast.success(action === "approve" ? "Commission approved for payout." : "Commission blocked.");
      await invalidate();
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  const payBatch = async () => {
    if (!selected.length || !paymentReference.trim()) {
      toast.error("Select approved commissions and enter the bank or transfer reference.");
      return;
    }
    if (selectedCurrencies.length !== 1) {
      toast.error("Pay one currency per batch. Split the selected rewards by currency.");
      return;
    }
    setPayoutSaving(true);
    try {
      const response = await api.post("/admin/referrals/rewards/payout-batch", {
        reward_ids: selected,
        payment_reference: paymentReference.trim(),
      });
      toast.success(
        `Payout batch recorded: ${response.data.reward_count} commission(s), ${money(response.data.total_amount, response.data.currency)}.`,
      );
      setSelected([]);
      setPaymentReference("");
      await invalidate();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setPayoutSaving(false);
    }
  };

  const toggleSelected = (rewardId: string) => {
    setSelected((current) =>
      current.includes(rewardId) ? current.filter((id) => id !== rewardId) : [...current, rewardId],
    );
  };

  const partnerRows = partnersQuery.data || [];
  const pendingRows = pendingQuery.data || [];
  const approvedRows = approvedQuery.data || [];

  return (
    <div className="space-y-6" data-testid="admin-referral-centre">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="gx-eyebrow text-emerald-300">Growth and partnerships</p>
          <h1 className="gx-h1">Referral & Affiliate Centre</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Create tracked creator links, monitor first-deposit conversions, approve commissions and reconcile payouts.
            Every eligible GTEX account type receives the same first-deposit offer.
          </p>
        </div>
        <button
          onClick={() => void invalidate()}
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-200 hover:bg-white/5"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">Partners / campaigns</p>
          <p className="mt-2 text-2xl font-bold text-white">{partnerRows.length}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">Attributed signups</p>
          <p className="mt-2 text-2xl font-bold text-white">{partnerRows.reduce((n, p) => n + Number(p.attributed_signups || 0), 0)}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">Commissions awaiting review</p>
          <p className="mt-2 text-2xl font-bold text-amber-200">{pendingRows.length}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">Approved to pay</p>
          <p className="mt-2 text-2xl font-bold text-emerald-300">{approvedRows.length}</p>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <form onSubmit={createPartner} className="space-y-4 rounded-2xl border border-white/10 bg-[#0B1421] p-5">
          <div className="flex items-center gap-2">
            <Plus size={17} className="text-emerald-300" />
            <h2 className="text-lg font-bold text-white">Create an influencer referral link</h2>
          </div>
          <p className="text-xs leading-5 text-slate-400">
            The partner does not need a GTEX login. Add their identity and a secure payout destination reference;
            do not enter full bank-card or account credentials here.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-slate-400">Creator / partner name
              <input required minLength={2} maxLength={120} value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} className="gx-input mt-1" placeholder="Creator name" />
            </label>
            <label className="text-xs text-slate-400">Contact email
              <input type="email" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} className="gx-input mt-1" placeholder="creator@example.com" />
            </label>
            <label className="text-xs text-slate-400">Social handle
              <input value={form.social_handle} onChange={(e) => setForm({ ...form, social_handle: e.target.value })} className="gx-input mt-1" placeholder="@creator" />
            </label>
            <label className="text-xs text-slate-400">Campaign name
              <input value={form.campaign_name} onChange={(e) => setForm({ ...form, campaign_name: e.target.value })} className="gx-input mt-1" placeholder="November creator launch" />
            </label>
            <label className="text-xs text-slate-400">Payout method
              <select value={form.payout_method} onChange={(e) => setForm({ ...form, payout_method: e.target.value })} className="gx-input mt-1">
                <option value="bank_transfer">Bank transfer</option>
                <option value="mobile_money">Mobile money</option>
                <option value="crypto">Crypto</option>
                <option value="wallet">GTEX wallet</option>
                <option value="manual">Manual / offline</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label className="text-xs text-slate-400">Payout destination reference (masked / provider ID)
              <input value={form.payout_destination_reference} onChange={(e) => setForm({ ...form, payout_destination_reference: e.target.value })} className="gx-input mt-1" placeholder="Secure payout profile or masked label" />
            </label>
            <label className="text-xs text-slate-400">Custom referral code (optional)
              <input maxLength={32} value={form.vanity_code} onChange={(e) => setForm({ ...form, vanity_code: e.target.value.toLowerCase().replace(/[^a-z0-9]/g, "") })} className="gx-input mt-1" placeholder="CREATOR10" />
            </label>
            <label className="text-xs text-slate-400">Maximum registrations
              <input type="number" min={1} max={1000000} value={form.max_uses} onChange={(e) => setForm({ ...form, max_uses: e.target.value })} className="gx-input mt-1" />
            </label>
          </div>
          <label className="block text-xs text-slate-400">Internal notes
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="gx-input mt-1 min-h-20" placeholder="Contract terms, approval notes, campaign details" />
          </label>
          <button disabled={saving} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-sm font-bold text-slate-950 disabled:opacity-50">
            {saving ? "Creating link…" : "Create referral partner & link"}
          </button>
          {createdLink && (
            <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/5 p-3">
              <p className="text-xs font-bold text-emerald-200">Referral link created</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <code className="min-w-0 flex-1 break-all text-xs text-white">{createdLink}</code>
                <button type="button" onClick={() => { void navigator.clipboard.writeText(createdLink).then(() => toast.success("Referral link copied.")); }} className="rounded-lg border border-white/15 px-3 py-2 text-xs text-white">
                  <Copy size={13} className="inline mr-1" /> Copy
                </button>
              </div>
            </div>
          )}
          <div className="rounded-lg border border-white/10 bg-black/20 p-3 text-xs leading-5 text-slate-400">
            <b className="text-white">Campaign terms:</b> 10% first-deposit bonus for the referred user and 10% commission for the partner. The first-deposit bonus is credited after a real deposit settles. Partner commission is held for seven days, then reviewed and paid in batches.
          </div>
        </form>

        <div className="space-y-4 rounded-2xl border border-white/10 bg-[#0B1421] p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-white">Partner performance</h2>
            <Link2 size={17} className="text-slate-500" />
          </div>
          {partnersQuery.isLoading ? <p className="text-sm text-slate-500">Loading referral partners…</p> : null}
          {partnerRows.length === 0 && !partnersQuery.isLoading ? <p className="text-sm text-slate-500">No referral partners have been created yet.</p> : null}
          <div className="space-y-3">
            {partnerRows.map((partner) => {
              const link = partner.referral_path ? window.location.origin + partner.referral_path : "";
              return (
                <div key={partner.partner_id} className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-bold text-white">{partner.display_name}</p>
                      <p className="mt-0.5 text-xs text-slate-500">{partner.contact_email || partner.social_handle || "No contact provided"}</p>
                      <p className="mt-1 font-mono text-xs text-emerald-300">{partner.share_code || "No code"}</p>
                    </div>
                    <button onClick={() => void setPartnerActive(partner)} className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${partner.is_active ? "border-emerald-400/30 text-emerald-300" : "border-rose-400/30 text-rose-300"}`}>
                      {partner.is_active ? "Active · Disable" : "Disabled · Enable"}
                    </button>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                    <div><p className="text-slate-500">Signups</p><b className="text-white">{partner.attributed_signups}</b></div>
                    <div><p className="text-slate-500">Pending</p><b className="text-amber-200">{money(partner.pending_commission)}</b></div>
                    <div><p className="text-slate-500">Approved</p><b className="text-emerald-200">{money(partner.approved_commission)}</b></div>
                    <div><p className="text-slate-500">Paid</p><b className="text-white">{money(partner.paid_commission)}</b></div>
                  </div>
                  {link && <div className="mt-3 flex items-center gap-2"><p className="min-w-0 flex-1 truncate text-xs text-slate-500">{link}</p><button onClick={() => { void navigator.clipboard.writeText(link).then(() => toast.success("Referral link copied.")); }} className="rounded-md border border-white/10 px-2 py-1 text-xs text-slate-200"><Copy size={12} /></button></div>}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-[#0B1421] p-5">
          <div className="mb-4 flex items-center gap-2">
            <ShieldCheck size={17} className="text-amber-300" />
            <h2 className="text-lg font-bold text-white">Commissions awaiting review</h2>
          </div>
          <div className="space-y-3">
            {pendingRows.length === 0 ? <p className="text-sm text-slate-500">No commissions are awaiting review.</p> : null}
            {pendingRows.map((reward) => (
              <div key={reward.reward_id} className="rounded-xl border border-white/10 bg-black/20 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div><p className="font-semibold text-white">{reward.beneficiary_name || "GTEX referrer"}</p><p className="text-xs text-slate-500">{reward.beneficiary_email || reward.share_code || "Referral partner"}</p></div>
                  <b className="text-amber-200">{money(reward.amount, String(reward.unit || "NGN").toUpperCase())}</b>
                </div>
                <p className="mt-2 text-xs text-slate-400">First deposit: {money(reward.deposit_amount_fiat, "NGN")} · {reward.deposit_reference || "verified deposit"}</p>
                <p className="mt-1 text-xs text-slate-500">Hold until: {reward.hold_until ? new Date(reward.hold_until).toLocaleString() : "No hold"}</p>
                {reward.review_reason && <p className="mt-1 text-xs text-slate-500">{reward.review_reason}</p>}
                <div className="mt-3 flex gap-2">
                  <button onClick={() => void reviewReward(reward.reward_id, "approve")} className="rounded-lg bg-emerald-400 px-3 py-2 text-xs font-bold text-slate-950">Approve</button>
                  <button onClick={() => void reviewReward(reward.reward_id, "block")} className="rounded-lg border border-rose-400/30 px-3 py-2 text-xs font-bold text-rose-200">Block</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#0B1421] p-5">
          <div className="mb-4 flex items-center gap-2">
            <Wallet size={17} className="text-emerald-300" />
            <h2 className="text-lg font-bold text-white">Approved commissions · payout batch</h2>
          </div>
          <p className="mb-3 text-xs leading-5 text-slate-400">Select approved, hold-cleared commissions that have already been transferred externally. Recording this batch marks them paid and appends an immutable referral payout audit entry; it does not initiate the bank transfer.</p>
          <div className="space-y-2">
            {approvedRows.length === 0 ? <p className="text-sm text-slate-500">No approved commissions are ready for payout.</p> : null}
            {approvedRows.map((reward) => (
              <label key={reward.reward_id} className="flex items-start gap-2 rounded-lg border border-white/10 bg-black/20 p-3 text-xs">
                <input type="checkbox" checked={selected.includes(reward.reward_id)} onChange={() => toggleSelected(reward.reward_id)} className="mt-0.5" />
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-white">{reward.beneficiary_name || "GTEX referrer"}</span>
                  <span className="block text-slate-500">{reward.share_code || reward.beneficiary_email || "First-deposit referral"}</span>
                </span>
                <b className="shrink-0 text-emerald-200">{money(reward.amount, String(reward.unit || "NGN").toUpperCase())}</b>
              </label>
            ))}
          </div>
          <div className="mt-4 rounded-lg border border-white/10 bg-black/20 p-3">
            <p className="text-xs text-slate-400">Selected: {selected.length} · Total: {money(selectedTotal.reduce((sum, reward) => sum + Number(reward.amount || 0), 0), selectedCurrencies[0] || "NGN")}</p>
            <label className="mt-3 block text-xs text-slate-400">External payment / batch reference
              <input value={paymentReference} onChange={(e) => setPaymentReference(e.target.value)} className="gx-input mt-1" placeholder="Bank transfer reference or payout batch ID" />
            </label>
            <button disabled={payoutSaving || !selected.length || !paymentReference.trim()} onClick={() => void payBatch()} className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-sm font-bold text-slate-950 disabled:opacity-40">
              {payoutSaving ? "Recording payout…" : "Record selected payouts as paid"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
