import React, { useEffect, useRef, useState } from "react";
import { ExternalLink, Music2, ShieldCheck, Sparkles, VolumeX } from "lucide-react";
import { api } from "@/lib/api";
import { resolveCommercialMediaUrl } from "@/lib/commercial/api";
import { GtexSponsoredMusicCard, useSponsoredMusic } from "@/lib/audio";

export interface PublicBrandCampaign {
  id: string;
  brand_name: string;
  headline: string;
  description: string;
  placement: string;
  placements?: string[];
  destination_url: string;
  logo_url?: string | null;
  creative_url?: string | null;
  creative_media_type?: string | null;
  is_silent_creative?: boolean;
  sponsored_label?: string;
  priority: number;
}

const sessionReportedEvents = new Set<string>();
const sessionFrequencyCounts: Record<string, number> = {};

export function recordAdEvent(
  campaignId: string,
  eventType: "impression" | "viewable_impression" | "click",
  placement: string,
) {
  const dedupeKey = `${campaignId}:${placement}:${eventType}`;
  if (eventType !== "click" && sessionReportedEvents.has(dedupeKey)) {
    return;
  }
  const freqKey = `${campaignId}:${placement}`;
  if (eventType === "impression") {
    const count = sessionFrequencyCounts[freqKey] || 0;
    if (count >= 25) return;
    sessionFrequencyCounts[freqKey] = count + 1;
  }
  sessionReportedEvents.add(dedupeKey);

  const uuid =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  void api
    .post("/public/ads/events", {
      campaign_id: campaignId,
      event_type: eventType,
      idempotency_key: `match-${placement}-${eventType}-${uuid}`.slice(0, 95),
      metadata_json: { placement, surface: "match_broadcast" },
    })
    .catch(() => undefined);
}

export function useMatchCommercialInventory(_matchId?: string, _enabled = true) {
  const [sponsorIdAd, setSponsorIdAd] = useState<PublicBrandCampaign | null>(null);
  const [livePanelAds, setLivePanelAds] = useState<PublicBrandCampaign[]>([]);
  const [halftimeAds, setHalftimeAds] = useState<PublicBrandCampaign[]>([]);
  const [perimeterAds, setPerimeterAds] = useState<PublicBrandCampaign[]>([]);
  const [rotationIdx, setRotationIdx] = useState(0);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await api.get("/public/ads/campaigns", { params: { limit: 60 } });
        const all: PublicBrandCampaign[] = Array.isArray(data?.campaigns) ? data.campaigns : [];
        if (!mounted) return;

        const matchesPlacement = (c: PublicBrandCampaign, target: string, fallbacks: string[] = []) => {
          const list = c.placements && c.placements.length > 0 ? c.placements : [c.placement];
          return list.includes(target) || fallbacks.some((f) => list.includes(f));
        };

        const sponsors = all.filter((c) => matchesPlacement(c, "match_sponsor_id", ["partner_showcase"]));
        const panels = all.filter((c) => matchesPlacement(c, "live_match_panel", ["homepage_rail", "public_homepage"]));
        const halftimes = all.filter((c) => matchesPlacement(c, "halftime_sponsorship", ["homepage_hero", "live_match_panel"]));
        const perimeters = all.filter((c) => matchesPlacement(c, "stadium_perimeter", ["match_sponsor_id", "partner_showcase"]));

        setSponsorIdAd(sponsors[0] || all[0] || null);
        setLivePanelAds(panels.length > 0 ? panels : all.slice(0, 3));
        setHalftimeAds(halftimes.length > 0 ? halftimes : panels.slice(0, 2));
        setPerimeterAds(perimeters.length > 0 ? perimeters : sponsors.slice(0, 3));
      } catch {
        // Non-blocking fallback when no live campaigns exist
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setRotationIdx((prev) => prev + 1);
    }, 30000);
    return () => clearInterval(timer);
  }, []);

  const activeLivePanelAd = livePanelAds.length > 0 ? livePanelAds[rotationIdx % livePanelAds.length] : null;
  const activeHalftimeAd = halftimeAds.length > 0 ? halftimeAds[rotationIdx % halftimeAds.length] : null;
  const activePerimeterAd = perimeterAds.length > 0 ? perimeterAds[rotationIdx % perimeterAds.length] : null;

  return {
    sponsorIdAd,
    activeLivePanelAd,
    activeHalftimeAd,
    activePerimeterAd,
    sponsorAd: sponsorIdAd,
    livePanelAd: activeLivePanelAd,
    halftimeAd: activeHalftimeAd,
    perimeterAd: activePerimeterAd,
  };
}

/**
 * A. Persistent, non-intrusive Match Sponsor Identification badge.
 */
