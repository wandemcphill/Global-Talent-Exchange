/**
 * GTEX Living Football Ecosystem — Stadium LED Advertising Network
 *
 * Connects the physical 3D stadium perimeter LED boards to the existing GTEX
 * advertising and sponsorship infrastructure:
 *  - Public Brand Ad Campaigns (`GET /api/public/ads/campaigns`, `POST /api/public/ads/events`)
 *  - Club & Competition Sponsorship Placements (`POST /api/sponsorship/placements`)
 *  - Match Viewer Monetization Placements (`MatchViewStateView.monetization`)
 *  - Official GTEX House Fallback Creatives
 *
 * Enforces:
 *  - Strict campaign approval, active flag, budget, and start/expiry window validation
 *  - Club-specific, competition-level, platform-wide, and house fallback hierarchy
 *  - High-contrast 2048x256 broadcast LED rendering legible at 1920x1080 from main camera
 *  - Configurable slot-boundary rotation (default 10s) with zero per-frame allocations
 *  - Idempotent impression telemetry only when a campaign slot is visibly displayed
 */

import * as THREE from "three";
import axios from "axios";
import { API } from "@/lib/api";
import { resolveCommercialMediaUrl } from "@/lib/commercial/api";
import type { GtexAdCampaign } from "@/components/advertising/GtexAdvertising";
import type { SpectatorMonetizationView } from "./spectatorContract";

export type StadiumAdCampaignSource =
  | "club_sponsor"
  | "club_contract"
  | "competition"
  | "brand_campaign"
  | "match_monetization"
  | "house_fallback";

export interface StadiumLedCampaign {
  id: string;
  brandName: string;
  headline: string;
  tagline?: string;
  categoryLabel?: string;
  source: StadiumAdCampaignSource;
  priority: number;
  status?: "approved" | "active" | "draft" | "pending" | "paused" | "rejected" | "expired" | "withdrawn";
  isApproved?: boolean;
  isActive?: boolean;
  budgetExhausted?: boolean;
  startAt?: string | number | Date | null;
  endAt?: string | number | Date | null;
  activeFromSecond?: number | null;
  activeUntilSecond?: number | null;
  clubId?: string | null;
  competitionId?: string | null;
  logoUrl?: string | null;
  creativeUrl?: string | null;
  videoUrl?: string | null;
  destinationUrl?: string | null;
  primaryColor?: string;
  accentColor?: string;
  textColor?: string;
  trackPublicBrandImpression?: boolean;
}

export interface SponsorshipPlacementDTO {
  surface: string;
  sponsor_name: string;
  campaign_code: string;
  source: string;
  asset_type?: string | null;
  creative_url?: string | null;
  fallback: boolean;
  metadata?: Record<string, unknown>;
}

export interface StadiumAdMatchContext {
  matchId?: string;
  homeTeamId?: string;
  homeTeamName?: string;
  homePrimaryColor?: string;
  awayTeamId?: string;
  awayTeamName?: string;
  awayPrimaryColor?: string;
  competitionId?: string;
  competitionName?: string;
  regionCode?: string;
}

export interface StadiumAdImpressionEvent {
  campaignId: string;
  brandName: string;
  source: StadiumAdCampaignSource;
  slotIndex: number;
  rotationIndex: number;
  idempotencyKey: string;
  matchId?: string;
  timestampMs: number;
}

export interface StadiumAdvertisingNetworkOptions {
  rotationIntervalSec?: number;
  minVisibleDwellSec?: number;
  enableNetworkFetch?: boolean;
  enableImpressionPost?: boolean;
  onImpressionRecorded?: (event: StadiumAdImpressionEvent) => void;
  onRotationChanged?: (activeCampaigns: StadiumLedCampaign[], rotationIndex: number) => void;
}

const BRAND_PALETTES: Record<string, { primary: string; accent: string; badge: string }> = {
  MTN: { primary: "#FFCC00", accent: "#0B132B", badge: "TELECOM PARTNER" },
  FLUTTERWAVE: { primary: "#F5A623", accent: "#0F172A", badge: "OFFICIAL PAYMENTS" },
  BETKING: { primary: "#0052CC", accent: "#FACC15", badge: "MATCHDAY PARTNER" },
  NIKE: { primary: "#111827", accent: "#F97316", badge: "TECHNICAL SUPPLIER" },
  ADIDAS: { primary: "#0F172A", accent: "#38BDF8", badge: "OFFICIAL BALL PARTNER" },
  "EA SPORTS": { primary: "#1E1B4B", accent: "#FB7185", badge: "GAMING PARTNER" },
  GTEX: { primary: "#042F2E", accent: "#10B981", badge: "OFFICIAL PLATFORM" },
};

