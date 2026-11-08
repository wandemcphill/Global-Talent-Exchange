import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Navigate } from "react-router-dom";
import {
  AlertCircle,
  BarChart3,
  Building2,
  CreditCard,
  LayoutGrid,
  Megaphone,
  Music,
  RefreshCw,
  ShieldAlert,
  Tag,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api, errMsg } from "@/lib/api";
import { formatNairaFromKobo, resolveCommercialMediaUrl } from "@/lib/commercial/api";

export type Campaign = {
  id: string;
  campaign_type: string;
  brand_name: string;
  headline: string;
  description: string;
  placement: string;
  placements?: string[];
  destination_url: string;
  creative_url?: string | null;
  logo_url?: string | null;
  audio_url?: string | null;
  artist_name?: string | null;
  track_title?: string | null;
  record_label?: string | null;
  explicit_content?: boolean;
  rights_confirmed?: boolean;
  is_silent_creative?: boolean;
  duration_days?: number;
  payment_status?: string;
  price_minor_ngn?: number | null;
  start_at: string;
  end_at: string;
  budget_amount: string;
  currency: string;
  pricing_model: string;
  unit_price: string;
  status: string;
  review_note?: string | null;
  advertiser_id?: string | null;
};

export type Report = {
  campaign_id: string;
  campaign_name: string;
  currency: string;
  impressions: number;
  clicks: number;
  conversions: number;
  ctr_percent: number;
  estimated_spend: string;
  billing_state: string;
};

type AdminTab =
  | "campaigns"
  | "music"
  | "accounts"
  | "placements"
  | "pricing"
  | "payments"
  | "analytics";

const filters = ["pending", "approved", "rejected", "paused", "archived", "draft"];

function resolveInitialTab(initialSection?: AdminTab): AdminTab {
  if (initialSection) return initialSection;
  if (typeof window === "undefined") return "campaigns";
  const path = window.location.pathname.toLowerCase();
  if (path.endsWith("/accounts")) return "accounts";
  if (path.endsWith("/music")) return "music";
  if (path.endsWith("/placements")) return "placements";
  if (path.endsWith("/pricing")) return "pricing";
  if (path.endsWith("/payments")) return "payments";
  if (path.endsWith("/analytics")) return "analytics";
  return "campaigns";
}

