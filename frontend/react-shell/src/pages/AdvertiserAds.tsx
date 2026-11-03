import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertCircle, RefreshCw } from "lucide-react";
import { api, errMsg } from "@/lib/api";

type AdvertiserProfile = {
  company_name: string;
  contact_name: string;
  website_url?: string | null;
  billing_email: string;
};
type Campaign = {
  id: string;
  campaign_type: "brand" | "music";
  brand_name: string;
  headline: string;
  description: string;
  placement: string;
  destination_url: string;
  logo_url?: string | null;
  creative_url?: string | null;
  start_at: string;
  end_at: string;
  budget_amount: string;
  currency: string;
  pricing_model: "CPM" | "CPC";
  unit_price: string;
  status: string;
  review_note?: string | null;
  music_target_type?: string | null;
  music_target_id?: string | null;
  music_title?: string | null;
  music_artist_name?: string | null;
  music_playlist_name?: string | null;
  music_genre?: string | null;
};
type HistoryEvent = {
  id: string;
  actor_user_id: string;
  action: string;
  note?: string | null;
  from_status: string;
  to_status: string;
  created_at: string;
};
type Report = {
  campaign_id: string;
  campaign_name: string;
  currency: string;
  budget_amount: string;
  impressions: number;
  clicks: number;
  conversions: number;
  ctr_percent: number;
  estimated_spend: string;
  estimated_budget_remaining: string;
  billing_state: string;
};

const emptyProfile: AdvertiserProfile = {
  company_name: "",
  contact_name: "",
  website_url: "",
  billing_email: "",
};
const emptyCampaign = {
  campaign_type: "brand" as "brand" | "music",
  brand_name: "",
  headline: "",
  description: "",
  placement: "homepage_rail",
  destination_url: "",
  logo_url: "",
  creative_url: "",
  start_at: "",
  end_at: "",
  budget_amount: "100",
  currency: "USD",
  pricing_model: "CPM" as "CPM" | "CPC",
  unit_price: "5",
  music_target_type: "track",
  music_target_id: "",
  music_title: "",
  music_artist_name: "",
  music_playlist_name: "",
  music_genre: "",
};
const fieldClass = "gx-input w-full";
const labelClass = "mb-1 block text-[10px] font-bold uppercase tracking-wider text-slate-400";

function localDate(value: string) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
function utcDate(value: string) {
  return value ? new Date(value).toISOString() : "";
}
function money(value: string, currency: string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;
  try { return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount); }
  catch { return `${currency} ${amount.toFixed(2)}`; }
}