export const DEFAULT_HOUSE_FALLBACK_CAMPAIGNS: StadiumLedCampaign[] = [
  {
    id: "gtex-house-exchange",
    brandName: "GTEX GLOBAL TALENT EXCHANGE",
    headline: "VERIFIED AFRICAN & GLOBAL FOOTBALL ECOSYSTEM",
    tagline: "SCOUT • INVEST • COMPETE LIVE",
    categoryLabel: "GTEX HOUSE NETWORK",
    source: "house_fallback",
    priority: 10,
    status: "approved",
    isApproved: true,
    isActive: true,
    primaryColor: "#042F2E",
    accentColor: "#10B981",
    textColor: "#FFFFFF",
  },
  {
    id: "gtex-house-broadcast",
    brandName: "GTEX PREMIER BROADCAST 3D",
    headline: "AUTHORITATIVE LIVE MATCH TELEMETRY & ANALYTICS",
    tagline: "REAL-TIME 22-PLAYER SPATIAL ENGINE",
    categoryLabel: "OFFICIAL BROADCAST",
    source: "house_fallback",
    priority: 9,
    status: "approved",
    isApproved: true,
    isActive: true,
    primaryColor: "#0F172A",
    accentColor: "#F59E0B",
    textColor: "#FFFFFF",
  },
  {
    id: "gtex-house-regen",
    brandName: "GTEX REGEN ACADEMY",
    headline: "DISCOVER THE NEXT GENERATION OF FOOTBALL ICONS",
    tagline: "LAGOS • ABUJA • ACCRA • LONDON",
    categoryLabel: "TALENT PATHWAY",
    source: "house_fallback",
    priority: 8,
    status: "approved",
    isApproved: true,
    isActive: true,
    primaryColor: "#1E1B4B",
    accentColor: "#38BDF8",
    textColor: "#FFFFFF",
  },
];

function parseDateMs(value?: string | number | Date | null): number | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (value instanceof Date) return Number.isFinite(value.getTime()) ? value.getTime() : null;
  const parsed = Date.parse(String(value));
  return Number.isFinite(parsed) ? parsed : null;
}

function resolveBrandPalette(brandName: string, fallbackPrimary?: string, fallbackAccent?: string) {
  const upper = brandName.toUpperCase();
  for (const [key, palette] of Object.entries(BRAND_PALETTES)) {
    if (upper.includes(key)) {
      return palette;
    }
  }
  return {
    primary: fallbackPrimary || "#091526",
    accent: fallbackAccent || "#10B981",
    badge: "OFFICIAL SPONSOR",
  };
}

/**
 * Validates whether a campaign is eligible to be displayed at the given wall-clock
 * time (`nowMs`) and match playback time (`matchTimeSec`), filtering out expired,
 * unapproved, paused, rejected, withdrawn, or club-mismatched campaigns.
 */
export function isCampaignEligible(
  campaign: StadiumLedCampaign,
  nowMs: number = Date.now(),
  matchTimeSec: number = 0,
  context?: StadiumAdMatchContext
): boolean {
  if (!campaign || !campaign.id || !campaign.brandName?.trim()) {
    return false;
  }

  // Status & approval gates
  if (campaign.isApproved === false || campaign.isActive === false || campaign.budgetExhausted === true) {
    return false;
  }
  if (
    campaign.status &&
    !["approved", "active"].includes(String(campaign.status).toLowerCase())
  ) {
    return false;
  }

  // Schedule window gate (start_at / end_at)
  const startMs = parseDateMs(campaign.startAt);
  if (startMs !== null && nowMs < startMs) {
    return false;
  }
  const endMs = parseDateMs(campaign.endAt);
  if (endMs !== null && nowMs >= endMs) {
    return false;
  }

  // Match-second window gate (only if both bounds define a >15s stadium window;
  // short overlay stings still contribute their sponsor brand across the match)
  if (
    typeof campaign.activeFromSecond === "number" &&
    typeof campaign.activeUntilSecond === "number" &&
    campaign.activeUntilSecond - campaign.activeFromSecond >= 15
  ) {
    if (matchTimeSec < campaign.activeFromSecond || matchTimeSec > campaign.activeUntilSecond) {
      return false;
    }
  }

  // Club scope gate
  if (campaign.clubId && context?.homeTeamId && context?.awayTeamId) {
    const targetClub = String(campaign.clubId).toLowerCase();
    const homeId = String(context.homeTeamId).toLowerCase();
    const awayId = String(context.awayTeamId).toLowerCase();
    if (targetClub !== homeId && targetClub !== awayId) {
      return false;
    }
  }

  // Competition scope gate
  if (campaign.competitionId && context?.competitionId) {
    if (String(campaign.competitionId).toLowerCase() !== String(context.competitionId).toLowerCase()) {
      return false;
    }
  }

  return true;
}

const SOURCE_RANK: Record<StadiumAdCampaignSource, number> = {
  club_sponsor: 500,
  club_contract: 450,
  competition: 400,
  brand_campaign: 300,
  match_monetization: 250,
  house_fallback: 10,
};