export default function AdminAdvertising({ initialSection }: { initialSection?: AdminTab } = {}) {
  const { user } = useAuth();
  const isAdmin = ["admin", "super_admin"].includes(String(user?.role || "").toLowerCase());
  const [activeTab, setActiveTab] = useState<AdminTab>(() => resolveInitialTab(initialSection));

  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [filter, setFilter] = useState("pending");
  const [notes, setNotes] = useState<Record<string, string>>({});

  // Independent request states for Campaign Review Queue (preserved for existing test suite)
  const [loadingCampaigns, setLoadingCampaigns] = useState(true);
  const [loadingReports, setLoadingReports] = useState(false);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);
  const [reportsError, setReportsError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  // Commercial Administration Extended State
  const [accounts, setAccounts] = useState<any[]>([]);
  const [placements, setPlacements] = useState<any[]>([]);
  const [pricingPackages, setPricingPackages] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [analyticsSummary, setAnalyticsSummary] = useState<any | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [sectionLoading, setSectionLoading] = useState(false);

  // Editable placement / package drafts
  const [placementEdits, setPlacementEdits] = useState<Record<string, { priceNaira: string; active: boolean }>>({});
  const [packageEdits, setPackageEdits] = useState<Record<string, { priceNaira: string; discount: string; active: boolean }>>({});
  const [refundReason, setRefundReason] = useState<Record<string, string>>({});

  const fetchCampaigns = useCallback(async () => {
    setLoadingCampaigns(true);
    setCampaignsError(null);
    try {
      const response = await api.get("/v2/ads/brand/admin/campaigns", {
        params: filter ? { status: filter } : {},
      });
      const data = response.data;
      setCampaigns(Array.isArray(data) ? data : []);
      setCampaignsError(null);
    } catch (error) {
      const msg = errMsg(error);
      setCampaignsError(msg);
      toast.error(msg);
    } finally {
      setLoadingCampaigns(false);
    }
  }, [filter]);

  const fetchReports = useCallback(async () => {
    setLoadingReports(true);
    setReportsError(null);
    try {
      const response = await api.get("/v2/ads/brand/admin/reports");
      const data = response.data;
      setReports(data?.reports || []);
      setReportsError(null);
    } catch (error) {
      const msg = errMsg(error);
      setReportsError(msg);
    } finally {
      setLoadingReports(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    await Promise.allSettled([fetchCampaigns(), fetchReports()]);
  }, [fetchCampaigns, fetchReports]);

  useEffect(() => {
    if (isAdmin) void refresh();
  }, [isAdmin, refresh]);

  const loadExtendedTab = useCallback(async (tab: AdminTab) => {
    if (tab === "campaigns" || tab === "music") return;
    setSectionLoading(true);
    try {
      if (tab === "accounts") {
        const res = await api.get("/v2/admin/advertising/accounts");
        setAccounts(Array.isArray(res.data) ? res.data : []);
      } else if (tab === "placements") {
        const res = await api.get("/v2/admin/advertising/placements");
        const list = Array.isArray(res.data) ? res.data : [];
        setPlacements(list);
        const edits: Record<string, { priceNaira: string; active: boolean }> = {};
        for (const p of list) {
          const rateMinor = p.weekly_rate_minor_ngn ?? p.price_per_week_minor_ngn;
          edits[p.placement_key] = {
            priceNaira: rateMinor !== null && rateMinor !== undefined
              ? String(Math.round(Number(rateMinor) / 100))
              : "",
            active: Boolean(p.is_enabled ?? p.active),
          };
        }
        setPlacementEdits(edits);
      } else if (tab === "pricing") {
        const res = await api.get("/v2/admin/advertising/pricing");
        const list = Array.isArray(res.data) ? res.data : [];
        setPricingPackages(list);
        const edits: Record<string, { priceNaira: string; discount: string; active: boolean }> = {};
        for (const pkg of list) {
          const code = pkg.package_code || pkg.package_key;
          edits[code] = {
            priceNaira: pkg.price_minor_ngn !== null && pkg.price_minor_ngn !== undefined
              ? String(Math.round(Number(pkg.price_minor_ngn) / 100))
              : "",
            discount: String(pkg.discount_percent ?? 0),
            active: Boolean(pkg.is_active ?? pkg.active),
          };
        }
        setPackageEdits(edits);
      } else if (tab === "payments") {
        const res = await api.get("/v2/admin/advertising/payments");
        setPayments(Array.isArray(res.data?.payments) ? res.data.payments : Array.isArray(res.data) ? res.data : []);
      } else if (tab === "analytics") {
        const [overviewRes, analyticsRes] = await Promise.all([
          api.get("/v2/admin/advertising/overview"),
          api.get("/v2/admin/advertising/analytics"),
        ]);
        setAnalyticsSummary(overviewRes.data);
        setAuditLogs(Array.isArray(analyticsRes.data?.audit_logs) ? analyticsRes.data.audit_logs : []);
      }
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSectionLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin && activeTab !== "campaigns" && activeTab !== "music") {
      void loadExtendedTab(activeTab);
    }
  }, [isAdmin, activeTab, loadExtendedTab]);

  if (!isAdmin) return <Navigate to="/app" replace />;

  const review = async (id: string, action: "approve" | "reject" | "pause" | "archive") => {
    setBusy(id + action);
    try {
      await api.post(`/v2/ads/brand/admin/campaigns/${id}/review`, {
        action,
        note: notes[id] || null,
      });
      toast.success(
        `Campaign ${({ approve: "approved", reject: "rejected", pause: "paused", archive: "archived" } as const)[action]}.`
      );
      await refresh();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy(null);
    }
  };

  const handleAccountAction = async (workspaceId: string, action: "verify" | "suspend" | "reactivate") => {
    setBusy(workspaceId + action);
    try {
      await api.post(`/v2/admin/advertising/accounts/${workspaceId}/action`, { action });
      toast.success(`Advertiser workspace ${action}d.`);
      await loadExtendedTab("accounts");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy(null);
    }
  };

  const handleSavePlacement = async (placementKey: string) => {
    const edit = placementEdits[placementKey];
    if (!edit) return;
    setBusy(`placement-${placementKey}`);
    try {
      const priceMinor = edit.priceNaira.trim() === "" ? null : Math.round(Number(edit.priceNaira) * 100);
      await api.patch(`/v2/admin/advertising/placements/${placementKey}`, {
        is_enabled: edit.active,
        weekly_rate_minor_ngn: priceMinor,
      });
      toast.success(`Updated placement ${placementKey} NGN pricing & inventory state.`);
      await loadExtendedTab("placements");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy(null);
    }
  };

  const handleSavePackage = async (pkg: any) => {
    const packageCode = pkg.package_code || pkg.package_key;
    const edit = packageEdits[packageCode];
    if (!edit) return;
    setBusy(`pkg-${packageCode}`);
    try {
      const priceMinor = edit.priceNaira.trim() === "" ? null : Math.round(Number(edit.priceNaira) * 100);
      await api.put("/v2/admin/advertising/pricing", {
        package_code: packageCode,
        name: pkg.name,
        division: pkg.division,
        description: pkg.description || "",
        duration_days: pkg.duration_days || 7,
        placement_keys: pkg.placement_keys || [],
        is_bundle: Boolean(pkg.is_bundle),
        is_subscription: Boolean(pkg.is_subscription),
        billing_interval_days: pkg.billing_interval_days ?? null,
        price_minor_ngn: priceMinor,
        discount_percent: Number(edit.discount || 0),
        is_active: edit.active,
      });
      toast.success(`Updated NGN pricing package ${packageCode}.`);
      await loadExtendedTab("pricing");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy(null);
    }
  };

  const handleRefundPayment = async (paymentId: string) => {
    setBusy(`refund-${paymentId}`);
    try {
      await api.post("/v2/admin/advertising/payments/refund", {
        payment_record_id: paymentId,
        reason: refundReason[paymentId] || "Administrative commercial refund",
      });
      toast.success("NGN payment refunded and campaign paused.");
      await loadExtendedTab("payments");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy(null);
    }
  };

  const reportById = new Map<string, Report>(reports.map((report) => [report.campaign_id, report] as [string, Report]));
  const visibleCampaigns =
    activeTab === "music"
      ? campaigns.filter((c) => c.campaign_type === "music")
      : campaigns;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8" data-testid="admin-brand-advertising">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="gx-eyebrow text-amber-300">GTEX COMMERCIAL NETWORK · ADMINISTRATION CENTRE</p>
          <h1 className="gx-display text-3xl font-black text-white sm:text-4xl">Advertising Review Desk</h1>
          <p className="mt-2 text-sm text-slate-400">
            Review brand and music submissions, manage advertiser accounts, configure Nigerian Naira (NGN) pricing, and inspect genuine campaign telemetry.
          </p>
        </div>
        <a
          href="/advertise"
          className="rounded-xl border border-emerald-400/35 bg-emerald-500/10 px-3.5 py-2 text-xs font-bold uppercase tracking-wider text-emerald-300 hover:bg-emerald-500/20"
        >
          View Public Commercial Portal
        </a>
      </header>

      {/* Commercial Administration Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3" data-testid="commercial-admin-tabs">
        {[
          { id: "campaigns" as const, label: "All Campaigns", icon: Megaphone },
          { id: "music" as const, label: "Music Promotion", icon: Music },
          { id: "accounts" as const, label: "Advertiser Accounts", icon: Building2 },
          { id: "placements" as const, label: "Placement Registry", icon: LayoutGrid },
          { id: "pricing" as const, label: "NGN Pricing & Packages", icon: Tag },
          { id: "payments" as const, label: "NGN Payments & Refunds", icon: CreditCard },
          { id: "analytics" as const, label: "Genuine Analytics & Audit", icon: BarChart3 },
        ].map((tab) => {
          const Icon = tab.icon;
          const isCurrent = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              data-testid={`admin-tab-${tab.id}`}
              className={`flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold uppercase tracking-wider transition-all ${
                isCurrent
                  ? "border border-amber-400/50 bg-amber-400/15 text-amber-200"
                  : "border border-white/10 bg-white/[0.03] text-slate-400 hover:text-white"
              }`}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB: CAMPAIGNS & MUSIC MODERATION QUEUE */}
      {(activeTab === "campaigns" || activeTab === "music") && (
        <section className="rounded-2xl border border-white/10 bg-slate-950/65 p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="gx-label">Moderation queue</p>
              <h2 className="text-lg font-black text-white">
                {activeTab === "music" ? "Music promotion campaigns" : "Brand and music campaigns"}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <select
                className="gx-input"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                data-testid="admin-status-filter"
              >
                <option value="">All statuses</option>
                {filters.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void refresh()}
                disabled={loadingCampaigns || loadingReports}
                className="flex items-center gap-1.5 rounded-lg border border-white/15 px-3 py-2 text-xs font-bold text-slate-200 hover:bg-white/10 transition-colors"
                data-testid="admin-refresh-btn"
              >
                <RefreshCw size={13} className={loadingCampaigns || loadingReports ? "animate-spin text-amber-400" : ""} />
                Refresh
              </button>
            </div>
          </div>

          {/* Independent Reports Warning Banner */}
          {reportsError && (
            <div
              className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200"
              data-testid="reports-error-banner"
            >
              <div className="flex items-center gap-2">
                <AlertCircle size={15} className="shrink-0 text-amber-400" />
                <span>Campaign telemetry could not be loaded: {reportsError}</span>
              </div>
              <button
                type="button"
                onClick={() => void fetchReports()}
                disabled={loadingReports}
                className="rounded bg-amber-500/20 px-2.5 py-1 text-[11px] font-bold uppercase text-amber-300 hover:bg-amber-500/30"
                data-testid="retry-reports-btn"
              >
                {loadingReports ? "Retrying…" : "Retry Telemetry"}
              </button>
            </div>
          )}

          {/* Campaign Queue Content States */}
          {loadingCampaigns ? (
            <p className="py-8 text-center text-sm text-slate-500" data-testid="loading-queue-indicator">
              Loading review queue…
            </p>
          ) : campaignsError ? (
            <div
              className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-center space-y-3"
              data-testid="campaigns-error-state"
            >
              <div className="flex justify-center text-rose-400">
                <AlertCircle size={24} />
              </div>
              <p className="text-sm font-bold text-rose-300">Failed to load campaign moderation queue</p>
              <p className="text-xs text-rose-200/80">{campaignsError}</p>
              <button
                type="button"
                onClick={() => void fetchCampaigns()}
                className="rounded-lg bg-rose-500/20 px-4 py-2 text-xs font-bold uppercase text-rose-200 hover:bg-rose-500/30 transition-all"
                data-testid="retry-campaigns-btn"
              >
                Retry Queue Loading
              </button>
            </div>
          ) : visibleCampaigns.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500" data-testid="empty-queue-message">
              No campaigns in this queue.
            </p>
          ) : (
            <div className="space-y-3" data-testid="campaigns-list">
              {visibleCampaigns.map((c) => {
                const report = reportById.get(c.id);
                const resolvedAudio = resolveCommercialMediaUrl(c.audio_url);
                return (
                  <article
                    key={c.id}
                    className="rounded-xl border border-white/10 bg-white/[0.025] p-4"
                    data-testid={`campaign-card-${c.id}`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-black text-white">{c.headline}</h3>
                          <span className="rounded bg-amber-400/15 px-2 py-0.5 text-[9px] font-black uppercase text-amber-200">
                            {c.campaign_type === "music" ? "GTEX TRAX" : "Brand"}
                          </span>
                          <span className="rounded bg-white/10 px-2 py-0.5 text-[9px] font-bold uppercase text-slate-300">
                            {c.status}
                          </span>
                          {c.payment_status && (
                            <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[9px] font-bold uppercase text-emerald-300">
                              Payment: {c.payment_status}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-slate-400">
                          {c.brand_name} · {(c.placements?.join(", ") || c.placement).replaceAll("_", " ")} · advertiser{" "}
                          {c.advertiser_id || "legacy/admin-seeded"}
                        </p>
                        {c.campaign_type === "music" && (
                          <p className="mt-1 text-xs text-amber-300">
                            Artist: {c.artist_name || c.brand_name} · Track: {c.track_title || c.headline}
                            {c.explicit_content ? " · EXPLICIT" : " · CLEAN"}
                            {c.rights_confirmed ? " · Rights Declared" : ""}
                          </p>
                        )}
                        <p className="mt-1 text-xs text-slate-500">
                          {c.start_at} → {c.end_at} ({c.duration_days || 7} days)
                        </p>
                        {c.destination_url && (
                          <a
                            href={c.destination_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-1 inline-block text-xs text-sky-300 underline"
                          >
                            Review destination
                          </a>
                        )}
                        {resolvedAudio && (
                          <div className="mt-2">
                            <audio controls preload="none" src={resolvedAudio} className="h-8 max-w-xs" />
                          </div>
                        )}
                      </div>
                      <span className="text-right text-xs text-slate-300">
                        {c.price_minor_ngn !== undefined && c.price_minor_ngn !== null
                          ? formatNairaFromKobo(c.price_minor_ngn)
                          : `${c.currency} ${c.budget_amount} budget`}
                        <br />
                        {c.pricing_model} · {c.unit_price}
                      </span>
                    </div>

                    {report && (
                      <div className="mt-3 flex flex-wrap gap-4 border-t border-white/10 pt-3 text-[10px] text-slate-400">
                        <span>{report.impressions} impressions</span>
                        <span>{report.clicks} clicks</span>
                        <span>{report.ctr_percent}% CTR</span>
                        <span>
                          Estimated spend {report.currency} {report.estimated_spend}
                        </span>
                      </div>
                    )}

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <input
                        className="gx-input min-w-[220px] flex-1"
                        placeholder="Review note / reason"
                        value={notes[c.id] || ""}
                        onChange={(e) => setNotes((v) => ({ ...v, [c.id]: e.target.value }))}
                        data-testid={`review-note-${c.id}`}
                      />
                      {["pending", "paused"].includes(c.status) && (
                        <>
                          <button
                            disabled={busy === c.id + "approve"}
                            onClick={() => void review(c.id, "approve")}
                            className="rounded-lg bg-emerald-400 px-3 py-2 text-[10px] font-black uppercase text-slate-950"
                            data-testid={`approve-btn-${c.id}`}
                          >
                            {c.status === "paused" ? "Resume" : "Approve"}
                          </button>
                          {c.status === "pending" && (
                            <button
                              disabled={busy === c.id + "reject"}
                              onClick={() => void review(c.id, "reject")}
                              className="rounded-lg border border-rose-400/35 px-3 py-2 text-[10px] font-black uppercase text-rose-300"
                              data-testid={`reject-btn-${c.id}`}
                            >
                              Reject
                            </button>
                          )}
                        </>
                      )}
                      {c.status === "approved" && (
                        <button
                          disabled={busy === c.id + "pause"}
                          onClick={() => void review(c.id, "pause")}
                          className="rounded-lg border border-amber-400/35 px-3 py-2 text-[10px] font-black uppercase text-amber-200"
                          data-testid={`pause-btn-${c.id}`}
                        >
                          Pause
                        </button>
                      )}
                      {c.status !== "archived" && (
                        <button
                          disabled={busy === c.id + "archive"}
                          onClick={() => void review(c.id, "archive")}
                          className="rounded-lg border border-white/15 px-3 py-2 text-[10px] font-black uppercase text-slate-300"
                          data-testid={`archive-btn-${c.id}`}
                        >
                          Archive
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* TAB: ADVERTISER ACCOUNTS */}
      {activeTab === "accounts" && (
        <section className="rounded-2xl border border-white/10 bg-slate-950/65 p-5" data-testid="admin-accounts-section">
          <div className="mb-4">
            <p className="gx-label">Commercial Network Accounts</p>
            <h2 className="text-lg font-black text-white">Registered Advertiser & Agency Workspaces</h2>
          </div>
          {sectionLoading ? (
            <p className="py-6 text-xs text-slate-400">Loading advertiser workspaces…</p>
          ) : accounts.length === 0 ? (
            <p className="py-6 text-xs text-slate-500">No advertiser workspaces registered yet.</p>
          ) : (
            <div className="space-y-3">
              {accounts.map((acc) => (
                <div
                  key={acc.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.025] p-4"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{acc.company_name}</span>
                      <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                        {acc.account_type}
                      </span>
                      <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-300">
                        {acc.status}
                      </span>
                      {acc.verified && (
                        <span className="rounded bg-sky-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-sky-300">
                          Verified
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      {acc.contact_email} · {acc.contact_phone || "No phone"} · Contact: {acc.contact_name || "N/A"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {!acc.verified && (
                      <button
                        type="button"
                        disabled={busy === acc.id + "verify"}
                        onClick={() => void handleAccountAction(acc.id, "verify")}
                        className="rounded-lg bg-emerald-400 px-3 py-1.5 text-[10px] font-black uppercase text-slate-950"
                      >
                        Verify
                      </button>
                    )}
                    {acc.status !== "suspended" ? (
                      <button
                        type="button"
                        disabled={busy === acc.id + "suspend"}
                        onClick={() => void handleAccountAction(acc.id, "suspend")}
                        className="rounded-lg border border-rose-400/40 px-3 py-1.5 text-[10px] font-black uppercase text-rose-300"
                      >
                        Suspend
                      </button>
                    ) : (
                      <button
                        type="button"
                        disabled={busy === acc.id + "reactivate"}
                        onClick={() => void handleAccountAction(acc.id, "reactivate")}
                        className="rounded-lg border border-emerald-400/40 px-3 py-1.5 text-[10px] font-black uppercase text-emerald-300"
                      >
                        Reactivate
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* TAB: PLACEMENT REGISTRY */}
      {activeTab === "placements" && (
        <section className="rounded-2xl border border-white/10 bg-slate-950/65 p-5" data-testid="admin-placements-section">
          <div className="mb-4">
            <p className="gx-label">Central Inventory Registry</p>
            <h2 className="text-lg font-black text-white">GTEX Advertising Placements & Weekly NGN Rates</h2>
            <p className="mt-1 text-xs text-slate-400">
              Leave the NGN rate blank to keep a placement in explicit unconfigured state until commercial pricing is approved.
            </p>
          </div>
          {sectionLoading ? (
            <p className="py-6 text-xs text-slate-400">Loading placement inventory…</p>
          ) : (
            <div className="space-y-3">
              {placements.map((pl) => {
                const edit = placementEdits[pl.placement_key] || { priceNaira: "", active: true };
                return (
                  <div
                    key={pl.placement_key}
                    className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.025] p-4"
                  >
                    <div className="max-w-xl">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{pl.name}</span>
                        <span className="gx-mono text-[10px] text-slate-400">({pl.placement_key})</span>
                        <span className="rounded bg-amber-400/15 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-200">
                          {pl.pricing_status === "configured"
                            ? `${formatNairaFromKobo(pl.price_per_week_minor_ngn)} / 7 days`
                            : "Pricing Unconfigured"}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">{pl.description}</p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        Dimensions: {pl.aspect_ratio} ({pl.recommended_width}×{pl.recommended_height}) · Silent required:{" "}
                        {pl.silent_required ? "Yes" : "No"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="flex items-center gap-1.5 text-xs text-slate-300">
                        <input
                          type="checkbox"
                          checked={edit.active}
                          onChange={(e) =>
                            setPlacementEdits((prev) => ({
                              ...prev,
                              [pl.placement_key]: { ...edit, active: e.target.checked },
                            }))
                          }
                        />
                        Enabled
                      </label>
                      <input
                        type="number"
                        min="0"
                        placeholder="Weekly rate in ₦"
                        value={edit.priceNaira}
                        onChange={(e) =>
                          setPlacementEdits((prev) => ({
                            ...prev,
                            [pl.placement_key]: { ...edit, priceNaira: e.target.value },
                          }))
                        }
                        className="gx-input w-40"
                      />
                      <button
                        type="button"
                        disabled={busy === `placement-${pl.placement_key}`}
                        onClick={() => void handleSavePlacement(pl.placement_key)}
                        className="rounded-lg bg-emerald-400 px-3 py-2 text-[10px] font-black uppercase text-slate-950"
                      >
                        Save NGN Rate
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* TAB: NGN PRICING PACKAGES */}
      {activeTab === "pricing" && (
        <section className="rounded-2xl border border-white/10 bg-slate-950/65 p-5" data-testid="admin-pricing-section">
          <div className="mb-4">
            <p className="gx-label">Nigerian Naira (NGN) Commercial Packages</p>
            <h2 className="text-lg font-black text-white">Brand & Music Promotion Packages</h2>
            <p className="mt-1 text-xs text-slate-400">
              All amounts are stored in integer kobo and displayed in NGN (₦). Packages without configured NGN prices block self-serve checkout until configured.
            </p>
          </div>
          {sectionLoading ? (
            <p className="py-6 text-xs text-slate-400">Loading NGN pricing packages…</p>
          ) : (
            <div className="space-y-3">
              {pricingPackages.map((pkg) => {
                const pkgCode = pkg.package_code || pkg.package_key;
                const edit = packageEdits[pkgCode] || { priceNaira: "", discount: "0", active: true };
                return (
                  <div
                    key={pkgCode}
                    className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.025] p-4"
                  >
                    <div className="max-w-xl">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{pkg.name}</span>
                        <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-300">
                          {pkg.division} · {pkg.duration_days} days
                        </span>
                        <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                          {pkg.pricing_configured || pkg.pricing_status === "configured"
                            ? formatNairaFromKobo(pkg.price_minor_ngn)
                            : "NGN Price Unconfigured"}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">{pkg.description}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        type="number"
                        min="0"
                        placeholder="Package price in ₦"
                        value={edit.priceNaira}
                        onChange={(e) =>
                          setPackageEdits((prev) => ({
                            ...prev,
                            [pkgCode]: { ...edit, priceNaira: e.target.value },
                          }))
                        }
                        className="gx-input w-40"
                      />
                      <input
                        type="number"
                        min="0"
                        max="90"
                        placeholder="Discount %"
                        value={edit.discount}
                        onChange={(e) =>
                          setPackageEdits((prev) => ({
                            ...prev,
                            [pkgCode]: { ...edit, discount: e.target.value },
                          }))
                        }
                        className="gx-input w-24"
                      />
                      <button
                        type="button"
                        disabled={busy === `pkg-${pkgCode}`}
                        onClick={() => void handleSavePackage(pkg)}
                        className="rounded-lg bg-emerald-400 px-3 py-2 text-[10px] font-black uppercase text-slate-950"
                      >
                        Update NGN Package
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* TAB: PAYMENTS, INVOICES & REFUNDS */}
      {activeTab === "payments" && (
        <section className="rounded-2xl border border-white/10 bg-slate-950/65 p-5" data-testid="admin-payments-section">
          <div className="mb-4">
            <p className="gx-label">Finance & Reconciliation</p>
            <h2 className="text-lg font-black text-white">NGN Payments, Provider References & Finance Refunds</h2>
            <p className="mt-1 text-xs text-slate-400">
              Refund actions require Finance Admin or Super Admin permissions and are recorded in the immutable commercial audit log.
            </p>
          </div>
          {sectionLoading ? (
            <p className="py-6 text-xs text-slate-400">Loading NGN payment ledger…</p>
          ) : payments.length === 0 ? (
            <p className="py-6 text-xs text-slate-500">No commercial payment records yet.</p>
          ) : (
            <div className="space-y-3">
              {payments.map((pay) => (
                <div
                  key={pay.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.025] p-4"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="gx-mono font-bold text-white">{pay.reference}</span>
                      <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                        {formatNairaFromKobo(pay.amount_minor_ngn)}
                      </span>
                      <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-300">
                        {pay.provider} · {pay.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      Campaign: {pay.campaign_id} · Workspace: {pay.workspace_id}
                    </p>
                  </div>
                  {pay.status === "paid" && (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="Refund reason"
                        value={refundReason[pay.id] || ""}
                        onChange={(e) => setRefundReason((prev) => ({ ...prev, [pay.id]: e.target.value }))}
                        className="gx-input w-48"
                      />
                      <button
                        type="button"
                        disabled={busy === `refund-${pay.id}`}
                        onClick={() => void handleRefundPayment(pay.id)}
                        className="rounded-lg border border-rose-400/40 bg-rose-500/10 px-3 py-2 text-[10px] font-black uppercase text-rose-300"
                      >
                        Issue Refund
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* TAB: GENUINE ANALYTICS & AUDIT LOGS */}
      {activeTab === "analytics" && (
        <section className="space-y-6" data-testid="admin-analytics-section">
          <div className="rounded-2xl border border-white/10 bg-slate-950/65 p-5">
            <p className="gx-label">Verified Delivery Telemetry</p>
            <h2 className="text-lg font-black text-white">Commercial Network Performance & NGN Revenue</h2>
            {analyticsSummary ? (
              <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-[10px] font-bold uppercase text-slate-400">Verified NGN Revenue</p>
                  <p className="mt-1 text-xl font-black text-emerald-400">
                    {analyticsSummary.total_revenue_formatted_ngn}
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-[10px] font-bold uppercase text-slate-400">Active / Total Campaigns</p>
                  <p className="mt-1 text-xl font-black text-white">
                    {analyticsSummary.active_campaigns} / {analyticsSummary.total_campaigns}
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-[10px] font-bold uppercase text-slate-400">Brand Impressions / Clicks</p>
                  <p className="mt-1 text-xl font-black text-sky-300">
                    {analyticsSummary.total_impressions} / {analyticsSummary.total_clicks}
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-[10px] font-bold uppercase text-slate-400">Music Plays / Qualified</p>
                  <p className="mt-1 text-xl font-black text-amber-300">
                    {analyticsSummary.total_music_plays} / {analyticsSummary.total_qualified_listens}
                  </p>
                </div>
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-400">Loading verified commercial analytics…</p>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-950/65 p-5">
            <div className="flex items-center gap-2">
              <ShieldAlert size={16} className="text-amber-400" />
              <h3 className="text-sm font-black uppercase tracking-wider text-white">Commercial Audit Trail</h3>
            </div>
            <div className="mt-3 space-y-2">
              {auditLogs.length === 0 ? (
                <p className="text-xs text-slate-500">No administrative actions recorded yet.</p>
              ) : (
                auditLogs.slice(0, 25).map((log) => (
                  <div
                    key={log.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-xs"
                  >
                    <span className="font-bold text-slate-200">{log.action}</span>
                    <span className="text-slate-400">
                      {log.target_type} · {log.target_id}
                    </span>
                    <span className="gx-mono text-[10px] text-slate-500">{log.created_at}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
