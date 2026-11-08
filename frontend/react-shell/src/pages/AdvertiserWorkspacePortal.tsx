import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  BarChart3,
  Building2,
  CheckCircle2,
  CreditCard,
  Disc3,
  FileText,
  Layers,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Music2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Repeat,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
  VolumeX,
} from "lucide-react";
import { toast } from "sonner";
import { parseError, tokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  AdPlacementSpec,
  AdPricingPackage,
  AdvertiserMediaAsset,
  AdvertiserWorkspace,
  CommercialCampaign,
  CommercialPriceCalculation,
  commercialApi,
  formatNairaMinor,
  resolveCommercialMediaUrl,
} from "@/lib/commercial/api";

const NAV_ITEMS = [
  { to: "/advertiser/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/advertiser/campaigns", label: "Campaigns", icon: Megaphone },
  { to: "/advertiser/campaigns/new", label: "New Brand Ad (4-Step)", icon: Plus },
  { to: "/advertiser/music", label: "Music Promotion", icon: Disc3 },
  { to: "/advertiser/brands", label: "Brands & Agency Team", icon: Users },
  { to: "/advertiser/billing", label: "NGN Billing & Invoices", icon: CreditCard },
  { to: "/advertiser/subscriptions", label: "Subscriptions", icon: Repeat },
  { to: "/advertiser/reports", label: "Analytics Reports", icon: BarChart3 },
  { to: "/advertiser/settings", label: "Workspace Settings", icon: Settings },
];