export class StadiumAdvertisingNetwork {
  private readonly rotationIntervalSec: number;
  private readonly minVisibleDwellSec: number;
  private readonly enableNetworkFetch: boolean;
  private readonly enableImpressionPost: boolean;
  private readonly onImpressionRecorded?: (event: StadiumAdImpressionEvent) => void;
  private readonly onRotationChanged?: (activeCampaigns: StadiumLedCampaign[], rotationIndex: number) => void;

  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private texture: THREE.CanvasTexture;

  private matchContext: StadiumAdMatchContext = {};
  private customCampaigns: StadiumLedCampaign[] = [];
  private brandCampaigns: StadiumLedCampaign[] = [];
  private sponsorshipCampaigns: StadiumLedCampaign[] = [];
  private monetizationCampaigns: StadiumLedCampaign[] = [];

  private loadedImages = new Map<string, HTMLImageElement>();
  private failedImageUrls = new Set<string>();
  private activeVideoEl: HTMLVideoElement | null = null;
  private activeVideoUrl: string | null = null;

  private currentRotationIndex = -1;
  private rotationCount = 0;
  private slotDwellSec = 0;
  private currentPair: [StadiumLedCampaign, StadiumLedCampaign] = [
    DEFAULT_HOUSE_FALLBACK_CAMPAIGNS[0],
    DEFAULT_HOUSE_FALLBACK_CAMPAIGNS[1],
  ];
  private recordedImpressionKeys = new Set<string>();
  private impressionHistory: StadiumAdImpressionEvent[] = [];
  private needsRedraw = true;
  private isDocumentVisible = true;
  private isDisposed = false;
  private lastVideoFrameRedrawMs = 0;

  constructor(options: StadiumAdvertisingNetworkOptions = {}) {
    this.rotationIntervalSec = Math.max(3, options.rotationIntervalSec ?? 10);
    this.minVisibleDwellSec = Math.max(0.25, options.minVisibleDwellSec ?? 0.8);
    this.enableNetworkFetch = options.enableNetworkFetch ?? true;
    this.enableImpressionPost = options.enableImpressionPost ?? true;
    this.onImpressionRecorded = options.onImpressionRecorded;
    this.onRotationChanged = options.onRotationChanged;

    if (typeof document !== "undefined") {
      this.canvas = document.createElement("canvas");
      this.canvas.width = 2048;
      this.canvas.height = 256;
      const isJsdom =
        typeof navigator !== "undefined" &&
        /jsdom/i.test(navigator.userAgent || "") &&
        !(this.canvas.getContext as any)?._isMockFunction;
      if (!isJsdom) {
        try {
          this.ctx = this.canvas.getContext("2d");
        } catch {
          this.ctx = null;
        }
      }
      this.TextureInitFromCanvas();
    } else {
      this.texture = new THREE.CanvasTexture({ width: 2048, height: 256 } as unknown as HTMLCanvasElement);
    }

    this.renderCurrentPairToCanvas();
  }

  private TextureInitFromCanvas(): void {
    this.texture = new THREE.CanvasTexture(
      (this.canvas ?? ({ width: 2048, height: 256 } as unknown as HTMLCanvasElement))
    );
    this.texture.wrapS = THREE.RepeatWrapping;
    this.texture.wrapT = THREE.ClampToEdgeWrapping;
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.anisotropy = 8;
    this.texture.needsUpdate = true;
  }

  public getTexture(): THREE.CanvasTexture {
    return this.texture;
  }

  public getRotationIntervalSec(): number {
    return this.rotationIntervalSec;
  }

  public getRotationCount(): number {
    return this.rotationCount;
  }

  public getCurrentRotationIndex(): number {
    return Math.max(0, this.currentRotationIndex);
  }

  public getActiveCampaigns(): StadiumLedCampaign[] {
    return [...this.currentPair];
  }

  public getImpressionHistory(): StadiumAdImpressionEvent[] {
    return [...this.impressionHistory];
  }

  public setDocumentVisible(visible: boolean): void {
    this.isDocumentVisible = visible;
    if (this.activeVideoEl) {
      if (!visible) {
        this.activeVideoEl.pause();
      } else {
        void this.activeVideoEl.play().catch(() => undefined);
      }
    }
  }

  public setMatchContext(context: StadiumAdMatchContext): void {
    const changed =
      this.matchContext.matchId !== context.matchId ||
      this.matchContext.homeTeamId !== context.homeTeamId ||
      this.matchContext.awayTeamId !== context.awayTeamId ||
      this.matchContext.competitionName !== context.competitionName;

    this.matchContext = { ...this.matchContext, ...context };
    if (changed) {
      this.needsRedraw = true;
      if (this.enableNetworkFetch) {
        void this.fetchBackendSponsorshipPlacements();
      }
    }
  }