export function MatchSponsorIdentificationBadge({
  campaign,
  ad,
}: {
  campaign?: PublicBrandCampaign | null;
  ad?: PublicBrandCampaign | null;
}) {
  const resolved = campaign ?? ad ?? null;
  useEffect(() => {
    if (resolved) {
      recordAdEvent(resolved.id, "impression", "match_sponsor_id");
    }
  }, [resolved]);

  if (!resolved) return null;

  const logoSrc = resolveCommercialMediaUrl(resolved.logo_url);

  return (
    <a
      href={resolved.destination_url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => recordAdEvent(resolved.id, "click", "match_sponsor_id")}
      data-testid="match-sponsor-id-badge"
      className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-slate-950/90 px-3 py-1 text-[11px] text-slate-200 transition hover:border-emerald-400/60"
    >
      <span className="uppercase tracking-wider text-[9px] font-bold text-emerald-400">Sponsored by</span>
      {logoSrc && (
        <img src={logoSrc} alt={resolved.brand_name} className="h-3.5 w-3.5 rounded-sm object-contain" />
      )}
      <span className="font-bold text-white truncate max-w-[140px]">{resolved.brand_name}</span>
    </a>
  );
}

/**
 * B. Silent Broadcast Advertising Panel (Side-by-side / Split-screen / Adaptive)
 * and C. Halftime Broadcast Sponsorship Showcase.
 */
export function SilentMatchBroadcastPanel({
  campaign,
  halftimeCampaign,
  liveAd,
  halftimeAd,
  isHalftime,
}: {
  campaign?: PublicBrandCampaign | null;
  halftimeCampaign?: PublicBrandCampaign | null;
  liveAd?: PublicBrandCampaign | null;
  halftimeAd?: PublicBrandCampaign | null;
  isHalftime: boolean;
}) {
  const resolvedLive = campaign ?? liveAd ?? null;
  const resolvedHalftime = halftimeCampaign ?? halftimeAd ?? null;
  const activeAd = isHalftime ? resolvedHalftime || resolvedLive : resolvedLive;
  const placementKey = isHalftime ? "halftime_sponsorship" : "live_match_panel";
  const viewableTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!activeAd) return undefined;
    recordAdEvent(activeAd.id, "impression", placementKey);
    viewableTimerRef.current = setTimeout(() => {
      recordAdEvent(activeAd.id, "viewable_impression", placementKey);
    }, 1500);
    return () => {
      if (viewableTimerRef.current) clearTimeout(viewableTimerRef.current);
    };
  }, [activeAd, placementKey]);

  if (!activeAd) return null;

  const creativeSrc = resolveCommercialMediaUrl(activeAd.creative_url || activeAd.logo_url);
  const logoSrc = resolveCommercialMediaUrl(activeAd.logo_url);
  const isVideo =
    (activeAd.creative_media_type && activeAd.creative_media_type.startsWith("video/")) ||
    (creativeSrc && /\.(mp4|webm)$/i.test(creativeSrc));

  return (
    <aside
      data-testid={isHalftime ? "match-halftime-sponsorship-panel" : "match-silent-broadcast-panel"}
      className={`rounded-2xl border p-3.5 transition-all ${
        isHalftime
          ? "border-amber-400/40 bg-gradient-to-br from-slate-900/95 via-amber-950/20 to-slate-950 shadow-lg"
          : "border-white/10 bg-slate-900/80"
      }`}
    >
      <div className="flex items-center justify-between gap-2 text-[10px] font-bold uppercase tracking-wider">
        <span className={isHalftime ? "text-amber-300" : "text-emerald-400"}>
          {isHalftime ? "Halftime Official Sponsorship" : "Broadcast Partner • Sponsored"}
        </span>
        <span className="inline-flex items-center gap-1 text-slate-400" title="Visual advertisements are strictly silent">
          <VolumeX className="h-3 w-3" />
          Silent Ad
        </span>
      </div>

      {creativeSrc && (
        <div className="mt-2.5 overflow-hidden rounded-xl border border-white/10 bg-black">
          {isVideo ? (
            <video
              src={creativeSrc}
              muted
              autoPlay
              loop
              playsInline
              data-testid="match-broadcast-silent-video"
              className="h-32 w-full object-cover"
            />
          ) : (
            <img
              src={creativeSrc}
              alt={activeAd.headline}
              className="h-32 w-full object-cover"
            />
          )}
        </div>
      )}

      <div className="mt-2.5 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            {logoSrc && (
              <img src={logoSrc} alt={activeAd.brand_name} className="h-4 w-4 rounded object-contain" />
            )}
            <span className="text-xs font-bold text-white truncate">{activeAd.brand_name}</span>
          </div>
          <div className="mt-0.5 text-xs font-semibold text-slate-200 line-clamp-1">{activeAd.headline}</div>
          {activeAd.description && (
            <p className="mt-0.5 text-[11px] text-slate-400 line-clamp-2">{activeAd.description}</p>
          )}
        </div>
        <a
          href={activeAd.destination_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => recordAdEvent(activeAd.id, "click", placementKey)}
          className="shrink-0 inline-flex items-center gap-1 rounded-lg bg-emerald-500/20 border border-emerald-400/30 px-2.5 py-1.5 text-[11px] font-bold text-emerald-300 hover:bg-emerald-500/30"
        >
          Visit
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </aside>
  );
}