export default function AdvertiserWorkspacePortal({
  section: _section,
}: {
  section?: string;
} = {}) {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();
  const { logout } = useAuth();

  const [workspace, setWorkspace] = useState<AdvertiserWorkspace | null>(null);
  const [summary, setSummary] = useState<Record<string, any>>({});
  const [members, setMembers] = useState<any[]>([]);
  const [clientBrands, setClientBrands] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<CommercialCampaign[]>([]);
  const [placements, setPlacements] = useState<AdPlacementSpec[]>([]);
  const [packages, setPackages] = useState<AdPricingPackage[]>([]);
  const [billing, setBilling] = useState<{ payments: any[]; invoices: any[]; subscriptions: any[] }>({
    payments: [],
    invoices: [],
    subscriptions: [],
  });
  const [reportsData, setReportsData] = useState<any>(null);
  const [campaignDetail, setCampaignDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // 4-Step Brand Wizard State
  const [brandStep, setBrandStep] = useState<1 | 2 | 3 | 4>(1);
  const [brandCompanyName, setBrandCompanyName] = useState("");
  const [brandContactEmail, setBrandContactEmail] = useState("");
  const [brandContactPhone, setBrandContactPhone] = useState("");
  const [brandContactName, setBrandContactName] = useState("");
  const [brandWebsiteUrl, setBrandWebsiteUrl] = useState("");
  const [brandClientBrandId, setBrandClientBrandId] = useState("");
  const [brandLogoAsset, setBrandLogoAsset] = useState<AdvertiserMediaAsset | null>(null);
  const [brandSelectedPlacements, setBrandSelectedPlacements] = useState<string[]>(["public_homepage"]);
  const [brandCreativeAsset, setBrandCreativeAsset] = useState<AdvertiserMediaAsset | null>(null);
  const [brandHeadline, setBrandHeadline] = useState("");
  const [brandDescription, setBrandDescription] = useState("");
  const [brandDurationDays, setBrandDurationDays] = useState<number>(7);
  const [brandPackageCode, setBrandPackageCode] = useState<string>("brand_7d");
  const [brandIsSubscription, setBrandIsSubscription] = useState<boolean>(false);
  const [brandSubConsent, setBrandSubConsent] = useState<boolean>(false);
  const [brandPaymentProvider, setBrandPaymentProvider] = useState<"paystack" | "korapay">("paystack");
  const [brandPriceQuote, setBrandPriceQuote] = useState<CommercialPriceCalculation | null>(null);
  const [uploadingAsset, setUploadingAsset] = useState(false);
  const [submittingWizard, setSubmittingWizard] = useState(false);

  // Music Promotion State
  const [musicAudioAsset, setMusicAudioAsset] = useState<AdvertiserMediaAsset | null>(null);
  const [musicArtworkAsset, setMusicArtworkAsset] = useState<AdvertiserMediaAsset | null>(null);
  const [musicTrackTitle, setMusicTrackTitle] = useState("");
  const [musicStageName, setMusicStageName] = useState("");
  const [musicLabelName, setMusicLabelName] = useState("");
  const [musicGenre, setMusicGenre] = useState("Afrobeats");
  const [musicExternalUrl, setMusicExternalUrl] = useState("");
  const [musicDurationDays, setMusicDurationDays] = useState<number>(7);
  const [musicIsSubscription, setMusicIsSubscription] = useState<boolean>(false);
  const [musicSubConsent, setMusicSubConsent] = useState<boolean>(false);
  const [musicExplicit, setMusicExplicit] = useState<boolean>(false);
  const [musicRightsAccepted, setMusicRightsAccepted] = useState<boolean>(false);
  const [musicRightsHolder, setMusicRightsHolder] = useState("");
  const [musicPaymentProvider, setMusicPaymentProvider] = useState<"paystack" | "korapay">("paystack");
  const [musicPriceQuote, setMusicPriceQuote] = useState<CommercialPriceCalculation | null>(null);

  // Agency / Team Form State
  const [newBrandName, setNewBrandName] = useState("");
  const [newBrandWebsite, setNewBrandWebsite] = useState("");
  const [newBrandIndustry, setNewBrandIndustry] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("campaign_manager");

  const loadWorkspaceData = useCallback(async () => {
    if (!tokens.get()) {
      navigate("/advertiser/login");
      return;
    }
    setLoading(true);
    try {
      const [wsOverview, campList, plList, pkgList, billData] = await Promise.all([
        commercialApi.getWorkspaceOverview(),
        commercialApi.listCampaigns(),
        commercialApi.listPublicPlacements(),
        commercialApi.listPublicPackages(),
        commercialApi.getBillingLedger(),
      ]);
      const ws: AdvertiserWorkspace = wsOverview.workspace;
      setWorkspace(ws);
      setSummary(wsOverview.summary || {});
      setMembers(wsOverview.members || []);
      setClientBrands(wsOverview.client_brands || []);
      setCampaigns(campList);
      setPlacements(plList);
      setPackages(pkgList);
      setBilling(billData);

      setBrandCompanyName((prev) => prev || ws.company_name || "");
      setBrandContactEmail((prev) => prev || ws.contact_email || "");
      setBrandContactPhone((prev) => prev || ws.contact_phone || "");
      setBrandContactName((prev) => prev || ws.contact_name || "");
      setBrandWebsiteUrl((prev) => prev || ws.website_url || "");
      setMusicStageName((prev) => prev || ws.stage_name || ws.company_name || "");
      setMusicLabelName((prev) => prev || ws.label_name || ws.company_name || "");
      setMusicRightsHolder((prev) => prev || ws.label_name || ws.company_name || "");
    } catch (err) {
      toast.error(parseError(err));
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    void loadWorkspaceData();
  }, [loadWorkspaceData]);

  // Verify reference if returned from payment checkout
  useEffect(() => {
    const verifyRef = searchParams.get("verify_reference");
    if (verifyRef) {
      commercialApi
        .verifyPayment(verifyRef)
        .then(() => {
          toast.success(`Payment ${verifyRef} verified in NGN!`);
          void loadWorkspaceData();
        })
        .catch((err) => toast.error(parseError(err)));
    }
  }, [searchParams, loadWorkspaceData]);

  // Load campaign detail when on /advertiser/campaigns/:id
  useEffect(() => {
    if (params.id && params.id !== "new") {
      commercialApi
        .getCampaignDetail(params.id)
        .then((res) => setCampaignDetail(res))
        .catch((err) => toast.error(parseError(err)));
    } else {
      setCampaignDetail(null);
    }
  }, [params.id]);

  // Load full reports when on /advertiser/reports
  useEffect(() => {
    if (location.pathname === "/advertiser/reports") {
      commercialApi
        .getReports()
        .then((res) => setReportsData(res))
        .catch((err) => toast.error(parseError(err)));
    }
  }, [location.pathname]);

  // Live NGN Price Quote for Brand Wizard
  useEffect(() => {
    if (brandSelectedPlacements.length === 0 || brandDurationDays < 7) return;
    commercialApi
      .calculatePrice({
        division: "brand",
        placements: brandSelectedPlacements,
        duration_days: brandDurationDays,
        package_code: brandPackageCode || null,
        is_subscription: brandIsSubscription,
      })
      .then((res) => setBrandPriceQuote(res))
      .catch(() => setBrandPriceQuote(null));
  }, [brandSelectedPlacements, brandDurationDays, brandPackageCode, brandIsSubscription]);

  // Live NGN Price Quote for Music Promotion
  useEffect(() => {
    const pkgCode = musicIsSubscription ? "music_monthly_sub" : `music_${musicDurationDays}d`;
    commercialApi
      .calculatePrice({
        division: "music",
        placements: ["music_rotation"],
        duration_days: musicIsSubscription ? 30 : musicDurationDays,
        package_code: pkgCode,
        is_subscription: musicIsSubscription,
      })
      .then((res) => setMusicPriceQuote(res))
      .catch(() => setMusicPriceQuote(null));
  }, [musicDurationDays, musicIsSubscription]);

  const brandPlacements = useMemo(
    () => placements.filter((p) => p.division === "brand" && p.is_enabled && p.delivery_surface_ready),
    [placements],
  );

  const handleUploadFile = async (
    file: File | undefined,
    kind: "logo" | "brand_image" | "brand_video" | "music_audio" | "music_artwork",
    onUploaded: (asset: AdvertiserMediaAsset) => void,
  ) => {
    if (!file) return;
    setUploadingAsset(true);
    try {
      const uploaded = await commercialApi.uploadMediaAsset(file, kind);
      onUploaded(uploaded);
      toast.success(`Uploaded ${uploaded.original_filename} (${uploaded.mime_type})`);
    } catch (err) {
      toast.error(parseError(err));
    } finally {
      setUploadingAsset(false);
    }
  };

  const handleCreateBrandCampaign = async (initiateCheckout: boolean) => {
    if (!brandCreativeAsset) {
      toast.error("Please upload a silent image or video creative in Step 3.");
      return;
    }
    if (brandDurationDays < 7) {
      toast.error("The minimum brand advertising campaign duration is 7 days.");
      return;
    }
    setSubmittingWizard(true);
    try {
      const created = await commercialApi.createBrandCampaign({
        company_name: brandCompanyName.trim(),
        contact_email: brandContactEmail.trim(),
        contact_phone: brandContactPhone.trim(),
        contact_name: brandContactName.trim() || null,
        website_url: brandWebsiteUrl.trim() || null,
        logo_asset_id: brandLogoAsset?.id || workspace?.logo_asset_id || null,
        client_brand_id: brandClientBrandId || null,
        placements: brandSelectedPlacements,
        creative_asset_id: brandCreativeAsset.id,
        headline: brandHeadline.trim() || `${brandCompanyName.trim()} on GTEX`,
        description: brandDescription.trim(),
        duration_days: brandDurationDays,
        package_code: brandPackageCode || null,
        is_subscription: brandIsSubscription,
        submit_immediately: true,
      });
      toast.success("Brand campaign created. System will calculate start & end dates upon approval + NGN payment.");

      if (initiateCheckout && created.price_minor_ngn > 0) {
        const pay = await commercialApi.initiatePayment({
          campaign_id: created.id,
          provider: brandPaymentProvider,
          subscription_consent_accepted: brandSubConsent,
        });
        toast.success(`NGN Payment initiated (${pay.reference}).`);
      }
      await loadWorkspaceData();
      navigate(`/advertiser/campaigns/${created.id}`);
    } catch (err) {
      toast.error(parseError(err));
    } finally {
      setSubmittingWizard(false);
    }
  };

  const handleCreateMusicPromotion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!musicAudioAsset) {
      toast.error("Please upload your audio track directly first.");
      return;
    }
    if (!musicRightsAccepted) {
      toast.error("Please accept the music rights and copyright declaration.");
      return;
    }
    setSubmittingWizard(true);
    try {
      const pkgCode = musicIsSubscription ? "music_monthly_sub" : `music_${musicDurationDays}d`;
      const created = await commercialApi.createMusicPromotion({
        audio_asset_id: musicAudioAsset.id,
        track_title: musicTrackTitle.trim() || null,
        stage_name: musicStageName.trim() || null,
        label_name: musicLabelName.trim() || null,
        genre: musicGenre.trim() || "Afrobeats",
        artwork_asset_id: musicArtworkAsset?.id || null,
        external_profile_url: musicExternalUrl.trim() || null,
        duration_days: musicIsSubscription ? 30 : musicDurationDays,
        package_code: pkgCode,
        is_subscription: musicIsSubscription,
        explicit_content: musicExplicit,
        rights_declaration_accepted: musicRightsAccepted,
        rights_holder: musicRightsHolder.trim() || musicStageName.trim() || workspace?.company_name || null,
      });
      toast.success("Music promotion submitted for rights verification & NGN billing.");

      if (created.price_minor_ngn > 0) {
        await commercialApi.initiatePayment({
          campaign_id: created.id,
          provider: musicPaymentProvider,
          subscription_consent_accepted: musicSubConsent,
        });
      }
      await loadWorkspaceData();
      navigate(`/advertiser/campaigns/${created.id}`);
    } catch (err) {
      toast.error(parseError(err));
    } finally {
      setSubmittingWizard(false);
    }
  };

  const currentPath = location.pathname;

  return (
    <div
      className="min-h-screen bg-[#050811] text-slate-100 flex flex-col lg:flex-row"
      data-testid="advertiser-workspace-shell"
    >
      {/* Dedicated Advertiser Sidebar */}
      <aside className="w-full lg:w-72 shrink-0 border-b lg:border-b-0 lg:border-r border-white/10 bg-[#080d1a] p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <Link to="/advertise" className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500 font-black text-slate-950">
                GTEX
              </div>
              <div>
                <div className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                  COMMERCIAL NETWORK
                </div>
                <div className="text-sm font-bold text-white truncate max-w-[160px]">
                  {workspace?.company_name || "Advertiser Workspace"}
                </div>
              </div>
            </Link>
          </div>

          {workspace && (
            <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/70 p-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="uppercase tracking-wider text-slate-400 font-semibold">
                  {workspace.account_type} Account
                </span>
                <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                  {workspace.status}
                </span>
              </div>
              <div className="mt-1 text-slate-300 truncate">{workspace.contact_email}</div>
              <div className="mt-1 font-mono text-[11px] text-amber-300">Billing Currency: NGN (₦)</div>
            </div>
          )}

          <nav className="mt-6 space-y-1">
            {NAV_ITEMS.map((item) => {
              const active = currentPath === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition ${
                    active
                      ? "bg-emerald-500 text-slate-950 font-bold"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-8 border-t border-white/10 pt-4 space-y-2">
          <Link
            to="/advertise"
            className="block rounded-xl border border-white/10 bg-white/5 px-3.5 py-2 text-center text-xs font-semibold text-slate-300 hover:bg-white/10"
          >
            Public Commercial Site
          </Link>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate("/advertiser/login");
            }}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-xs font-semibold text-rose-200 hover:bg-rose-500/20"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign Out of Advertiser Portal
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-5 sm:p-8 lg:p-10 overflow-y-auto">
        {/* 1. DASHBOARD VIEW */}
        {currentPath === "/advertiser/dashboard" && (
          <div className="space-y-8" data-testid="advertiser-dashboard-view">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                  GTEX Commercial Workspace
                </div>
                <h1 className="mt-1 text-3xl font-bold text-white">
                  {workspace?.company_name || "Advertiser Dashboard"}
                </h1>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Link
                  to="/advertiser/campaigns/new"
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-bold text-slate-950 hover:bg-emerald-400"
                >
                  <Plus className="h-4 w-4" />
                  New Brand Campaign (4-Step)
                </Link>
                <Link
                  to="/advertiser/music"
                  className="inline-flex items-center gap-2 rounded-xl border border-amber-400/40 bg-amber-500/15 px-4 py-2.5 text-xs font-bold text-amber-200 hover:bg-amber-500/25"
                >
                  <Music2 className="h-4 w-4" />
                  Promote Music Track
                </Link>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
                <div className="text-xs text-slate-400">Active Campaigns</div>
                <div className="mt-2 text-2xl font-black text-white">
                  {summary.active_campaigns ?? 0} / {summary.total_campaigns ?? 0}
                </div>
                <div className="mt-1 text-[11px] text-emerald-400">
                  {summary.brand_campaigns ?? 0} Brand • {summary.music_campaigns ?? 0} Music
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
                <div className="text-xs text-slate-400">Verified NGN Spend</div>
                <div className="mt-2 text-2xl font-black text-emerald-300">
                  {summary.total_paid_formatted_ngn || "₦0.00"}
                </div>
                <div className="mt-1 text-[11px] text-slate-400">Exclusively in Nigerian Naira (₦)</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
                <div className="text-xs text-slate-400">Verified Impressions &amp; Clicks</div>
                <div className="mt-2 text-2xl font-black text-white">
                  {(summary.impressions ?? 0).toLocaleString()} / {(summary.clicks ?? 0).toLocaleString()}
                </div>
                <div className="mt-1 text-[11px] text-slate-400">Genuine recorded delivery events</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
                <div className="text-xs text-slate-400">Promoted Music Plays Started</div>
                <div className="mt-2 text-2xl font-black text-amber-300">
                  {(summary.plays_started ?? 0).toLocaleString()}
                </div>
                <div className="mt-1 text-[11px] text-slate-400">Global GTEX Music Player rotation</div>
              </div>
            </div>

            {/* Recent Campaigns Table */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-white">Recent Commercial Campaigns</h2>
                <Link to="/advertiser/campaigns" className="text-xs font-semibold text-emerald-400 hover:underline">
                  View All Campaigns
                </Link>
              </div>
              {campaigns.length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm text-slate-400">
                  No campaigns created yet. Launch a 4-Step Brand Campaign or a Music Promotion to reach the GTEX audience.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-white/10 text-slate-400 uppercase">
                      <tr>
                        <th className="py-2.5 pr-4">Campaign</th>
                        <th className="py-2.5 pr-4">Division</th>
                        <th className="py-2.5 pr-4">Placements</th>
                        <th className="py-2.5 pr-4">Duration</th>
                        <th className="py-2.5 pr-4">Price (NGN)</th>
                        <th className="py-2.5 pr-4">Payment</th>
                        <th className="py-2.5 pr-4">Status</th>
                        <th className="py-2.5 text-right">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {campaigns.slice(0, 8).map((c) => (
                        <tr key={c.id} className="hover:bg-white/5">
                          <td className="py-3 pr-4 font-semibold text-white">
                            <div>{c.headline}</div>
                            <div className="text-[11px] text-slate-400">{c.brand_name}</div>
                          </td>
                          <td className="py-3 pr-4 uppercase font-bold text-slate-300">{c.campaign_type}</td>
                          <td className="py-3 pr-4 text-slate-300">{(c.placements || [c.placement]).join(", ")}</td>
                          <td className="py-3 pr-4 text-slate-300">{c.duration_days} days</td>
                          <td className="py-3 pr-4 font-mono font-bold text-emerald-300">
                            {c.currency === "NGN" ? c.price_formatted_ngn : `${c.currency} ${c.price_minor_ngn}`}
                          </td>
                          <td className="py-3 pr-4">
                            <span
                              className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${
                                c.payment_status === "paid"
                                  ? "bg-emerald-500/20 text-emerald-300"
                                  : "bg-amber-500/20 text-amber-300"
                              }`}
                            >
                              {c.payment_status}
                            </span>
                          </td>
                          <td className="py-3 pr-4">
                            <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-white">
                              {c.status}
                            </span>
                          </td>
                          <td className="py-3 text-right">
                            <Link
                              to={`/advertiser/campaigns/${c.id}`}
                              className="text-emerald-400 font-semibold hover:underline"
                            >
                              Report &rarr;
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 2. 4-STEP BRAND CAMPAIGN WIZARD (/advertiser/campaigns/new) */}
        {currentPath === "/advertiser/campaigns/new" && (
          <div className="max-w-4xl space-y-6" data-testid="brand-campaign-wizard">
            <div>
              <div className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                GTEX Brand Advertising • 4-Step Workflow
              </div>
              <h1 className="mt-1 text-2xl sm:text-3xl font-bold text-white">
                Create Brand Advertising Campaign
              </h1>
              <p className="mt-1 text-xs text-slate-400">
                Direct creative uploads, silent visual delivery, minimum 7-day duration, and system-calculated start/end dates upon approval and NGN payment.
              </p>
            </div>

            {/* Step Indicator */}
            <div className="grid grid-cols-4 gap-2">
              {[
                { step: 1, title: "1. Business Details" },
                { step: 2, title: "2. Placements" },
                { step: 3, title: "3. Upload Creative" },
                { step: 4, title: "4. Duration & NGN Pay" },
              ].map((s) => (
                <button
                  key={s.step}
                  type="button"
                  onClick={() => setBrandStep(s.step as any)}
                  data-testid={`wizard-step-btn-${s.step}`}
                  className={`rounded-xl border px-3 py-2.5 text-left text-xs font-bold transition ${
                    brandStep === s.step
                      ? "border-emerald-400 bg-emerald-500/15 text-emerald-300"
                      : "border-white/10 bg-slate-900/60 text-slate-400"
                  }`}
                >
                  {s.title}
                </button>
              ))}
            </div>

            {/* STEP 1: BUSINESS DETAILS */}
            {brandStep === 1 && (
              <div
                className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 space-y-4"
                data-testid="brand-wizard-step-1"
              >
                <h2 className="text-lg font-bold text-white">Step 1: Business &amp; Brand Details</h2>
                <p className="text-xs text-slate-400">
                  Enter your company or agency contact details and upload your business logo directly. External logo URLs are not required.
                </p>

                {clientBrands.length > 0 && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Agency Client Brand (Optional)
                    </label>
                    <select
                      value={brandClientBrandId}
                      onChange={(e) => {
                        setBrandClientBrandId(e.target.value);
                        const found = clientBrands.find((b) => b.id === e.target.value);
                        if (found) {
                          setBrandCompanyName(found.brand_name);
                          if (found.website_url) setBrandWebsiteUrl(found.website_url);
                        }
                      }}
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                    >
                      <option value="">-- Workspace Default / Direct Brand --</option>
                      {clientBrands.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.brand_name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Company or Agency Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={brandCompanyName}
                      onChange={(e) => setBrandCompanyName(e.target.value)}
                      placeholder="Company or Brand Name"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                      data-testid="step1-company-name"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Contact Email *
                    </label>
                    <input
                      type="email"
                      required
                      value={brandContactEmail}
                      onChange={(e) => setBrandContactEmail(e.target.value)}
                      placeholder="marketing@company.com"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                      data-testid="step1-contact-email"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Contact Telephone *
                    </label>
                    <input
                      type="tel"
                      required
                      value={brandContactPhone}
                      onChange={(e) => setBrandContactPhone(e.target.value)}
                      placeholder="+234 800 000 0000"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                      data-testid="step1-contact-phone"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Contact Person&apos;s Name (Optional)
                    </label>
                    <input
                      type="text"
                      value={brandContactName}
                      onChange={(e) => setBrandContactName(e.target.value)}
                      placeholder="Full name"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Website (Optional)
                  </label>
                  <input
                    type="url"
                    value={brandWebsiteUrl}
                    onChange={(e) => setBrandWebsiteUrl(e.target.value)}
                    placeholder="https://yourcompany.com"
                    className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Direct Business Logo Upload (PNG, JPG, WebP — Optional)
                  </label>
                  <div className="flex items-center gap-4">
                    <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-2.5 text-xs font-bold text-emerald-300 hover:bg-emerald-500/20">
                      <Upload className="h-4 w-4" />
                      {uploadingAsset ? "Uploading..." : "Upload Logo File"}
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        className="hidden"
                        data-testid="step1-logo-upload-input"
                        onChange={(e) =>
                          handleUploadFile(e.target.files?.[0], "logo", (asset) => setBrandLogoAsset(asset))
                        }
                      />
                    </label>
                    {brandLogoAsset && (
                      <div className="flex items-center gap-2 text-xs text-emerald-300">
                        <CheckCircle2 className="h-4 w-4" />
                        <span>{brandLogoAsset.original_filename}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex justify-end pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      if (!brandCompanyName.trim() || !brandContactEmail.trim() || !brandContactPhone.trim()) {
                        toast.error("Please fill in Company Name, Contact Email, and Contact Telephone.");
                        return;
                      }
                      setBrandStep(2);
                    }}
                    className="rounded-xl bg-emerald-500 px-6 py-2.5 text-xs font-bold text-slate-950 hover:bg-emerald-400"
                    data-testid="step1-next-btn"
                  >
                    Continue to Step 2: Select Placements &rarr;
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: ADVERTISING PLACEMENT */}
            {brandStep === 2 && (
              <div
                className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 space-y-4"
                data-testid="brand-wizard-step-2"
              >
                <h2 className="text-lg font-bold text-white">
                  Step 2: Select GTEX Advertising Placements
                </h2>
                <p className="text-xs text-slate-400">
                  Select one or multiple placements from the central GTEX commercial inventory. Only enabled placements with active delivery surfaces are shown.
                </p>

                <div className="grid gap-3 sm:grid-cols-2">
                  {brandPlacements.map((pl) => {
                    const selected = brandSelectedPlacements.includes(pl.placement_key);
                    return (
                      <button
                        key={pl.placement_key}
                        type="button"
                        onClick={() => {
                          setBrandSelectedPlacements((prev) =>
                            prev.includes(pl.placement_key)
                              ? prev.length > 1
                                ? prev.filter((k) => k !== pl.placement_key)
                                : prev
                              : [...prev, pl.placement_key],
                          );
                        }}
                        data-testid={`placement-option-${pl.placement_key}`}
                        className={`flex flex-col justify-between rounded-xl border p-4 text-left transition ${
                          selected
                            ? "border-emerald-400 bg-emerald-500/15"
                            : "border-white/10 bg-slate-950/60 hover:border-white/20"
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                              {pl.category}
                            </span>
                            <span className="text-[11px] font-mono text-slate-400">
                              {pl.aspect_ratio}
                            </span>
                          </div>
                          <div className="mt-1 text-sm font-bold text-white">{pl.name}</div>
                          <p className="mt-1 text-xs text-slate-400">{pl.description}</p>
                        </div>
                        <div className="mt-3 flex items-center justify-between border-t border-white/10 pt-2 text-[11px]">
                          <span className="text-slate-400">
                            {pl.supported_media_types.map((m) => m.split("/")[1]?.toUpperCase()).join(", ")}
                          </span>
                          <span className="font-bold text-emerald-300">
                            {pl.pricing_configured && pl.weekly_rate_minor_ngn !== null
                              ? `${formatNairaMinor(pl.weekly_rate_minor_ngn)} / wk`
                              : "Admin NGN Rate"}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="flex justify-between pt-4">
                  <button
                    type="button"
                    onClick={() => setBrandStep(1)}
                    className="rounded-xl border border-white/15 px-4 py-2 text-xs font-semibold text-slate-300"
                  >
                    &larr; Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setBrandStep(3)}
                    className="rounded-xl bg-emerald-500 px-6 py-2.5 text-xs font-bold text-slate-950 hover:bg-emerald-400"
                    data-testid="step2-next-btn"
                  >
                    Continue to Step 3: Upload Creative &rarr;
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: UPLOAD CREATIVE */}
            {brandStep === 3 && (
              <div
                className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 space-y-4"
                data-testid="brand-wizard-step-3"
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-bold text-white">Step 3: Direct Creative Upload</h2>
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/15 px-3 py-1 text-xs font-bold text-amber-300">
                    <VolumeX className="h-3.5 w-3.5" />
                    All Visual Ads Are Strictly Silent
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Upload your campaign image (PNG, JPG, WebP) or silent video (MP4, WebM) directly. External creative URLs are not used. Videos with audio tracks are rejected automatically.
                </p>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Campaign Headline *
                    </label>
                    <input
                      type="text"
                      required
                      value={brandHeadline}
                      onChange={(e) => setBrandHeadline(e.target.value)}
                      placeholder="Headline displayed with your creative"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                      data-testid="step3-headline-input"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Short Description (Optional)
                    </label>
                    <input
                      type="text"
                      value={brandDescription}
                      onChange={(e) => setBrandDescription(e.target.value)}
                      placeholder="Supporting sponsor message"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                    />
                  </div>
                </div>

                <div className="flex flex-wrap gap-3">
                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-bold text-slate-950 hover:bg-emerald-400">
                    <Upload className="h-4 w-4" />
                    {uploadingAsset ? "Validating & Uploading..." : "Upload Image Creative (PNG/JPG/WebP)"}
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      className="hidden"
                      data-testid="step3-image-upload-input"
                      onChange={(e) =>
                        handleUploadFile(e.target.files?.[0], "brand_image", (asset) =>
                          setBrandCreativeAsset(asset),
                        )
                      }
                    />
                  </label>

                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-emerald-400/40 bg-emerald-500/15 px-4 py-2.5 text-xs font-bold text-emerald-200 hover:bg-emerald-500/25">
                    <Upload className="h-4 w-4" />
                    {uploadingAsset ? "Verifying Silent Video..." : "Upload Silent Video Creative (MP4/WebM)"}
                    <input
                      type="file"
                      accept="video/mp4,video/webm"
                      className="hidden"
                      data-testid="step3-video-upload-input"
                      onChange={(e) =>
                        handleUploadFile(e.target.files?.[0], "brand_video", (asset) =>
                          setBrandCreativeAsset(asset),
                        )
                      }
                    />
                  </label>
                </div>

                {brandCreativeAsset && (
                  <div
                    className="mt-4 rounded-2xl border border-emerald-500/30 bg-slate-950 p-4 space-y-3"
                    data-testid="step3-creative-preview"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-emerald-300">
                        Verified Creative Preview: {brandCreativeAsset.original_filename}
                      </span>
                      <span className="font-mono text-slate-400">
                        {brandCreativeAsset.mime_type} • Silent Verified:{" "}
                        {brandCreativeAsset.is_silent_verified ? "YES" : "NO"}
                      </span>
                    </div>
                    {brandCreativeAsset.mime_type.startsWith("video/") ? (
                      <video
                        src={resolveCommercialMediaUrl(brandCreativeAsset.delivery_url) || undefined}
                        muted
                        autoPlay
                        loop
                        playsInline
                        className="max-h-64 w-full rounded-xl object-contain bg-black"
                      />
                    ) : (
                      <img
                        src={resolveCommercialMediaUrl(brandCreativeAsset.delivery_url) || undefined}
                        alt={brandHeadline || "Brand Creative"}
                        className="max-h-64 w-full rounded-xl object-contain bg-black"
                      />
                    )}
                  </div>
                )}

                <div className="flex justify-between pt-4">
                  <button
                    type="button"
                    onClick={() => setBrandStep(2)}
                    className="rounded-xl border border-white/15 px-4 py-2 text-xs font-semibold text-slate-300"
                  >
                    &larr; Back
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!brandCreativeAsset) {
                        toast.error("Please upload a creative image or silent video before continuing.");
                        return;
                      }
                      setBrandStep(4);
                    }}
                    className="rounded-xl bg-emerald-500 px-6 py-2.5 text-xs font-bold text-slate-950 hover:bg-emerald-400"
                    data-testid="step3-next-btn"
                  >
                    Continue to Step 4: Duration &amp; NGN Payment &rarr;
                  </button>
                </div>
              </div>
            )}

            {/* STEP 4: CAMPAIGN DURATION & NGN PAYMENT */}
            {brandStep === 4 && (
              <div
                className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 space-y-5"
                data-testid="brand-wizard-step-4"
              >
                <h2 className="text-lg font-bold text-white">
                  Step 4: Campaign Duration &amp; Nigerian Naira (NGN) Payment
                </h2>

                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-200">
                  <strong>Automatic System Scheduling:</strong> You do not need to enter manual start or end dates.
                  Your campaign&apos;s {brandDurationDays}-day delivery window is calculated automatically by the
                  system the moment creative moderation is approved and NGN payment is verified.
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                    Select Campaign Duration (Minimum 7 Days)
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { days: 7, code: "brand_7d", label: "7 Days (1 Week)", sub: false },
                      { days: 14, code: "brand_14d", label: "14 Days (2 Weeks)", sub: false },
                      { days: 30, code: "brand_30d", label: "30 Days (1 Month)", sub: false },
                      { days: 30, code: "brand_monthly_sub", label: "Monthly Subscription", sub: true },
                    ].map((opt) => {
                      const active =
                        brandDurationDays === opt.days && brandIsSubscription === opt.sub;
                      return (
                        <button
                          key={opt.code}
                          type="button"
                          onClick={() => {
                            setBrandDurationDays(opt.days);
                            setBrandPackageCode(opt.code);
                            setBrandIsSubscription(opt.sub);
                          }}
                          className={`rounded-xl border p-3 text-left transition ${
                            active
                              ? "border-emerald-400 bg-emerald-500/15 text-white"
                              : "border-white/10 bg-slate-950/60 text-slate-300"
                          }`}
                        >
                          <div className="text-xs font-bold">{opt.label}</div>
                          <div className="mt-1 text-[11px] text-emerald-300">
                            {opt.sub ? "Auto-renews every 30d" : "One-time NGN campaign"}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Price Breakdown in NGN */}
                <div className="rounded-2xl border border-white/10 bg-slate-950 p-4 space-y-2 text-xs">
                  <div className="flex items-center justify-between font-bold text-slate-300">
                    <span>Selected Placements ({brandSelectedPlacements.length})</span>
                    <span>{brandSelectedPlacements.join(", ")}</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Campaign Duration</span>
                    <span>{brandDurationDays} Days (System-Calculated Window)</span>
                  </div>
                  <div className="border-t border-white/10 pt-2 flex items-center justify-between text-sm font-black">
                    <span className="text-white">Total Price (NGN)</span>
                    <span className="text-emerald-400" data-testid="step4-ngn-total">
                      {brandPriceQuote?.pricing_configured && brandPriceQuote.total_minor_ngn !== null
                        ? formatNairaMinor(brandPriceQuote.total_minor_ngn)
                        : "Pricing pending admin configuration (NGN)"}
                    </span>
                  </div>
                </div>

                {brandIsSubscription && (
                  <label className="flex items-start gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
                    <input
                      type="checkbox"
                      checked={brandSubConsent}
                      onChange={(e) => setBrandSubConsent(e.target.checked)}
                      className="mt-0.5"
                    />
                    <span>
                      I explicitly authorise GTEX Commercial Network to charge my payment method in Nigerian Naira (NGN)
                      every 30 days until I cancel or pause my subscription from the Advertiser Portal.
                    </span>
                  </label>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Nigerian Payment Provider
                  </label>
                  <div className="flex gap-3">
                    {(["paystack", "korapay"] as const).map((prov) => (
                      <button
                        key={prov}
                        type="button"
                        onClick={() => setBrandPaymentProvider(prov)}
                        className={`rounded-xl border px-4 py-2 text-xs font-bold uppercase ${
                          brandPaymentProvider === prov
                            ? "border-emerald-400 bg-emerald-500/15 text-emerald-300"
                            : "border-white/10 bg-slate-950 text-slate-400"
                        }`}
                      >
                        {prov} (NGN ₦)
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setBrandStep(3)}
                    className="rounded-xl border border-white/15 px-4 py-2 text-xs font-semibold text-slate-300"
                  >
                    &larr; Back
                  </button>
                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      disabled={submittingWizard}
                      onClick={() => handleCreateBrandCampaign(false)}
                      className="rounded-xl border border-white/15 bg-white/5 px-5 py-2.5 text-xs font-bold text-white hover:bg-white/10"
                      data-testid="step4-submit-campaign-btn"
                    >
                      Submit Campaign for Review
                    </button>
                    {brandPriceQuote?.pricing_configured && (
                      <button
                        type="button"
                        disabled={submittingWizard}
                        onClick={() => handleCreateBrandCampaign(true)}
                        className="rounded-xl bg-emerald-500 px-6 py-2.5 text-xs font-bold text-slate-950 hover:bg-emerald-400"
                        data-testid="step4-pay-ngn-btn"
                      >
                        Submit &amp; Pay {brandPriceQuote.formatted_total_ngn}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 3. MUSIC PROMOTION WORKFLOW (/advertiser/music) */}
        {currentPath === "/advertiser/music" && (
          <div className="max-w-4xl space-y-6" data-testid="music-promotion-workflow">
            <div>
              <div className="text-xs font-bold uppercase tracking-widest text-amber-400">
                GTEX Music Promotion • Global Background Player Rotation
              </div>
              <h1 className="mt-1 text-2xl sm:text-3xl font-bold text-white">
                Promote Your Music Across GTEX
              </h1>
              <p className="mt-1 text-xs text-slate-400">
                Upload your master audio track directly, choose a 7, 21, 30, or 42-day NGN rotation package, and your song will rotate fairly in the global GTEX Music Player across Homepage, App, Club HQ, Halftime, and Post-Match.
              </p>
            </div>

            <form
              onSubmit={handleCreateMusicPromotion}
              className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 space-y-6"
            >
              {/* Step 1: Audio & Cover Art Upload */}
              <div className="space-y-4">
                <h2 className="text-lg font-bold text-white">
                  Step 1: Direct Audio Upload &amp; Track Identity
                </h2>
                <div className="flex flex-wrap gap-3">
                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-xs font-bold text-slate-950 hover:bg-amber-300">
                    <Upload className="h-4 w-4" />
                    {uploadingAsset ? "Uploading Audio..." : "Upload Audio Track (MP3, WAV, OGG, M4A, AAC) *"}
                    <input
                      type="file"
                      accept="audio/mpeg,audio/wav,audio/ogg,audio/mp4,audio/aac,.mp3,.wav,.ogg,.m4a,.aac"
                      className="hidden"
                      data-testid="music-audio-upload-input"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        handleUploadFile(file, "music_audio", (asset) => {
                          setMusicAudioAsset(asset);
                          if (!musicTrackTitle.trim()) {
                            const stem = asset.original_filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ");
                            setMusicTrackTitle(stem);
                          }
                        });
                      }}
                    />
                  </label>

                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-xs font-semibold text-white hover:bg-white/10">
                    <Upload className="h-4 w-4" />
                    Upload Cover Artwork (Optional PNG/JPG/WebP)
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      className="hidden"
                      data-testid="music-artwork-upload-input"
                      onChange={(e) =>
                        handleUploadFile(e.target.files?.[0], "music_artwork", (asset) =>
                          setMusicArtworkAsset(asset),
                        )
                      }
                    />
                  </label>
                </div>

                {musicAudioAsset && (
                  <div
                    className="rounded-xl border border-amber-500/30 bg-slate-950 p-4 space-y-2"
                    data-testid="music-audio-preview"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-amber-300">
                        Uploaded Audio: {musicAudioAsset.original_filename}
                      </span>
                      <span className="font-mono text-slate-400">{musicAudioAsset.mime_type}</span>
                    </div>
                    <audio
                      controls
                      src={resolveCommercialMediaUrl(musicAudioAsset.delivery_url) || undefined}
                      className="w-full h-9"
                    />
                  </div>
                )}

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Track Title (Auto-filled from filename if omitted)
                    </label>
                    <input
                      type="text"
                      value={musicTrackTitle}
                      onChange={(e) => setMusicTrackTitle(e.target.value)}
                      placeholder="Auto-filled from uploaded audio filename"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                      data-testid="music-track-title-input"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Artist / Stage Name (Optional — defaults to account name)
                    </label>
                    <input
                      type="text"
                      value={musicStageName}
                      onChange={(e) => setMusicStageName(e.target.value)}
                      placeholder="Artist or Stage Name"
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Genre (Optional)
                    </label>
                    <input
                      type="text"
                      value={musicGenre}
                      onChange={(e) => setMusicGenre(e.target.value)}
                      placeholder="Afrobeats, Amapiano, Hip-Hop..."
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Artist Profile / Streaming Link (Optional)
                    </label>
                    <input
                      type="url"
                      value={musicExternalUrl}
                      onChange={(e) => setMusicExternalUrl(e.target.value)}
                      placeholder="https://..."
                      className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
                    />
                  </div>
                </div>
              </div>

              {/* Step 2: Select Music Promotional Package (NGN) */}
              <div className="border-t border-white/10 pt-5 space-y-3">
                <h2 className="text-lg font-bold text-white">
                  Step 2: Select Promotional Duration Package (NGN ₦)
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                  {[
                    { days: 7, sub: false, label: "7 Days" },
                    { days: 21, sub: false, label: "21 Days" },
                    { days: 30, sub: false, label: "30 Days" },
                    { days: 42, sub: false, label: "42 Days" },
                    { days: 30, sub: true, label: "Monthly Sub" },
                  ].map((opt) => {
                    const active =
                      musicDurationDays === opt.days && musicIsSubscription === opt.sub;
                    return (
                      <button
                        key={`${opt.days}-${opt.sub}`}
                        type="button"
                        onClick={() => {
                          setMusicDurationDays(opt.days);
                          setMusicIsSubscription(opt.sub);
                        }}
                        data-testid={`music-duration-${opt.days}${opt.sub ? "-sub" : ""}`}
                        className={`rounded-xl border p-3 text-left transition ${
                          active
                            ? "border-amber-400 bg-amber-500/15 text-white"
                            : "border-white/10 bg-slate-950/60 text-slate-300"
                        }`}
                      >
                        <div className="text-xs font-bold">{opt.label}</div>
                        <div className="mt-1 text-[10px] text-amber-300">
                          {opt.sub ? "Recurring 30d" : "Global Rotation"}
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="rounded-xl border border-white/10 bg-slate-950 p-3.5 flex items-center justify-between text-xs">
                  <span className="text-slate-300">
                    Package Total ({musicIsSubscription ? "30-Day Monthly Subscription" : `${musicDurationDays}-Day Rotation`})
                  </span>
                  <span className="text-sm font-black text-amber-300" data-testid="music-ngn-total">
                    {musicPriceQuote?.pricing_configured && musicPriceQuote.total_minor_ngn !== null
                      ? formatNairaMinor(musicPriceQuote.total_minor_ngn)
                      : "Pricing pending admin configuration (NGN)"}
                  </span>
                </div>
              </div>

              {/* Step 3: Rights & Explicit Content Declaration */}
              <div className="border-t border-white/10 pt-5 space-y-3">
                <h2 className="text-lg font-bold text-white">
                  Step 3: Copyright &amp; Content Declaration
                </h2>
                <label className="flex items-center gap-2.5 text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={musicExplicit}
                    onChange={(e) => setMusicExplicit(e.target.checked)}
                  />
                  <span>This track contains explicit lyrics (Explicit badge will be shown).</span>
                </label>

                <label className="flex items-start gap-2.5 rounded-xl border border-white/10 bg-slate-950 p-3.5 text-xs text-slate-200">
                  <input
                    type="checkbox"
                    required
                    checked={musicRightsAccepted}
                    onChange={(e) => setMusicRightsAccepted(e.target.checked)}
                    data-testid="music-rights-checkbox"
                    className="mt-0.5"
                  />
                  <span>
                    <strong>Rights &amp; Licensing Declaration *:</strong> I confirm that I own or control the master
                    and publishing rights required to promote and stream this audio recording across the GTEX Global
                    Music Player, and I grant GTEX a non-exclusive promotional playback license for the duration of
                    the campaign.
                  </span>
                </label>

                {musicIsSubscription && (
                  <label className="flex items-start gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
                    <input
                      type="checkbox"
                      checked={musicSubConsent}
                      onChange={(e) => setMusicSubConsent(e.target.checked)}
                      className="mt-0.5"
                    />
                    <span>
                      I authorise recurring monthly NGN charges every 30 days until cancelled.
                    </span>
                  </label>
                )}

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={submittingWizard}
                    className="rounded-xl bg-amber-400 px-6 py-3 text-xs font-bold text-slate-950 hover:bg-amber-300"
                    data-testid="music-submit-btn"
                  >
                    {submittingWizard ? "Submitting Promotion..." : "Submit Music Promotion & Proceed"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        )}

        {/* 4. CAMPAIGNS LIST (/advertiser/campaigns) */}
        {currentPath === "/advertiser/campaigns" && (
          <div className="space-y-6" data-testid="advertiser-campaigns-list">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold text-white">All Commercial Campaigns</h1>
              <div className="flex gap-2">
                <Link
                  to="/advertiser/campaigns/new"
                  className="rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950"
                >
                  + Brand Campaign
                </Link>
                <Link
                  to="/advertiser/music"
                  className="rounded-xl bg-amber-400 px-4 py-2 text-xs font-bold text-slate-950"
                >
                  + Music Promotion
                </Link>
              </div>
            </div>

            <div className="grid gap-4">
              {campaigns.map((c) => (
                <div
                  key={c.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/10 bg-slate-900/70 p-5"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                        {c.campaign_type}
                      </span>
                      <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-white">
                        {c.status}
                      </span>
                      <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                        Payment: {c.payment_status}
                      </span>
                    </div>
                    <h3 className="mt-2 text-lg font-bold text-white">{c.headline}</h3>
                    <div className="mt-1 text-xs text-slate-400">
                      Brand/Artist: {c.brand_name} • Placements: {(c.placements || [c.placement]).join(", ")} • Duration:{" "}
                      {c.duration_days} Days
                    </div>
                    {c.review_note && (
                      <div className="mt-1 text-xs text-amber-300">Moderation Note: {c.review_note}</div>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {c.payment_status !== "paid" && c.price_minor_ngn > 0 && (
                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            const pay = await commercialApi.initiatePayment({
                              campaign_id: c.id,
                              provider: "paystack",
                              subscription_consent_accepted: true,
                            });
                            await commercialApi.verifyPayment(pay.reference);
                            toast.success("NGN Payment verified!");
                            void loadWorkspaceData();
                          } catch (err) {
                            toast.error(parseError(err));
                          }
                        }}
                        className="rounded-xl bg-emerald-500 px-3.5 py-2 text-xs font-bold text-slate-950"
                      >
                        Pay {c.price_formatted_ngn}
                      </button>
                    )}
                    {c.is_active && (
                      <button
                        type="button"
                        onClick={() =>
                          commercialApi.campaignAction(c.id, "pause").then(() => void loadWorkspaceData())
                        }
                        className="rounded-xl border border-white/15 px-3 py-2 text-xs font-semibold text-slate-200"
                      >
                        Pause
                      </button>
                    )}
                    {c.status === "paused" && (
                      <button
                        type="button"
                        onClick={() =>
                          commercialApi.campaignAction(c.id, "resume").then(() => void loadWorkspaceData())
                        }
                        className="rounded-xl border border-emerald-500/40 px-3 py-2 text-xs font-semibold text-emerald-300"
                      >
                        Resume
                      </button>
                    )}
                    <Link
                      to={`/advertiser/campaigns/${c.id}`}
                      className="rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 text-xs font-bold text-white hover:bg-white/10"
                    >
                      Analytics &amp; Details
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 5. CAMPAIGN DETAIL & GENUINE ANALYTICS (/advertiser/campaigns/:id) */}
        {params.id && params.id !== "new" && campaignDetail && (
          <div className="space-y-6" data-testid="campaign-detail-analytics">
            <div className="flex items-center justify-between">
              <div>
                <Link to="/advertiser/campaigns" className="text-xs text-emerald-400 hover:underline">
                  &larr; All Campaigns
                </Link>
                <h1 className="mt-1 text-2xl font-bold text-white">
                  {campaignDetail.campaign.headline}
                </h1>
                <div className="text-xs text-slate-400">
                  Status: <strong className="text-white uppercase">{campaignDetail.campaign.status}</strong> •
                  Payment: <strong className="text-emerald-300 uppercase">{campaignDetail.campaign.payment_status}</strong> •
                  Price: <strong className="text-emerald-300">{campaignDetail.campaign.price_formatted_ngn}</strong>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {[
                { label: "Impressions", val: campaignDetail.metrics.impressions },
                { label: "Viewable Impr.", val: campaignDetail.metrics.viewable_impressions },
                { label: "Clicks", val: campaignDetail.metrics.clicks },
                { label: "CTR (%)", val: `${campaignDetail.metrics.ctr_percent}%` },
                { label: "Started Plays", val: campaignDetail.metrics.plays_started },
                { label: "Qualified Listens", val: campaignDetail.metrics.qualified_listens },
              ].map((m) => (
                <div key={m.label} className="rounded-2xl border border-white/10 bg-slate-900/70 p-4">
                  <div className="text-[11px] text-slate-400">{m.label}</div>
                  <div className="mt-1 text-xl font-black text-white">{m.val}</div>
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">
                Moderation &amp; Lifecycle Audit Trail
              </h2>
              <div className="space-y-2 text-xs">
                {(campaignDetail.history || []).map((h: any) => (
                  <div key={h.id} className="flex items-center justify-between border-b border-white/5 pb-2">
                    <span className="font-semibold text-white uppercase">{h.action}</span>
                    <span className="text-slate-400">
                      {h.from_status} &rarr; {h.to_status} {h.note ? `(${h.note})` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 6. AGENCY BRANDS & TEAM (/advertiser/brands) */}
        {currentPath === "/advertiser/brands" && (
          <div className="grid gap-8 lg:grid-cols-2" data-testid="advertiser-agency-brands-view">
            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 space-y-4">
              <h2 className="text-lg font-bold text-white">Client Brands (Agency Portfolio)</h2>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    await commercialApi.createClientBrand({
                      brand_name: newBrandName,
                      website_url: newBrandWebsite || undefined,
                      industry: newBrandIndustry || undefined,
                    });
                    setNewBrandName("");
                    setNewBrandWebsite("");
                    setNewBrandIndustry("");
                    toast.success("Client brand added.");
                    void loadWorkspaceData();
                  } catch (err) {
                    toast.error(parseError(err));
                  }
                }}
                className="space-y-3"
              >
                <input
                  type="text"
                  required
                  value={newBrandName}
                  onChange={(e) => setNewBrandName(e.target.value)}
                  placeholder="Client Brand Name *"
                  className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2 text-xs text-white"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="url"
                    value={newBrandWebsite}
                    onChange={(e) => setNewBrandWebsite(e.target.value)}
                    placeholder="https://clientbrand.com"
                    className="rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2 text-xs text-white"
                  />
                  <input
                    type="text"
                    value={newBrandIndustry}
                    onChange={(e) => setNewBrandIndustry(e.target.value)}
                    placeholder="Industry (e.g. Fintech)"
                    className="rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2 text-xs text-white"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950"
                >
                  Add Client Brand
                </button>
              </form>

              <div className="space-y-2 pt-3">
                {clientBrands.map((b) => (
                  <div key={b.id} className="rounded-xl border border-white/10 bg-slate-950 p-3 text-xs">
                    <div className="font-bold text-white">{b.brand_name}</div>
                    <div className="text-slate-400">{b.industry || "Brand Client"} • {b.website_url || "No website"}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 space-y-4">
              <h2 className="text-lg font-bold text-white">Workspace Team Members &amp; Permissions</h2>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    await commercialApi.inviteMember({ email: inviteEmail, role: inviteRole });
                    setInviteEmail("");
                    toast.success("Team member invited.");
                    void loadWorkspaceData();
                  } catch (err) {
                    toast.error(parseError(err));
                  }
                }}
                className="flex gap-2"
              >
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@agency.com"
                  className="flex-1 rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2 text-xs text-white"
                />
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="rounded-xl border border-white/15 bg-slate-950 px-3 py-2 text-xs text-white"
                >
                  <option value="campaign_manager">Campaign Manager</option>
                  <option value="billing">Billing Officer</option>
                  <option value="analyst">Analyst</option>
                  <option value="admin">Workspace Admin</option>
                </select>
                <button
                  type="submit"
                  className="rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950"
                >
                  Invite
                </button>
              </form>

              <div className="space-y-2 pt-3">
                {members.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950 p-3 text-xs"
                  >
                    <div>
                      <div className="font-bold text-white">{m.invited_email}</div>
                      <div className="text-slate-400">Role: {m.role}</div>
                    </div>
                    <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                      {m.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 7. NGN BILLING & INVOICES (/advertiser/billing) */}
        {currentPath === "/advertiser/billing" && (
          <div className="space-y-6" data-testid="advertiser-billing-view">
            <h1 className="text-2xl font-bold text-white">
              Nigerian Naira (NGN ₦) Billing, Payments &amp; Official Invoices
            </h1>
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6">
                <h2 className="text-lg font-bold text-white mb-4">Payment Transactions (NGN)</h2>
                <div className="space-y-3">
                  {billing.payments.map((p) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950 p-3.5 text-xs"
                    >
                      <div>
                        <div className="font-mono font-bold text-white">{p.reference}</div>
                        <div className="text-slate-400">
                          Provider: {p.provider.toUpperCase()} • {p.amount_formatted_ngn}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                          {p.status}
                        </span>
                        {p.status === "pending" && (
                          <button
                            type="button"
                            onClick={() =>
                              commercialApi.verifyPayment(p.reference).then(() => {
                                toast.success("Payment verified!");
                                void loadWorkspaceData();
                              })
                            }
                            className="rounded-lg bg-emerald-500 px-2.5 py-1 text-[11px] font-bold text-slate-950"
                          >
                            Verify Now
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6">
                <h2 className="text-lg font-bold text-white mb-4">Official NGN Invoices &amp; Receipts</h2>
                <div className="space-y-3">
                  {billing.invoices.map((inv) => (
                    <div
                      key={inv.id}
                      className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950 p-3.5 text-xs"
                    >
                      <div>
                        <div className="font-mono font-bold text-white">{inv.invoice_number}</div>
                        <div className="text-slate-400">Total: {inv.total_formatted_ngn}</div>
                      </div>
                      <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                        {inv.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 8. SUBSCRIPTIONS (/advertiser/subscriptions) */}
        {currentPath === "/advertiser/subscriptions" && (
          <div className="space-y-6" data-testid="advertiser-subscriptions-view">
            <h1 className="text-2xl font-bold text-white">Recurring Monthly NGN Subscriptions</h1>
            <div className="space-y-3">
              {billing.subscriptions.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 text-xs text-slate-400">
                  No recurring monthly subscriptions active. You can enable monthly NGN billing when creating a Brand or Music campaign.
                </div>
              ) : (
                billing.subscriptions.map((sub) => (
                  <div
                    key={sub.id}
                    className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-white/10 bg-slate-900/70 p-5 text-xs"
                  >
                    <div>
                      <div className="font-bold text-white">
                        {sub.amount_formatted_ngn} / {sub.billing_interval_days} Days ({sub.provider.toUpperCase()})
                      </div>
                      <div className="text-slate-400 mt-1">{sub.consent_terms_text}</div>
                      {sub.next_billing_at && (
                        <div className="text-emerald-300 mt-1">
                          Next Renewal Date: {new Date(sub.next_billing_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-white/10 px-2.5 py-1 font-bold uppercase text-white">
                        {sub.status}
                      </span>
                      {sub.status === "active" && (
                        <button
                          type="button"
                          onClick={() =>
                            commercialApi.subscriptionAction(sub.id, "cancel").then(() => void loadWorkspaceData())
                          }
                          className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 font-bold text-rose-200"
                        >
                          Cancel Subscription
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* 9. REPORTS (/advertiser/reports) */}
        {currentPath === "/advertiser/reports" && (
          <div className="space-y-6" data-testid="advertiser-reports-view">
            <h1 className="text-2xl font-bold text-white">
              Genuine Event-Based Campaign Performance Reports
            </h1>
            <p className="text-xs text-slate-400">
              All metrics are computed strictly from real, idempotent delivery and playback telemetry events.
            </p>
            <div className="space-y-4">
              {(reportsData?.campaign_reports || []).map((rep: any) => (
                <div
                  key={rep.campaign.id}
                  className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-base font-bold text-white">{rep.campaign.headline}</div>
                      <div className="text-xs text-slate-400">
                        {rep.campaign.brand_name} • {rep.campaign.campaign_type.toUpperCase()} •{" "}
                        {rep.campaign.price_formatted_ngn}
                      </div>
                    </div>
                    <Link
                      to={`/advertiser/campaigns/${rep.campaign.id}`}
                      className="text-xs font-bold text-emerald-400 hover:underline"
                    >
                      Full Timeline &rarr;
                    </Link>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-xs">
                    <div className="rounded-xl bg-slate-950 p-3">
                      <div className="text-slate-400">Impressions</div>
                      <div className="font-bold text-white mt-0.5">{rep.metrics.impressions}</div>
                    </div>
                    <div className="rounded-xl bg-slate-950 p-3">
                      <div className="text-slate-400">Clicks</div>
                      <div className="font-bold text-white mt-0.5">{rep.metrics.clicks}</div>
                    </div>
                    <div className="rounded-xl bg-slate-950 p-3">
                      <div className="text-slate-400">CTR</div>
                      <div className="font-bold text-emerald-300 mt-0.5">{rep.metrics.ctr_percent}%</div>
                    </div>
                    <div className="rounded-xl bg-slate-950 p-3">
                      <div className="text-slate-400">Plays Started</div>
                      <div className="font-bold text-amber-300 mt-0.5">{rep.metrics.plays_started}</div>
                    </div>
                    <div className="rounded-xl bg-slate-950 p-3">
                      <div className="text-slate-400">Qualified Listens</div>
                      <div className="font-bold text-amber-300 mt-0.5">{rep.metrics.qualified_listens}</div>
                    </div>
                    <div className="rounded-xl bg-slate-950 p-3">
                      <div className="text-slate-400">Completed Listens</div>
                      <div className="font-bold text-amber-300 mt-0.5">{rep.metrics.completed_listens}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 10. SETTINGS (/advertiser/settings) */}
        {currentPath === "/advertiser/settings" && workspace && (
          <div className="max-w-xl rounded-2xl border border-white/10 bg-slate-900/70 p-6 space-y-4">
            <h1 className="text-xl font-bold text-white">Workspace Settings</h1>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  await commercialApi.updateWorkspace({
                    company_name: brandCompanyName,
                    contact_name: brandContactName,
                    contact_email: brandContactEmail,
                    contact_phone: brandContactPhone,
                    website_url: brandWebsiteUrl || null,
                    logo_asset_id: brandLogoAsset?.id || workspace.logo_asset_id,
                  });
                  toast.success("Workspace updated.");
                  void loadWorkspaceData();
                } catch (err) {
                  toast.error(parseError(err));
                }
              }}
              className="space-y-3 text-xs"
            >
              <div>
                <label className="block text-slate-300 mb-1">Company / Organisation / Artist Name</label>
                <input
                  type="text"
                  value={brandCompanyName}
                  onChange={(e) => setBrandCompanyName(e.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-300 mb-1">Contact Email</label>
                <input
                  type="email"
                  value={brandContactEmail}
                  onChange={(e) => setBrandContactEmail(e.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-300 mb-1">Contact Telephone</label>
                <input
                  type="tel"
                  value={brandContactPhone}
                  onChange={(e) => setBrandContactPhone(e.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-slate-950 px-3.5 py-2 text-white"
                />
              </div>
              <button
                type="submit"
                className="rounded-xl bg-emerald-500 px-5 py-2.5 font-bold text-slate-950"
              >
                Save Workspace Settings
              </button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