  /**
   * Ingests explicit StadiumLedCampaigns (e.g. club sponsors, competition campaigns, test fixtures).
   */
  public setCampaigns(campaigns: StadiumLedCampaign[], nowMs: number = Date.now()): void {
    this.customCampaigns = Array.isArray(campaigns) ? [...campaigns] : [];
    for (const c of this.customCampaigns) {
      this.preloadImage(c.logoUrl);
      this.preloadImage(c.creativeUrl);
    }
    this.currentRotationIndex = -1;
    this.needsRedraw = true;
    this.refreshActiveSlots(0, nowMs, true);
  }

  /**
   * Ingests live GTEX Brand Ad Campaigns from `GtexAdvertising` (`/public/ads/campaigns`).
   */
  public setPublicBrandCampaigns(campaigns: GtexAdCampaign[], nowMs: number = Date.now()): void {
    if (!Array.isArray(campaigns)) return;
    this.brandCampaigns = campaigns.map((c) => {
      const palette = resolveBrandPalette(c.brand_name);
      return {
        id: c.id,
        brandName: c.brand_name,
        headline: c.headline,
        tagline: c.description || "OFFICIAL GTEX ADVERTISING PARTNER",
        categoryLabel: palette.badge,
        source: "brand_campaign" as const,
        priority: Number.isFinite(c.priority) ? c.priority : 100,
        status: "approved" as const,
        isApproved: true,
        isActive: true,
        logoUrl: resolveCommercialMediaUrl(c.logo_url) ?? null,
        creativeUrl: resolveCommercialMediaUrl(c.creative_url) ?? null,
        destinationUrl: c.destination_url,
        primaryColor: palette.primary,
        accentColor: palette.accent,
        textColor: "#FFFFFF",
        trackPublicBrandImpression: true,
      };
    });
    for (const c of this.brandCampaigns) {
      this.preloadImage(c.logoUrl);
      this.preloadImage(c.creativeUrl);
    }
    this.currentRotationIndex = -1;
    this.needsRedraw = true;
    this.refreshActiveSlots(0, nowMs, true);
  }

  /**
   * Ingests backend `/sponsorship/placements` (`SponsorshipPlacementService`) items.
   */
  public setSponsorshipPlacements(placements: SponsorshipPlacementDTO[], nowMs: number = Date.now()): void {
    if (!Array.isArray(placements)) return;
    this.sponsorshipCampaigns = placements
      .filter((p) => p && p.sponsor_name && (!p.surface || p.surface === "stadium_board"))
      .map((p, idx) => {
        const isClub = p.source === "club_sponsor" || p.source === "club_contract";
        const isFallback = Boolean(p.fallback) || p.campaign_code === "gtex_internal";
        const palette = resolveBrandPalette(
          p.sponsor_name,
          isClub ? this.matchContext.homePrimaryColor || "#064E3B" : "#0F172A",
          isClub ? "#34D399" : "#F59E0B"
        );
        const source: StadiumAdCampaignSource = isFallback
          ? "house_fallback"
          : p.source === "club_sponsor"
          ? "club_sponsor"
          : p.source === "club_contract"
          ? "club_contract"
          : "competition";

        const clubName =
          p.metadata?.club_id && p.metadata.club_id === this.matchContext.awayTeamId
            ? this.matchContext.awayTeamName
            : this.matchContext.homeTeamName;

        return {
          id: p.campaign_code || `sponsorship-${idx}`,
          brandName: p.sponsor_name,
          headline: isClub
            ? `OFFICIAL PARTNER OF ${(clubName || "THE CLUB").toUpperCase()}`
            : isFallback
            ? "GLOBAL TALENT EXCHANGE — VERIFIED FOOTBALL BROADCAST"
            : `OFFICIAL ${(this.matchContext.competitionName || "GTEX MATCHDAY").toUpperCase()} PARTNER`,
          tagline: p.asset_type ? String(p.asset_type).replace(/_/g, " ").toUpperCase() : palette.badge,
          categoryLabel: isClub ? "CLUB SPONSOR" : isFallback ? "GTEX HOUSE" : "COMPETITION PARTNER",
          source,
          priority: isClub ? 200 : isFallback ? 5 : 150,
          status: "approved" as const,
          isApproved: true,
          isActive: true,
          clubId: typeof p.metadata?.club_id === "string" ? p.metadata.club_id : null,
          creativeUrl: resolveCommercialMediaUrl(p.creative_url) ?? null,
          primaryColor: palette.primary,
          accentColor: palette.accent,
          textColor: "#FFFFFF",
        };
      });

    for (const c of this.sponsorshipCampaigns) {
      this.preloadImage(c.creativeUrl);
    }
    this.currentRotationIndex = -1;
    this.needsRedraw = true;
    this.refreshActiveSlots(0, nowMs, true);
  }

