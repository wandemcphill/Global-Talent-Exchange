import React, { useState } from "react";
import { Navigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Loading } from "@/components/gtex/ui";

const SECTIONS = [
  ["overview", "Overview"],
  ["partners", "Referral partners"],
  ["create", "Create campaign"],
  ["links", "Referral links"],
  ["attributions", "Attributed registrations"],
  ["conversions", "First-deposit conversions"],
  ["pending", "Pending commissions"],
  ["approved", "Approved commissions"],
  ["payouts", "Payout batches"],
  ["history", "Payment history"],
  ["fraud", "Fraud review"],
  ["analytics", "Analytics and reports"],
  ["settings", "Programme settings"],
] as const;

type SectionId = (typeof SECTIONS)[number][0];

async function loadSection(section: SectionId) {
  if (section === "overview") return (await api.get("/admin/referrals/affiliate/overview")).data;
  if (section === "partners" || section === "create")
    return (await api.get("/admin/referrals/affiliate/partners")).data;
  if (section === "links") return (await api.get("/admin/referrals/affiliate/links")).data;
  if (section === "attributions")
    return (await api.get("/admin/referrals/affiliate/attributions")).data;
  if (section === "conversions")
    return (await api.get("/admin/referrals/affiliate/conversions")).data;
  if (section === "pending")
    return (
      await api.get("/admin/referrals/affiliate/commissions", { params: { status: "pending" } })
    ).data;
  if (section === "approved")
    return (
      await api.get("/admin/referrals/affiliate/commissions", { params: { status: "approved" } })
    ).data;
  if (section === "payouts")
    return (await api.get("/admin/referrals/affiliate/payouts/preview")).data;
  if (section === "history")
    return (await api.get("/admin/referrals/affiliate/payout-batches")).data;
  if (section === "fraud") return (await api.get("/admin/referrals/affiliate/fraud")).data;
  if (section === "analytics") return (await api.get("/admin/referrals/affiliate/analytics")).data;
  return (await api.get("/admin/referrals/affiliate/settings")).data;
}