/**
 * D. Stadium Pitchside Perimeter LED & Brand Sponsor Showcase.
 * Connects the GTEX Commercial Network to Stadium presentations and Public Club Profiles.
 */
export function StadiumPerimeterLEDShowcase({
  className = "",
  stadiumName = "Arena",
}: {
  className?: string;
  stadiumName?: string;
}) {
  const { perimeterAd, sponsorAd } = useMatchCommercialInventory();
  const activeAd = perimeterAd || sponsorAd;
  const placementKey = "stadium_perimeter";

  useEffect(() => {
    if (activeAd) {
      recordAdEvent(activeAd.id, "impression", placementKey);
    }
  }, [activeAd]);

  const logoSrc = activeAd ? resolveCommercialMediaUrl(activeAd.logo_url) : null;

  return (
    <div
      data-testid="stadium-perimeter-led-showcase"
      className={`relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950/20 p-5 shadow-xl ${className}`}
    >
      <div className="flex items-center justify-between gap-3 text-[10px] font-bold uppercase tracking-wider">
        <div className="flex items-center gap-1.5 text-emerald-400">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Pitchside Partner Showcase • {stadiumName}</span>
        </div>
        <span className="rounded-full bg-emerald-400/10 px-2 py-0.5 text-[9px] font-mono font-bold text-emerald-300 border border-emerald-400/20">
          Commercial Network
        </span>
      </div>

      {activeAd ? (
        <div className="mt-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            {logoSrc ? (
              <img
                src={logoSrc}
                alt={activeAd.brand_name}
                className="h-10 w-10 shrink-0 rounded-xl border border-white/10 bg-slate-950 p-1 object-contain"
              />
            ) : (
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 font-black">
                {activeAd.brand_name.slice(0, 2).toUpperCase()}
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white truncate">{activeAd.brand_name}</span>
                <span className="text-[10px] font-medium text-emerald-300 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-400/20">
                  Official Partner
                </span>
              </div>
              <p className="mt-0.5 text-xs font-semibold text-slate-200 line-clamp-1">{activeAd.headline}</p>
              {activeAd.description && (
                <p className="text-[11px] text-slate-400 line-clamp-1">{activeAd.description}</p>
              )}
            </div>
          </div>

          <a
            href={activeAd.destination_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => recordAdEvent(activeAd.id, "click", placementKey)}
            data-testid="stadium-perimeter-visit-btn"
            className="shrink-0 inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-3.5 py-2 text-xs font-bold text-slate-950 transition hover:opacity-95"
          >
            Visit Partner
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      ) : (
        <div className="mt-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h4 className="text-sm font-bold text-slate-100">Official Stadium Advertising Space</h4>
            <p className="mt-0.5 text-xs text-slate-400">
              Deliver your brand directly to matchday supporters across active GTEX continental fixtures.
            </p>
          </div>
          <a
            href="/advertise"
            data-testid="stadium-advertise-cta-btn"
            className="shrink-0 inline-flex items-center gap-1.5 rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-3.5 py-2 text-xs font-bold text-emerald-300 transition hover:bg-emerald-500/20"
          >
            Sponsor Arena
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      )}
    </div>
  );
}

/**
 * E. Stadium Matchday Soundscape & Artist Anthem Station.
 * Connects GTEX sponsored music rotation directly to club stadium showcases.
 */
export function StadiumMatchdaySoundscape({
  className = "",
  clubName = "Club",
}: {
  className?: string;
  clubName?: string;
}) {
  const { track, status } = useSponsoredMusic();
  const hasTrack = Boolean(track && status !== "idle");

  return (
    <div
      data-testid="stadium-matchday-soundscape"
      className={`relative overflow-hidden rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950/20 p-5 shadow-xl ${className}`}
    >
      <div className="flex items-center justify-between gap-3 text-[10px] font-bold uppercase tracking-wider">
        <div className="flex items-center gap-1.5 text-cyan-400">
          <Music2 className="h-3.5 w-3.5" />
          <span>Matchday Soundscape • {clubName} Anthem</span>
        </div>
        <span className="rounded-full bg-cyan-400/10 px-2 py-0.5 text-[9px] font-mono font-bold text-cyan-300 border border-cyan-400/20">
          GTEX Audio
        </span>
      </div>

      {hasTrack ? (
        <GtexSponsoredMusicCard compact className="mt-3.5 border-white/10" />
      ) : (
        <div className="mt-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h4 className="text-sm font-bold text-slate-100">Matchday Soundscape & Artist Showcase</h4>
            <p className="mt-0.5 text-xs text-slate-400">
              Atmospheric stadium acoustics, certified artist tracks, and curated anthems during live fixtures.
            </p>
          </div>
          <a
            href="/advertise/music"
            data-testid="soundscape-promote-cta-btn"
            className="shrink-0 inline-flex items-center gap-1.5 rounded-xl border border-cyan-400/30 bg-cyan-500/10 px-3.5 py-2 text-xs font-bold text-cyan-300 transition hover:bg-cyan-500/20"
          >
            Promote Music
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      )}
    </div>
  );
}