  /**
   * Ingests `MatchViewStateView.monetization` (`MatchViewerMonetizationView`) placements from `/match-viewer/{id}`.
   */
  public setMatchMonetization(monetization?: SpectatorMonetizationView | null, nowMs: number = Date.now()): void {
    if (!monetization || monetization.premium_ad_free || !monetization.ads_enabled) {
      this.monetizationCampaigns = [];
      this.needsRedraw = true;
      return;
    }

    const seenBrands = new Set<string>();
    const mapped: StadiumLedCampaign[] = [];
    for (const pl of monetization.placements || []) {
      if (!pl || !pl.brand?.trim()) continue;
      const brandKey = pl.brand.trim().toUpperCase();
      if (seenBrands.has(brandKey)) continue;
      seenBrands.add(brandKey);

      const palette = resolveBrandPalette(pl.brand);
      mapped.push({
        id: pl.ad_id || `monetization-${brandKey}`,
        brandName: pl.brand.toUpperCase(),
        headline: pl.message ? pl.message.toUpperCase() : `${pl.brand.toUpperCase()} — OFFICIAL MATCHDAY PARTNER`,
        tagline: pl.cta_label ? pl.cta_label.toUpperCase() : palette.badge,
        categoryLabel: palette.badge,
        source: "match_monetization",
        priority: 120,
        status: "approved",
        isApproved: true,
        isActive: true,
        activeFromSecond: pl.active_from_second ?? null,
        activeUntilSecond: pl.active_until_second ?? null,
        primaryColor: palette.primary,
        accentColor: palette.accent,
        textColor: "#FFFFFF",
      });
    }

    this.monetizationCampaigns = mapped;
    this.currentRotationIndex = -1;
    this.needsRedraw = true;
    this.refreshActiveSlots(0, nowMs, true);
  }

  /**
   * Fetches `/sponsorship/placements` and `/public/ads/campaigns` from the backend if available.
   * Never blocks rendering or throws if the backend is offline or in test mode.
   */
  public async fetchBackendSponsorshipPlacements(): Promise<void> {
    if (!this.enableNetworkFetch || this.isDisposed || typeof window === "undefined") return;
    try {
      const [placementsRes, publicAdsRes] = await Promise.allSettled([
        axios.post(
          `${API}/sponsorship/placements`,
          {
            home_club_id: this.matchContext.homeTeamId || null,
            away_club_id: this.matchContext.awayTeamId || null,
            competition_id: this.matchContext.competitionId || null,
            stage_name: this.matchContext.competitionName || null,
            region_code: this.matchContext.regionCode || "NG",
            surfaces: ["stadium_board"],
          },
          { timeout: 3000 }
        ),
        // Strict stadium inventory: approved + paid + in-window + booked for `stadium_perimeter`.
        axios.get(`${API}/v2/public/ads/stadium/inventory?limit=25`, { timeout: 3000 }),
      ]);

      if (this.isDisposed) return;

      if (
        placementsRes.status === "fulfilled" &&
        Array.isArray(placementsRes.value?.data?.placements)
      ) {
        this.setSponsorshipPlacements(placementsRes.value.data.placements);
      }

      if (
        publicAdsRes.status === "fulfilled" &&
        Array.isArray(publicAdsRes.value?.data?.campaigns)
      ) {
        this.setPublicBrandCampaigns(publicAdsRes.value.data.campaigns);
      }
    } catch {
      // Graceful fallback to existing campaigns / house creatives
    }
  }

  /**
   * Resolves the ordered list of currently eligible campaigns for the stadium perimeter.
   * Falls back to official GTEX house campaigns when no external campaigns are eligible.
   */
  public getEligiblePool(nowMs: number = Date.now(), matchTimeSec: number = 0): StadiumLedCampaign[] {
    const externalPool = [
      ...this.customCampaigns,
      ...this.sponsorshipCampaigns.filter((c) => c.source !== "house_fallback"),
      ...this.brandCampaigns,
      ...this.monetizationCampaigns,
    ].filter((c) => isCampaignEligible(c, nowMs, matchTimeSec, this.matchContext));

    // Deduplicate by campaign id, preserving highest priority/source rank
    const byId = new Map<string, StadiumLedCampaign>();
    for (const c of externalPool) {
      const existing = byId.get(c.id);
      if (!existing || this.computeScore(c) > this.computeScore(existing)) {
        byId.set(c.id, c);
      }
    }

    const sortedExternal = Array.from(byId.values()).sort(
      (a, b) => this.computeScore(b) - this.computeScore(a)
    );

    if (sortedExternal.length >= 2) {
      return sortedExternal;
    }

    if (sortedExternal.length === 1) {
      // Pair single active sponsor with club/competition identity or top GTEX house creative
      const clubFallback = this.buildClubIdentityFallbackCampaign();
      return [sortedExternal[0], clubFallback, ...DEFAULT_HOUSE_FALLBACK_CAMPAIGNS];
    }

    const clubFallback = this.buildClubIdentityFallbackCampaign();
    return [clubFallback, ...DEFAULT_HOUSE_FALLBACK_CAMPAIGNS];
  }