export default function ReferralAdmin() {
  const { user, loading } = useAuth();
  const queryClient = useQueryClient();
  const isAdmin = ["admin", "super_admin"].includes(String(user?.role).toLowerCase());
  const [section, setSection] = useState<SectionId>("overview");
  const [formError, setFormError] = useState<string | null>(null);
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [partnerForm, setPartnerForm] = useState({
    display_name: "",
    contact_email: "",
    social_handle: "",
    campaign_name: "",
    code: "",
    payout_currency: "NGN",
    notes: "",
    contractual_terms: "",
  });
  const [selectedRewards, setSelectedRewards] = useState<string[]>([]);
  const [paymentReference, setPaymentReference] = useState("");
  const [batchId, setBatchId] = useState("");
  const [settingsForm, setSettingsForm] = useState<any>(null);

  const query = useQuery({
    queryKey: ["referral-admin", section],
    queryFn: () => loadSection(section),
    enabled: isAdmin,
    retry: false,
  });

  if (loading) return <Loading label="Opening referral administration..." />;
  if (!isAdmin) return <Navigate to="/app" replace />;

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["referral-admin"] });
  };

  const createPartner = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    setFormMessage(null);
    try {
      const payload = {
        ...partnerForm,
        code: partnerForm.code.trim() || undefined,
        contact_email: partnerForm.contact_email.trim() || undefined,
      };
      const { data } = await api.post("/admin/referrals/affiliate/partners", payload);
      const link = data.campaigns?.[0]?.link;
      setFormMessage(link ? `Campaign created. Share ${link}` : "Campaign created.");
      setSection("links");
      await refresh();
    } catch (error) {
      setFormError(errMsg(error));
    } finally {
      setBusy(false);
    }
  };

  const decide = async (rewardId: string, decision: string) => {
    const reason = window.prompt(`Reason for ${decision}`) || "";
    if (reason.trim().length < 3) {
      setFormError("A review reason is required.");
      setFormMessage(null);
      return;
    }
    setBusy(true);
    setFormError(null);
    setFormMessage(null);
    try {
      await api.post(`/admin/referrals/affiliate/commissions/${rewardId}/decision`, {
        decision,
        reason,
      });
      setFormMessage(`Commission ${decision} recorded.`);
      await refresh();
    } catch (error) {
      setFormError(errMsg(error));
    } finally {
      setBusy(false);
    }
  };

  const createBatch = async () => {
    setBusy(true);
    setFormError(null);
    setFormMessage(null);
    try {
      const { data } = await api.post("/admin/referrals/affiliate/payout-batches", {
        reward_ids: selectedRewards,
        payout_method: "external_transfer",
        off_cycle_reason: "Administrator reconciliation",
      });
      setBatchId(data.id);
      setFormMessage(
        `Draft batch ${data.id} totals ${data.currency} ${data.total}. It is not paid until you record the transfer reference.`,
      );
      await refresh();
    } catch (error) {
      setFormError(errMsg(error));
    } finally {
      setBusy(false);
    }
  };

  const confirmBatch = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    setFormMessage(null);
    try {
      await api.post(`/admin/referrals/affiliate/payout-batches/${batchId}/confirm`, {
        external_reference: paymentReference,
      });
      setFormMessage("Payment reference recorded. The selected commissions are marked paid.");
      setPaymentReference("");
      await refresh();
    } catch (error) {
      setFormError(errMsg(error));
    } finally {
      setBusy(false);
    }
  };

  const saveSettings = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!settingsForm) return;
    setBusy(true);
    setFormError(null);
    setFormMessage(null);
    try {
      await api.put("/admin/referrals/affiliate/settings", {
        user_bonus_bps: Number(settingsForm.user_bonus_bps),
        referrer_commission_bps: Number(settingsForm.referrer_commission_bps),
        is_active: Boolean(settingsForm.is_active),
        hold_days: Number(settingsForm.hold_days),
        payout_weekday: Number(settingsForm.payout_weekday),
        min_payout_thresholds: settingsForm.min_payout_thresholds,
        eligible_account_types: settingsForm.eligible_account_types,
        qualifying_deposit_types: settingsForm.qualifying_deposit_types,
        reason: "Programme settings updated from the affiliate centre",
      });
      setFormMessage("Settings saved. Existing rewards keep the rate they were created with.");
      await refresh();
    } catch (error) {
      setFormError(errMsg(error));
    } finally {
      setBusy(false);
    }
  };

  const data = query.data;
  const settings = section === "settings" ? settingsForm || data : null;

  return (
    <div className="space-y-6 p-4 sm:p-8" data-testid="referral-admin">
      <header>
        <p className="gx-eyebrow text-amber-300">Administration</p>
        <h1 className="text-3xl font-black text-white">Referral & Affiliate Centre</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-300">
          External promoters do not need a GTEX login. Commissions stay pending through the hold and
          are marked paid only after an admin records the real transfer reference.
        </p>
      </header>
      <div className="flex flex-wrap gap-2">
        {SECTIONS.map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`rounded-full px-3 py-1 text-xs font-bold ${section === id ? "bg-cyan-400 text-slate-950" : "bg-slate-800 text-slate-200"}`}
            onClick={() => {
              setSection(id);
              setFormError(null);
              setFormMessage(null);
            }}
            data-testid={`referral-admin-tab-${id}`}
          >
            {label}
          </button>
        ))}
      </div>
      {formError && (
        <p
          className="rounded-xl border border-red-400/40 bg-red-950/40 p-3 text-sm text-red-200"
          data-testid="referral-admin-error"
        >
          {formError}
        </p>
      )}
      {formMessage && (
        <p
          className="rounded-xl border border-emerald-400/40 bg-emerald-950/30 p-3 text-sm text-emerald-100"
          data-testid="referral-admin-success"
        >
          {formMessage}
        </p>
      )}
      {query.isLoading && <Loading label="Loading referral records..." />}
      {query.isError && (
        <p className="text-sm text-red-300" data-testid="referral-admin-load-error">
          {errMsg(query.error)}
        </p>
      )}

      {section === "overview" && data && (
        <div className="grid gap-4 md:grid-cols-3" data-testid="referral-admin-overview">
          <Stat label="Clicks" value={data.clicks} />
          <Stat label="Registrations" value={data.registrations} />
          <Stat label="First deposits" value={data.first_deposits} />
          <Stat label="Conversion" value={data.conversion_rate} />
          <Stat label="Fraud flags" value={data.fraud_flags} />
          <Stat label="Partners" value={data.partners} />
        </div>
      )}

      {section === "create" && (
        <form
          className="grid max-w-xl gap-3"
          onSubmit={createPartner}
          data-testid="referral-admin-create"
        >
          {(
            [
              "display_name",
              "contact_email",
              "social_handle",
              "campaign_name",
              "code",
              "payout_currency",
            ] as const
          ).map((field) => (
            <label key={field} className="text-xs uppercase tracking-wide text-slate-400">
              {field.replace(/_/g, " ")}
              <input
                className="gx-input mt-1"
                value={(partnerForm as any)[field]}
                onChange={(event) =>
                  setPartnerForm((current) => ({ ...current, [field]: event.target.value }))
                }
                required={field === "display_name" || field === "campaign_name"}
              />
            </label>
          ))}
          <label className="text-xs uppercase tracking-wide text-slate-400">
            Notes
            <textarea
              className="gx-input mt-1"
              value={partnerForm.notes}
              onChange={(event) =>
                setPartnerForm((current) => ({ ...current, notes: event.target.value }))
              }
            />
          </label>
          <label className="text-xs uppercase tracking-wide text-slate-400">
            Contractual terms
            <textarea
              className="gx-input mt-1"
              value={partnerForm.contractual_terms}
              onChange={(event) =>
                setPartnerForm((current) => ({ ...current, contractual_terms: event.target.value }))
              }
            />
          </label>
          <button className="gx-btn-primary" disabled={busy} type="submit">
            Create partner and link
          </button>
        </form>
      )}

      {section === "partners" && Array.isArray(data) && (
        <ul className="space-y-3" data-testid="referral-admin-partners">
          {data.map((partner: any) => (
            <li key={partner.id} className="rounded-2xl border border-slate-700 p-4">
              <p className="font-bold text-white">
                {partner.display_name} · {partner.status}
              </p>
              <p className="text-sm text-slate-400">
                {partner.contact_email || "No login required"} ·{" "}
                {partner.social_handle || "No handle"}
              </p>
              {(partner.campaigns || []).map((campaign: any) => (
                <p key={campaign.id} className="mt-2 text-sm text-cyan-200">
                  {campaign.code} · {campaign.link}
                </p>
              ))}
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  className="gx-btn-secondary"
                  disabled={busy}
                  onClick={async () => {
                    setFormError(null);
                    setFormMessage(null);
                    try {
                      await api.post(`/admin/referrals/affiliate/partners/${partner.id}/status`, {
                        active: partner.status !== "active",
                        reason:
                          partner.status === "active"
                            ? "Suspended from the affiliate centre"
                            : "Reactivated from the affiliate centre",
                      });
                      setFormMessage(
                        partner.status === "active" ? "Partner suspended." : "Partner reactivated.",
                      );
                      await refresh();
                    } catch (error) {
                      setFormError(errMsg(error));
                    }
                  }}
                >
                  {partner.status === "active" ? "Suspend" : "Reactivate"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {section === "links" && Array.isArray(data) && (
        <ul className="space-y-2" data-testid="referral-admin-links">
          {data.map((link: any) => (
            <li key={link.id} className="text-sm text-slate-200">
              {link.name}: {link.code} · {link.link} · {link.status}
            </li>
          ))}
        </ul>
      )}

      {section === "attributions" && Array.isArray(data) && (
        <ul className="space-y-2 text-sm text-slate-200" data-testid="referral-admin-attributions">
          {data.map((row: any) => (
            <li key={row.id}>
              {row.referred_username || row.referred_user_id} · {row.account_type} ·{" "}
              {row.share_code} · {row.status}
            </li>
          ))}
        </ul>
      )}

      {section === "conversions" && Array.isArray(data) && (
        <ul className="space-y-2 text-sm text-slate-200">
          {data.map((row: any) => (
            <li key={row.id}>
              {row.qualifying_currency} {row.qualifying_amount} · bonus {row.reward_amount}{" "}
              {row.reward_unit} · {row.status}
            </li>
          ))}
        </ul>
      )}

      {(section === "pending" || section === "approved") && Array.isArray(data) && (
        <ul className="space-y-3" data-testid={`referral-admin-${section}`}>
          {data.map((row: any) => (
            <li
              key={row.id}
              className="rounded-2xl border border-slate-700 p-4 text-sm text-slate-200"
            >
              <p>
                {row.qualifying_currency} {row.reward_amount} · hold until {row.hold_until || "n/a"}{" "}
                · {row.status}
              </p>
              {section === "approved" && (
                <label className="mt-2 flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedRewards.includes(row.id)}
                    onChange={(event) =>
                      setSelectedRewards((current) =>
                        event.target.checked
                          ? [...current, row.id]
                          : current.filter((id) => id !== row.id),
                      )
                    }
                  />
                  Select for payout
                </label>
              )}
              {section === "pending" && (
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    className="gx-btn-primary"
                    onClick={() => decide(row.id, "approve")}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="gx-btn-secondary"
                    onClick={() => decide(row.id, "block")}
                  >
                    Block
                  </button>
                  <button
                    type="button"
                    className="gx-btn-secondary"
                    onClick={() => decide(row.id, "hold")}
                  >
                    Hold
                  </button>
                  <button
                    type="button"
                    className="gx-btn-secondary"
                    onClick={() => decide(row.id, "reverse")}
                  >
                    Reverse
                  </button>
                </div>
              )}
            </li>
          ))}
          {section === "approved" && (
            <button
              type="button"
              className="gx-btn-primary"
              disabled={busy || selectedRewards.length === 0}
              onClick={createBatch}
              data-testid="referral-admin-create-batch"
            >
              Create draft payout
            </button>
          )}
        </ul>
      )}

      {section === "payouts" && (
        <div className="space-y-4" data-testid="referral-admin-payouts">
          {Array.isArray(data) &&
            data.map((group: any) => (
              <p
                key={`${group.beneficiary_kind}-${group.beneficiary_id}-${group.currency}`}
                className="text-sm text-slate-200"
              >
                {group.beneficiary_kind} {group.beneficiary_id}: {group.currency} {group.total} ·
                threshold {group.threshold || "not set"} · destination{" "}
                {group.destination_label || "not recorded"}
              </p>
            ))}
          <form className="grid max-w-md gap-3" onSubmit={confirmBatch}>
            <input
              className="gx-input"
              placeholder="Draft batch id"
              value={batchId}
              onChange={(event) => setBatchId(event.target.value)}
              data-testid="referral-admin-batch-id"
            />
            <input
              className="gx-input"
              placeholder="Bank or provider reference"
              value={paymentReference}
              onChange={(event) => setPaymentReference(event.target.value)}
              data-testid="referral-admin-payment-reference"
            />
            <button
              className="gx-btn-primary"
              disabled={busy}
              type="submit"
              data-testid="referral-admin-confirm-payout"
            >
              Record completed transfer
            </button>
          </form>
        </div>
      )}

      {section === "history" && Array.isArray(data) && (
        <ul className="space-y-2 text-sm text-slate-200" data-testid="referral-admin-history">
          {data.map((batch: any) => (
            <li key={batch.id}>
              {batch.status} · {batch.currency} {batch.total} ·{" "}
              {batch.external_reference || "no reference"} · transferred by GTEX:{" "}
              {String(batch.transferred_by_gtex)}
            </li>
          ))}
        </ul>
      )}

      {section === "fraud" && Array.isArray(data) && (
        <ul className="space-y-2 text-sm text-slate-200">
          {data.map((flag: any) => (
            <li key={flag.id}>
              {flag.flag_type} · {flag.severity} · {flag.status}
            </li>
          ))}
        </ul>
      )}

      {section === "analytics" && data && (
        <div className="space-y-3" data-testid="referral-admin-analytics">
          <p className="text-sm text-slate-200">
            Clicks {data.clicks} · registrations {data.registrations} · deposits{" "}
            {data.first_deposits}
          </p>
          <a
            className="text-cyan-300 underline"
            href={`${api.defaults.baseURL}/admin/referrals/affiliate/reports/rewards`}
          >
            Download rewards CSV
          </a>
          <a
            className="ml-4 text-cyan-300 underline"
            href={`${api.defaults.baseURL}/admin/referrals/affiliate/reports/payouts`}
          >
            Download payout CSV
          </a>
        </div>
      )}

      {section === "settings" && settings && (
        <form
          className="grid max-w-xl gap-3"
          onSubmit={saveSettings}
          data-testid="referral-admin-settings"
        >
          <label className="text-xs text-slate-400">
            User bonus basis points
            <input
              className="gx-input mt-1"
              value={settings.user_bonus_bps}
              onChange={(event) =>
                setSettingsForm({ ...settings, user_bonus_bps: event.target.value })
              }
            />
          </label>
          <label className="text-xs text-slate-400">
            Referrer commission basis points
            <input
              className="gx-input mt-1"
              value={settings.referrer_commission_bps}
              onChange={(event) =>
                setSettingsForm({ ...settings, referrer_commission_bps: event.target.value })
              }
            />
          </label>
          <label className="text-xs text-slate-400">
            Hold days
            <input
              className="gx-input mt-1"
              value={settings.hold_days}
              onChange={(event) => setSettingsForm({ ...settings, hold_days: event.target.value })}
            />
          </label>
          <label className="text-xs text-slate-400">
            Payout weekday (0 = Monday)
            <input
              className="gx-input mt-1"
              value={settings.payout_weekday}
              onChange={(event) =>
                setSettingsForm({ ...settings, payout_weekday: event.target.value })
              }
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-200">
            <input
              type="checkbox"
              checked={Boolean(settings.is_active)}
              onChange={(event) =>
                setSettingsForm({ ...settings, is_active: event.target.checked })
              }
            />
            Programme active
          </label>
          <p className="text-xs text-slate-400">
            Eligible: {(settings.eligible_account_types || []).join(", ")}
          </p>
          <p className="text-xs text-slate-400">
            Deposit types: {(settings.qualifying_deposit_types || []).join(", ")}
          </p>
          <p className="text-xs text-slate-400">
            NGN threshold: {(settings.min_payout_thresholds || {}).NGN}
          </p>
          <button className="gx-btn-primary" disabled={busy} type="submit">
            Save settings
          </button>
        </form>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-700 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-black text-white">{String(value ?? "0")}</p>
    </div>
  );
}