export default function AdvertiserAds() {
  const [profile, setProfile] = useState<AdvertiserProfile>(emptyProfile);
  const [hasProfile, setHasProfile] = useState(false);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [historyById, setHistoryById] = useState<Record<string, HistoryEvent[]>>({});
  const [expandedHistory, setExpandedHistory] = useState<string | null>(null);
  const [form, setForm] = useState({ ...emptyCampaign });
  const [editingId, setEditingId] = useState<string | null>(null);
  
  // Independent request states
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [loadingCampaigns, setLoadingCampaigns] = useState(true);
  const [loadingReports, setLoadingReports] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);
  const [reportsError, setReportsError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchProfile = useCallback(async () => {
    setLoadingProfile(true);
    setProfileError(null);
    try {
      const response = await api.get("/v2/ads/brand/profile");
      const data = response.data;
      setHasProfile(Boolean(data));
      setProfile(data || emptyProfile);
      setProfileError(null);
    } catch (error) {
      const msg = errMsg(error);
      setProfileError(msg);
    } finally {
      setLoadingProfile(false);
    }
  }, []);

  const fetchCampaigns = useCallback(async () => {
    setLoadingCampaigns(true);
    setCampaignsError(null);
    try {
      const response = await api.get("/v2/ads/brand/campaigns");
      const data = response.data;
      setCampaigns(Array.isArray(data) ? data : []);
      setCampaignsError(null);
    } catch (error) {
      const msg = errMsg(error);
      setCampaignsError(msg);
    } finally {
      setLoadingCampaigns(false);
    }
  }, []);

  const fetchReports = useCallback(async () => {
    setLoadingReports(true);
    setReportsError(null);
    try {
      const response = await api.get("/v2/ads/brand/reports");
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
    await Promise.allSettled([fetchProfile(), fetchCampaigns(), fetchReports()]);
  }, [fetchProfile, fetchCampaigns, fetchReports]);

  useEffect(() => { void refresh(); }, [refresh]);

  const updateForm = (key: keyof typeof emptyCampaign, value: string) => {
    setForm((current) => ({ ...current, [key]: value }) as typeof emptyCampaign);
  };

  const saveProfile = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const response = await api.put("/v2/ads/brand/profile", profile);
      setProfile(response.data);
      setHasProfile(true);
      setProfileError(null);
      toast.success("Advertiser profile saved.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  const resetEditor = () => {
    setForm({ ...emptyCampaign });
    setEditingId(null);
  };

  const editCampaign = (campaign: Campaign) => {
    setEditingId(campaign.id);
    setForm({
      campaign_type: campaign.campaign_type,
      brand_name: campaign.brand_name,
      headline: campaign.headline,
      description: campaign.description || "",
      placement: campaign.placement,
      destination_url: campaign.destination_url,
      logo_url: campaign.logo_url || "",
      creative_url: campaign.creative_url || "",
      start_at: localDate(campaign.start_at),
      end_at: localDate(campaign.end_at),
      budget_amount: String(campaign.budget_amount),
      currency: campaign.currency,
      pricing_model: campaign.pricing_model,
      unit_price: String(campaign.unit_price),
      music_target_type: campaign.music_target_type || "track",
      music_target_id: campaign.music_target_id || "",
      music_title: campaign.music_title || "",
      music_artist_name: campaign.music_artist_name || "",
      music_playlist_name: campaign.music_playlist_name || "",
      music_genre: campaign.music_genre || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const saveCampaign = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.start_at || !form.end_at) {
      toast.error("Choose a campaign start and end date.");
      return;
    }
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        ...form,
        start_at: utcDate(form.start_at),
        end_at: utcDate(form.end_at),
      };
      if (form.campaign_type === "brand") {
        for (const key of ["music_target_type", "music_target_id", "music_title", "music_artist_name", "music_playlist_name", "music_genre"]) {
          delete payload[key];
        }
      }
      if (editingId) {
        await api.put(`/v2/ads/brand/campaigns/${editingId}`, payload);
        toast.success("Draft campaign updated.");
      } else {
        await api.post("/v2/ads/brand/campaigns", payload);
        toast.success("Campaign draft created.");
      }
      resetEditor();
      await refresh();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  const toggleHistory = async (campaignId: string) => {
    if (expandedHistory === campaignId) {
      setExpandedHistory(null);
      return;
    }
    setExpandedHistory(campaignId);
    if (historyById[campaignId]) return;
    try {
      const response = await api.get(`/v2/ads/brand/campaigns/${campaignId}/history`);
      setHistoryById((current) => ({ ...current, [campaignId]: Array.isArray(response.data) ? response.data : [] }));
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  const submitCampaign = async (campaignId: string) => {
    setSaving(true);
    try {
      await api.post(`/v2/ads/brand/campaigns/${campaignId}/submit`);
      toast.success("Campaign submitted for GTEX review.");
      await refresh();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8" data-testid="advertiser-ads-page">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="gx-eyebrow text-emerald-300">GTEX COMMERCIAL NETWORK</p>
          <h1 className="gx-display text-3xl font-black text-white sm:text-4xl">Advertiser Studio</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">Prepare brand placements and GTEX TRAX promotions, submit them for review, and monitor delivery reports.</p>
        </div>
        <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1.5 text-[10px] font-black uppercase tracking-wider text-amber-200">Campaigns require approval</span>
      </header>

      <section className="grid gap-5 xl:grid-cols-[.85fr_1.15fr]">
        <form onSubmit={saveProfile} className="space-y-4 rounded-2xl border border-gtex-graphite bg-gtex-slate/80 p-6 shadow-xl" data-testid="advertiser-profile-form">
          <div>
            <p className="gx-label">Advertiser account</p>
            <h2 className="mt-1 text-lg font-black text-white">Business profile</h2>
            <p className="mt-1 text-xs text-slate-500">This profile is associated with your signed-in GTEX user account.</p>
          </div>
          {profileError && (
            <div className="flex items-center justify-between gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200" data-testid="profile-error-banner">
              <div className="flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0 text-rose-400" />
                <span>Profile sync error: {profileError}</span>
              </div>
              <button type="button" onClick={() => void fetchProfile()} className="font-bold uppercase text-rose-300 hover:text-white" data-testid="retry-profile-btn">Retry</button>
            </div>
          )}
          <div><label className={labelClass}>Company / brand name</label><input className={fieldClass} required maxLength={160} value={profile.company_name} onChange={(e) => setProfile({ ...profile, company_name: e.target.value })}/></div>
          <div><label className={labelClass}>Contact name</label><input className={fieldClass} required maxLength={160} value={profile.contact_name} onChange={(e) => setProfile({ ...profile, contact_name: e.target.value })}/></div>
          <div><label className={labelClass}>Website (optional)</label><input className={fieldClass} type="url" placeholder="https://" value={profile.website_url || ""} onChange={(e) => setProfile({ ...profile, website_url: e.target.value })}/></div>
          <div><label className={labelClass}>Billing / contact email</label><input className={fieldClass} required type="email" value={profile.billing_email} onChange={(e) => setProfile({ ...profile, billing_email: e.target.value })}/></div>
          <button disabled={saving} className="w-full rounded-xl bg-emerald-400 px-4 py-2.5 text-xs font-black uppercase tracking-wider text-slate-950 disabled:opacity-50">{saving ? "Saving…" : hasProfile ? "Update advertiser profile" : "Create advertiser profile"}</button>
        </form>

        <form onSubmit={saveCampaign} className="space-y-4 rounded-2xl border border-gtex-emerald/30 bg-gtex-slate/80 p-6 shadow-xl" data-testid="campaign-workspace-form">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><p className="gx-label">Campaign workspace</p><h2 className="mt-1 text-lg font-black text-white">{editingId ? "Edit campaign draft" : "Create a campaign"}</h2></div>
            {editingId && <button type="button" onClick={resetEditor} className="text-xs font-bold text-slate-400 hover:text-white">Cancel edit</button>}
          </div>
          {!hasProfile && !loadingProfile && <p className="rounded-lg border border-amber-400/25 bg-amber-400/5 p-3 text-xs text-amber-200" data-testid="no-profile-warning">Save your advertiser profile before creating a campaign.</p>}
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className={labelClass}>Campaign type</label><select className={fieldClass} value={form.campaign_type} onChange={(e) => { const type = e.target.value as "brand" | "music"; setForm((v) => ({ ...v, campaign_type: type, placement: type === "brand" ? "homepage_rail" : "music_track" })); }}><option value="brand">Brand advertising</option><option value="music">GTEX TRAX sponsored promotion</option></select></div>
            <div><label className={labelClass}>Placement</label><select className={fieldClass} value={form.placement} onChange={(e) => updateForm("placement", e.target.value)}>{(form.campaign_type === "brand" ? [["homepage_rail","Homepage advertising rail"],["homepage_hero","Homepage hero"],["partner_showcase","Partner showcase"],["auth_canvas","Login / signup canvas"]] : [["music_track","Sponsored track"],["music_artist","Sponsored artist"],["music_playlist","Sponsored playlist"]]).map(([value,label]) => <option value={value} key={value}>{label}</option>)}</select></div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className={labelClass}>Advertised brand / label</label><input className={fieldClass} required maxLength={160} value={form.brand_name} onChange={(e) => updateForm("brand_name", e.target.value)}/></div>
            <div><label className={labelClass}>Headline</label><input className={fieldClass} required maxLength={180} value={form.headline} onChange={(e) => updateForm("headline", e.target.value)}/></div>
          </div>
          <div><label className={labelClass}>Description</label><textarea className={fieldClass} rows={2} maxLength={360} value={form.description} onChange={(e) => updateForm("description", e.target.value)}/></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className={labelClass}>Destination URL</label><input className={fieldClass} type="url" placeholder="https://" required value={form.destination_url} onChange={(e) => updateForm("destination_url", e.target.value)}/></div>
            <div><label className={labelClass}>Creative image URL (optional)</label><input className={fieldClass} type="url" placeholder="https://" value={form.creative_url} onChange={(e) => updateForm("creative_url", e.target.value)}/></div>
          </div>
          <div><label className={labelClass}>Logo URL (optional)</label><input className={fieldClass} type="url" placeholder="https://" value={form.logo_url} onChange={(e) => updateForm("logo_url", e.target.value)}/></div>
          {form.campaign_type === "music" && <div className="space-y-3 rounded-xl border border-amber-400/20 bg-amber-400/[0.04] p-3">
            <p className="text-[10px] font-black uppercase tracking-wider text-amber-200">Sponsored content target</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div><label className={labelClass}>Target type</label><select className={fieldClass} value={form.music_target_type} onChange={(e) => setForm((v) => ({ ...v, music_target_type: e.target.value, placement: e.target.value === "artist" ? "music_artist" : e.target.value === "playlist" ? "music_playlist" : "music_track" }))}><option value="track">Track</option><option value="artist">Artist</option><option value="playlist">Playlist</option></select></div>
              <div><label className={labelClass}>Stable GTEX TRAX ID</label><input className={fieldClass} required value={form.music_target_id} onChange={(e) => updateForm("music_target_id", e.target.value)} placeholder="Track / artist / playlist ID"/></div>
            </div>
            {form.music_target_type === "track" && <div className="grid gap-3 sm:grid-cols-2"><div><label className={labelClass}>Track title</label><input className={fieldClass} required value={form.music_title} onChange={(e) => updateForm("music_title", e.target.value)}/></div><div><label className={labelClass}>Artist</label><input className={fieldClass} required value={form.music_artist_name} onChange={(e) => updateForm("music_artist_name", e.target.value)}/></div></div>}
            {form.music_target_type === "artist" && <div><label className={labelClass}>Artist name</label><input className={fieldClass} required value={form.music_artist_name} onChange={(e) => updateForm("music_artist_name", e.target.value)}/></div>}
            {form.music_target_type === "playlist" && <div><label className={labelClass}>Playlist name</label><input className={fieldClass} required value={form.music_playlist_name} onChange={(e) => updateForm("music_playlist_name", e.target.value)}/></div>}
            <div><label className={labelClass}>Genre (optional)</label><input className={fieldClass} value={form.music_genre} onChange={(e) => updateForm("music_genre", e.target.value)}/></div>
          </div>}
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className={labelClass}>Start date / time</label><input className={fieldClass} type="datetime-local" required value={form.start_at} onChange={(e) => updateForm("start_at", e.target.value)}/></div>
            <div><label className={labelClass}>End date / time</label><input className={fieldClass} type="datetime-local" required value={form.end_at} onChange={(e) => updateForm("end_at", e.target.value)}/></div>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            <div><label className={labelClass}>Budget</label><input className={fieldClass} type="number" min="0.01" step="0.01" required value={form.budget_amount} onChange={(e) => updateForm("budget_amount", e.target.value)}/></div>
            <div><label className={labelClass}>Currency</label><input className={fieldClass} maxLength={3} required value={form.currency} onChange={(e) => updateForm("currency", e.target.value.toUpperCase())}/></div>
            <div><label className={labelClass}>Pricing</label><select className={fieldClass} value={form.pricing_model} onChange={(e) => updateForm("pricing_model", e.target.value)}><option value="CPM">CPM</option><option value="CPC">CPC</option></select></div>
            <div><label className={labelClass}>Rate / 1k or click</label><input className={fieldClass} type="number" min="0.0001" step="0.0001" required value={form.unit_price} onChange={(e) => updateForm("unit_price", e.target.value)}/></div>
          </div>
          <p className="text-[10px] leading-relaxed text-slate-500">Rates and spend are planning/reporting estimates only. No money is collected or deducted through this portal. Commercial terms and any payment flow require separate approval and integration.</p>
          <button disabled={!hasProfile || saving} className="w-full rounded-xl bg-emerald-400 px-4 py-2.5 text-xs font-black uppercase tracking-wider text-slate-950 disabled:opacity-40">{saving ? "Saving…" : editingId ? "Save campaign draft" : "Create campaign draft"}</button>
        </form>
      </section>

      <section className="rounded-2xl border border-gtex-graphite bg-gtex-slate/80 p-6 shadow-xl" data-testid="advertiser-inventory-section">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div><p className="gx-label">Your inventory</p><h2 className="text-lg font-black text-white">Campaigns & review status</h2></div>
          <button
            onClick={() => void refresh()}
            disabled={loadingCampaigns || loadingReports || loadingProfile}
            className="flex items-center gap-1.5 text-xs font-bold text-emerald-300 hover:text-white transition-colors"
            data-testid="advertiser-refresh-btn"
          >
            <RefreshCw size={12} className={loadingCampaigns ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        {loadingCampaigns ? (
          <p className="py-8 text-center text-sm text-slate-500" data-testid="loading-campaigns-indicator">Loading campaigns…</p>
        ) : campaignsError ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-center space-y-3" data-testid="advertiser-campaigns-error-state">
            <div className="flex justify-center text-rose-400">
              <AlertCircle size={24} />
            </div>
            <p className="text-sm font-bold text-rose-300">Failed to load campaigns</p>
            <p className="text-xs text-rose-200/80">{campaignsError}</p>
            <button
              type="button"
              onClick={() => void fetchCampaigns()}
              className="rounded-lg bg-rose-500/20 px-4 py-2 text-xs font-bold uppercase text-rose-200 hover:bg-rose-500/30 transition-all"
              data-testid="retry-advertiser-campaigns-btn"
            >
              Retry Loading Campaigns
            </button>
          </div>
        ) : campaigns.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500" data-testid="empty-campaigns-message">No campaigns created yet.</p>
        ) : (
          <div className="space-y-3" data-testid="advertiser-campaigns-list">
            {campaigns.map((campaign) => (
              <article key={campaign.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.025] p-4" data-testid={`campaign-row-${campaign.id}`}>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-black text-white">{campaign.headline}</h3>
                    <span className="rounded bg-white/10 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider text-slate-300">{campaign.status}</span>
                    <span className="text-[9px] font-bold uppercase text-amber-300">{campaign.campaign_type === "music" ? "GTEX TRAX" : campaign.placement.replaceAll("_"," ")}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">{campaign.brand_name} · {campaign.start_at.slice(0,10)} → {campaign.end_at.slice(0,10)}</p>
                  {campaign.review_note && <p className="mt-1 text-xs text-amber-200">Review note: {campaign.review_note}</p>}
                </div>
                <div className="flex flex-wrap gap-2">
                  {["draft","rejected"].includes(campaign.status) && (
                    <>
                      <button onClick={() => editCampaign(campaign)} className="rounded-lg border border-white/15 px-3 py-2 text-[10px] font-black uppercase text-slate-200 hover:bg-white/10">Edit</button>
                      <button disabled={saving} onClick={() => void submitCampaign(campaign.id)} className="rounded-lg bg-emerald-400 px-3 py-2 text-[10px] font-black uppercase text-slate-950 disabled:opacity-50">Submit for review</button>
                    </>
                  )}
                  <button onClick={() => void toggleHistory(campaign.id)} className="rounded-lg border border-white/15 px-3 py-2 text-[10px] font-black uppercase text-slate-300 hover:bg-white/10">Review history</button>
                </div>
                {expandedHistory === campaign.id && (
                  <div className="mt-3 w-full space-y-2 rounded-lg border border-white/10 bg-black/25 p-3">
                    {(historyById[campaign.id] || []).length === 0 ? (
                      <p className="text-xs text-slate-500">No review events are recorded yet.</p>
                    ) : (
                      historyById[campaign.id].map((event) => (
                        <div key={event.id} className="flex flex-wrap justify-between gap-2 border-b border-white/5 pb-2 text-[10px] last:border-0">
                          <span className="font-bold uppercase text-emerald-300">{event.action}: {event.from_status} → {event.to_status}</span>
                          <span className="text-slate-500">{new Date(event.created_at).toLocaleString()}</span>
                          {event.note && <p className="w-full text-slate-300">{event.note}</p>}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-gtex-graphite bg-gtex-slate/80 p-6 shadow-xl" data-testid="advertiser-reports-section">
        <div className="mb-3">
          <p className="gx-label">Performance</p>
          <h2 className="text-lg font-black text-white">Campaign reporting</h2>
          <p className="mt-1 text-[10px] text-amber-200">All counts and spend figures below are estimated telemetry. Browser events are not verified billable actions.</p>
        </div>

        {reportsError ? (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4" data-testid="advertiser-reports-error-state">
            <div className="flex items-center gap-2">
              <AlertCircle size={15} className="shrink-0 text-rose-400" />
              <span className="text-xs text-rose-200">Campaign telemetry could not be loaded: {reportsError}</span>
            </div>
            <button
              type="button"
              onClick={() => void fetchReports()}
              disabled={loadingReports}
              className="rounded bg-rose-500/20 px-2.5 py-1 text-[11px] font-bold uppercase text-rose-300 hover:bg-rose-500/30"
              data-testid="retry-advertiser-reports-btn"
            >
              {loadingReports ? "Retrying…" : "Retry Telemetry"}
            </button>
          </div>
        ) : reports.length === 0 ? (
          <p className="py-5 text-center text-sm text-slate-500" data-testid="empty-reports-message">Reports will appear when campaign events are recorded.</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2" data-testid="advertiser-reports-grid">
            {reports.map((report) => (
              <div key={report.campaign_id} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                <h3 className="font-bold text-white">{report.campaign_name}</h3>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                  {[["Impressions",report.impressions],["Clicks",report.clicks],["CTR",`${report.ctr_percent}%`]].map(([label,value]) => (
                    <div key={String(label)} className="rounded-lg bg-black/30 p-2">
                      <p className="text-[9px] uppercase text-slate-500">{label}</p>
                      <p className="gx-mono mt-1 text-sm font-black text-white">{value}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex justify-between text-xs">
                  <span className="text-slate-400">Estimated spend</span>
                  <strong className="text-emerald-300">{money(report.estimated_spend, report.currency)}</strong>
                </div>
                <div className="mt-1 flex justify-between text-xs">
                  <span className="text-slate-400">Est. budget remaining</span>
                  <strong className="text-white">{money(report.estimated_budget_remaining, report.currency)}</strong>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
