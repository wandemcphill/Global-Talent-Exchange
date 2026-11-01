import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, errMsg } from "@/lib/api";

type Campaign = {
  id: string;
  campaign_type: string;
  brand_name: string;
  headline: string;
  description: string;
  placement: string;
  destination_url: string;
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
type Report = {
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
const filters = ["pending","approved","rejected","paused","archived","draft"];

export default function AdminAdvertising() {
  const { user } = useAuth();
  const isAdmin = ["admin", "super_admin"].includes(String(user?.role || "").toLowerCase());
  const [campaigns,setCampaigns]=useState<Campaign[]>([]);
  const [reports,setReports]=useState<Report[]>([]);
  const [filter,setFilter]=useState("pending");
  const [notes,setNotes]=useState<Record<string,string>>({});
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState<string|null>(null);

  const refresh=useCallback(async()=>{
    setLoading(true);
    try {
      const [campaignResponse,reportResponse]=await Promise.all([
        api.get("/ads/brand/admin/campaigns",{params:filter?{status:filter}:{}}),
        api.get("/ads/brand/admin/reports"),
      ]);
      setCampaigns(Array.isArray(campaignResponse.data)?campaignResponse.data:[]);
      setReports(reportResponse.data?.reports||[]);
    } catch(error) { toast.error(errMsg(error)); }
    finally { setLoading(false); }
  },[filter]);

  useEffect(()=>{if(isAdmin) void refresh();},[isAdmin,refresh]);

  if (!isAdmin) return <Navigate to="/app" replace />;

  const review=async(id:string,action:"approve"|"reject"|"pause"|"archive")=>{
    setBusy(id+action);
    try {
      await api.post(`/ads/brand/admin/campaigns/${id}/review`,{action,note:notes[id]||null});
      toast.success(`Campaign ${({ approve: "approved", reject: "rejected", pause: "paused", archive: "archived" } as const)[action]}.`);
      await refresh();
    } catch(error) {toast.error(errMsg(error));}
    finally {setBusy(null);}
  };

  const reportById = new Map<string, Report>(reports.map((report) => [report.campaign_id, report] as [string, Report]));
  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8" data-testid="admin-brand-advertising">
    <header><p className="gx-eyebrow text-amber-300">ADMINISTRATION · COMMERCIAL SAFETY</p><h1 className="gx-display text-3xl font-black text-white sm:text-4xl">Advertising Review Desk</h1><p className="mt-2 text-sm text-slate-400">Review submissions, control delivery state and inspect estimated campaign telemetry.</p></header>
    <div className="rounded-xl border border-amber-400/25 bg-amber-400/[0.05] p-3 text-xs text-amber-100">No payment provider is connected. Spend is an estimate derived from browser-reported events and must not be treated as settled revenue or a billable invoice.</div>
    <section className="rounded-2xl border border-white/10 bg-slate-950/65 p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="gx-label">Moderation queue</p><h2 className="text-lg font-black text-white">Brand and music campaigns</h2></div><div className="flex gap-2"><select className="gx-input" value={filter} onChange={e=>setFilter(e.target.value)}><option value="">All statuses</option>{filters.map(s=><option key={s} value={s}>{s}</option>)}</select><button onClick={()=>void refresh()} className="rounded-lg border border-white/15 px-3 text-xs font-bold text-slate-200">Refresh</button></div></div>
      {loading?<p className="py-8 text-center text-sm text-slate-500">Loading review queue…</p>:campaigns.length===0?<p className="py-8 text-center text-sm text-slate-500">No campaigns in this queue.</p>:<div className="space-y-3">{campaigns.map(c=>{const report=reportById.get(c.id);return <article key={c.id} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="font-black text-white">{c.headline}</h3><span className="rounded bg-amber-400/15 px-2 py-0.5 text-[9px] font-black uppercase text-amber-200">{c.campaign_type==="music"?"GTEX TRAX":"Brand"}</span><span className="rounded bg-white/10 px-2 py-0.5 text-[9px] font-bold uppercase text-slate-300">{c.status}</span></div><p className="mt-1 text-xs text-slate-400">{c.brand_name} · {c.placement.replaceAll("_"," ")} · advertiser {c.advertiser_id||"legacy/admin-seeded"}</p><p className="mt-1 text-xs text-slate-500">{c.start_at} → {c.end_at}</p><a href={c.destination_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-block text-xs text-sky-300 underline">Review destination</a></div><span className="text-right text-xs text-slate-300">{c.currency} {c.budget_amount} budget<br/>{c.pricing_model} · {c.unit_price}</span></div>
        {report&&<div className="mt-3 flex flex-wrap gap-4 border-t border-white/10 pt-3 text-[10px] text-slate-400"><span>{report.impressions} impressions</span><span>{report.clicks} clicks</span><span>{report.ctr_percent}% CTR</span><span>Estimated spend {report.currency} {report.estimated_spend}</span></div>}
        <div className="mt-3 flex flex-wrap items-center gap-2"><input className="gx-input min-w-[220px] flex-1" placeholder="Review note / reason" value={notes[c.id]||""} onChange={e=>setNotes(v=>({...v,[c.id]:e.target.value}))}/>{["pending","paused"].includes(c.status)&&<><button disabled={busy===c.id+"approve"} onClick={()=>void review(c.id,"approve")} className="rounded-lg bg-emerald-400 px-3 py-2 text-[10px] font-black uppercase text-slate-950">{c.status==="paused"?"Resume":"Approve"}</button>{c.status==="pending"&&<button disabled={busy===c.id+"reject"} onClick={()=>void review(c.id,"reject")} className="rounded-lg border border-rose-400/35 px-3 py-2 text-[10px] font-black uppercase text-rose-300">Reject</button>}</>}{c.status==="approved"&&<button disabled={busy===c.id+"pause"} onClick={()=>void review(c.id,"pause")} className="rounded-lg border border-amber-400/35 px-3 py-2 text-[10px] font-black uppercase text-amber-200">Pause</button>}{c.status!=="archived"&&<button disabled={busy===c.id+"archive"} onClick={()=>void review(c.id,"archive")} className="rounded-lg border border-white/15 px-3 py-2 text-[10px] font-black uppercase text-slate-300">Archive</button>}</div>
      </article>;})}</div>}
    </section>
  </div>;
}