  private buildClubIdentityFallbackCampaign(): StadiumLedCampaign {
    const homeName = (this.matchContext.homeTeamName || "LAGOS ATLAS FC").toUpperCase();
    const awayName = (this.matchContext.awayTeamName || "ABUJA SOVEREIGN SC").toUpperCase();
    const compName = (this.matchContext.competitionName || "GTEX PREMIER BROADCAST").toUpperCase();
    return {
      id: `gtex-matchday-${this.matchContext.matchId || "fixture"}`,
      brandName: `${homeName} vs ${awayName}`,
      headline: `${compName} • OFFICIAL 3D MATCHDAY FEED`,
      tagline: "LIVE STADIUM NETWORK",
      categoryLabel: "MATCHDAY SHOWCASE",
      source: "house_fallback",
      priority: 15,
      status: "approved",
      isApproved: true,
      isActive: true,
      primaryColor: this.matchContext.homePrimaryColor || "#064E3B",
      accentColor: "#10B981",
      textColor: "#FFFFFF",
    };
  }

  private computeScore(c: StadiumLedCampaign): number {
    return (SOURCE_RANK[c.source] || 0) * 1000 + (c.priority || 0);
  }

  private preloadImage(url?: string | null): void {
    if (!url || typeof Image === "undefined") return;
    if (this.loadedImages.has(url) || this.failedImageUrls.has(url)) return;
    try {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        if (this.isDisposed) return;
        this.loadedImages.set(url, img);
        this.needsRedraw = true;
        this.renderCurrentPairToCanvas();
      };
      img.onerror = () => {
        this.failedImageUrls.add(url);
      };
      img.src = url;
    } catch {
      this.failedImageUrls.add(url);
    }
  }

  private syncVideoSource(campaign: StadiumLedCampaign): void {
    const videoUrl = campaign.videoUrl || null;
    if (videoUrl === this.activeVideoUrl) return;

    if (this.activeVideoEl) {
      this.activeVideoEl.pause();
      this.activeVideoEl.removeAttribute("src");
      this.activeVideoEl = null;
    }
    this.activeVideoUrl = videoUrl;

    if (videoUrl && typeof document !== "undefined") {
      try {
        const video = document.createElement("video");
        video.crossOrigin = "anonymous";
        video.muted = true;
        video.loop = true;
        video.playsInline = true;
        video.src = videoUrl;
        this.activeVideoEl = video;
        if (this.isDocumentVisible) {
          void video.play().catch(() => undefined);
        }
      } catch {
        this.activeVideoEl = null;
      }
    }
  }

  /**
   * Steps the advertising network clock. Rotates campaigns ONLY on slot boundaries
   * (`Math.floor(elapsedSec / rotationIntervalSec)`), avoiding per-frame texture rebuilds.
   */
  public update(
    deltaSec: number,
    elapsedSec: number,
    matchTimeSec: number = elapsedSec,
    nowMs: number = Date.now()
  ): void {
    if (this.isDisposed) return;

    const targetRotationIndex = Math.max(0, Math.floor(elapsedSec / this.rotationIntervalSec));
    if (targetRotationIndex !== this.currentRotationIndex || this.needsRedraw) {
      const rotationChanged = targetRotationIndex !== this.currentRotationIndex;
      this.RefreshSlotPair(targetRotationIndex, matchTimeSec, nowMs, rotationChanged);
    }

    // If an active campaign has a playing muted video creative, refresh at capped 12fps
    if (
      this.activeVideoEl &&
      this.isDocumentVisible &&
      !this.activeVideoEl.paused &&
      this.activeVideoEl.readyState >= 2 &&
      nowMs - this.lastVideoFrameRedrawMs >= 80
    ) {
      this.lastVideoFrameRedrawMs = nowMs;
      this.renderCurrentPairToCanvas();
    }

    // Impression dwell tracking (only when document is visible)
    if (this.isDocumentVisible && deltaSec > 0) {
      this.slotDwellSec += deltaSec;
      if (this.slotDwellSec >= this.minVisibleDwellSec) {
        this.recordSlotImpressionsIfNeeded(nowMs);
      }
    }
  }

  private refreshActiveSlots(matchTimeSec: number, nowMs: number, forceRedraw: boolean): void {
    const idx = Math.max(0, this.currentRotationIndex);
    this.RefreshSlotPair(idx, matchTimeSec, nowMs, forceRedraw);
  }

  private RefreshSlotPair(
    targetRotationIndex: number,
    matchTimeSec: number,
    nowMs: number,
    rotationChanged: boolean
  ): void {
    const pool = this.getEligiblePool(nowMs, matchTimeSec);
    const total = pool.length;
    const primaryIdx = targetRotationIndex % total;
    const secondaryIdx = (targetRotationIndex + 1) % total;

    const slotA = pool[primaryIdx] ?? DEFAULT_HOUSE_FALLBACK_CAMPAIGNS[0];
    const slotB = pool[secondaryIdx] ?? slotA;

    if (rotationChanged && this.currentRotationIndex >= 0) {
      this.rotationCount += 1;
      this.slotDwellSec = 0;
    } else if (this.currentRotationIndex < 0) {
      this.slotDwellSec = 0;
    }

    this.currentRotationIndex = targetRotationIndex;
    this.currentPair = [slotA, slotB];
    this.needsRedraw = false;

    this.syncVideoSource(slotA.videoUrl ? slotA : slotB);
    this.renderCurrentPairToCanvas();

    if (rotationChanged && this.onRotationChanged) {
      this.onRotationChanged([slotA, slotB], targetRotationIndex);
    }
  }

  private recordSlotImpressionsIfNeeded(nowMs: number): void {
    const rotIdx = Math.max(0, this.currentRotationIndex);
    this.currentPair.forEach((campaign, slotIndex) => {
      if (!campaign || campaign.source === "house_fallback") return;
      const dedupeKey = `${campaign.id}::rot:${rotIdx}::slot:${slotIndex}`;
      if (this.recordedImpressionKeys.has(dedupeKey)) return;
      this.recordedImpressionKeys.add(dedupeKey);

      const event: StadiumAdImpressionEvent = {
        campaignId: campaign.id,
        brandName: campaign.brandName,
        source: campaign.source,
        slotIndex,
        rotationIndex: rotIdx,
        idempotencyKey: `stadium-led-impression-${this.matchContext.matchId || "match"}-${campaign.id}-r${rotIdx}-s${slotIndex}`,
        matchId: this.matchContext.matchId,
        timestampMs: nowMs,
      };
      this.impressionHistory.push(event);

      if (this.onImpressionRecorded) {
        this.onImpressionRecorded(event);
      }

      if (this.enableImpressionPost && campaign.trackPublicBrandImpression && typeof window !== "undefined") {
        void axios
          .post(
            `${API}/v2/public/ads/events`,
            {
              campaign_id: campaign.id,
              event_type: "impression",
              idempotency_key: event.idempotencyKey,
              metadata_json: {
                placement: "stadium_perimeter",
                surface: "stadium_led_perimeter",
                match_id: this.matchContext.matchId || null,
                slot_index: slotIndex,
                rotation_index: rotIdx,
              },
            },
            { timeout: 1800 }
          )
          .catch(() => undefined);
      }
    });
  }

  /**
   * Renders the active 2-slot campaign pair onto the 2048x256 offscreen LED canvas
   * with high-contrast broadcast typography, brand badges, and LED pixel-grid styling.
   */
  private renderCurrentPairToCanvas(): void {
    const ctx = this.ctx;
    if (!ctx || !this.canvas) return;

    const W = this.canvas.width; // 2048
    const H = this.canvas.height; // 256
    const panelW = W / 2; // 1024 per slot panel

    ctx.clearRect(0, 0, W, H);

    this.drawCampaignPanel(ctx, this.currentPair[0], 0, 0, panelW, H);
    this.drawCampaignPanel(ctx, this.currentPair[1], panelW, 0, panelW, H);

    // Subtle LED scanline / matrix overlay for authentic broadcast stadium ribbon look
    ctx.fillStyle = "rgba(0, 0, 0, 0.14)";
    for (let y = 0; y < H; y += 6) {
      ctx.fillRect(0, y, W, 1.5);
    }

    // Center divider pillar between LED cabinets
    ctx.fillStyle = "#020617";
    ctx.fillRect(panelW - 4, 0, 8, H);
    ctx.fillStyle = "#38BDF8";
    ctx.fillRect(panelW - 1, 16, 2, H - 32);

    this.texture.needsUpdate = true;
  }

  private drawCampaignPanel(
    ctx: CanvasRenderingContext2D,
    campaign: StadiumLedCampaign,
    x: number,
    y: number,
    w: number,
    h: number
  ): void {
    const palette = resolveBrandPalette(
      campaign.brandName,
      campaign.primaryColor,
      campaign.accentColor
    );
    const primary = campaign.primaryColor || palette.primary;
    const accent = campaign.accentColor || palette.accent;
    const textCol = campaign.textColor || "#FFFFFF";

    // High-contrast LED cabinet background gradient
    const bgGrad = ctx.createLinearGradient(x, y, x + w, y + h);
    bgGrad.addColorStop(0, primary);
    bgGrad.addColorStop(0.72, "#070D19");
    bgGrad.addColorStop(1, primary);
    ctx.fillStyle = bgGrad;
    ctx.fillRect(x, y, w, h);

    // Top and bottom illuminated LED rails
    ctx.fillStyle = accent;
    ctx.fillRect(x, y, w, 10);
    ctx.fillRect(x, y + h - 10, w, 10);

    // Left angled accent chevron
    ctx.fillStyle = accent;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 210, y);
    ctx.lineTo(x + 175, y + h);
    ctx.lineTo(x, y + h);
    ctx.closePath();
    ctx.fill();

    // Draw brand logo / video / monogram inside the left badge zone
    const logoImg =
      (campaign.logoUrl && this.loadedImages.get(campaign.logoUrl)) ||
      (campaign.creativeUrl && this.loadedImages.get(campaign.creativeUrl)) ||
      null;

    if (
      campaign.videoUrl &&
      this.activeVideoEl &&
      this.activeVideoUrl === campaign.videoUrl &&
      this.activeVideoEl.readyState >= 2
    ) {
      try {
        ctx.drawImage(this.activeVideoEl, x + 16, y + 24, 145, h - 48);
      } catch {
        this.drawBrandMonogram(ctx, campaign.brandName, x + 90, y + h / 2, primary);
      }
    } else if (logoImg) {
      try {
        ctx.drawImage(logoImg, x + 20, y + 32, 140, h - 64);
      } catch {
        this.drawBrandMonogram(ctx, campaign.brandName, x + 90, y + h / 2, primary);
      }
    } else {
      this.drawBrandMonogram(ctx, campaign.brandName, x + 90, y + h / 2, primary);
    }

    // Category / Sponsor Tier Pill (top-right)
    const badgeLabel = (campaign.categoryLabel || palette.badge).toUpperCase();
    ctx.fillStyle = "rgba(255, 255, 255, 0.12)";
    ctx.fillRect(x + w - 265, y + 22, 245, 42);
    ctx.strokeStyle = accent;
    ctx.lineWidth = 2;
    ctx.strokeRect(x + w - 265, y + 22, 245, 42);

    ctx.fillStyle = accent === "#0B132B" || accent === "#0F172A" ? "#FFFFFF" : accent;
    ctx.font = "900 20px 'Outfit', 'Inter', system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(badgeLabel.slice(0, 22), x + w - 142, y + 43);

    // Main Brand Name (ultra-large high-contrast typography for 58m camera legibility)
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    const brandTitle = campaign.brandName.toUpperCase().slice(0, 26);
    ctx.font = "900 72px 'Outfit', 'Inter', system-ui, sans-serif";
    ctx.strokeStyle = "rgba(0, 0, 0, 0.85)";
    ctx.lineWidth = 6;
    ctx.strokeText(brandTitle, x + 208, y + 122);
    ctx.fillStyle = textCol;
    ctx.fillText(brandTitle, x + 208, y + 122);

    // Campaign Headline / Slogan
    const headlineText = (campaign.headline || "OFFICIAL GTEX BROADCAST PARTNER")
      .toUpperCase()
      .slice(0, 44);
    ctx.font = "800 38px 'Inter', system-ui, sans-serif";
    ctx.fillStyle = accent === "#0B132B" || accent === "#0F172A" ? "#FDE047" : accent;
    ctx.fillText(headlineText, x + 210, y + 186);

    // Sub-tagline
    const taglineText = (campaign.tagline || "GTEX LIVE STADIUM NETWORK").toUpperCase().slice(0, 52);
    ctx.font = "700 22px 'JetBrains Mono', monospace";
    ctx.fillStyle = "rgba(226, 232, 240, 0.9)";
    ctx.fillText(taglineText, x + 210, y + 226);
  }

  private drawBrandMonogram(
    ctx: CanvasRenderingContext2D,
    brandName: string,
    cx: number,
    cy: number,
    bgHex: string
  ): void {
    ctx.fillStyle = bgHex === "#FFCC00" || bgHex === "#F5A623" ? "#091526" : "#020617";
    ctx.beginPath();
    ctx.arc(cx, cy, 66, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "#FFFFFF";
    ctx.lineWidth = 4;
    ctx.stroke();

    const words = brandName
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    const initials =
      words.length >= 2
        ? `${words[0][0]}${words[1][0]}`.toUpperCase()
        : brandName.slice(0, 3).toUpperCase();

    ctx.fillStyle = "#FFFFFF";
    ctx.font = "900 46px 'Outfit', 'Inter', system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(initials, cx, cy + 2);
  }

  public dispose(): void {
    this.isDisposed = true;
    if (this.activeVideoEl) {
      this.activeVideoEl.pause();
      this.activeVideoEl.removeAttribute("src");
      this.activeVideoEl = null;
    }
    this.loadedImages.clear();
    this.texture.dispose();
  }
}
