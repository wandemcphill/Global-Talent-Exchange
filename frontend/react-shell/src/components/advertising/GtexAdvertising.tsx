import React, {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import axios from "axios";
import { ArrowLeft, ArrowRight, ExternalLink, Megaphone, RadioTower } from "lucide-react";
import { API } from "@/lib/api";

export type GtexAdPlacement =
  | "homepage_rail"
  | "homepage_hero"
  | "partner_showcase"
  | "auth_canvas";

export interface GtexAdCampaign {
  id: string;
  brand_name: string;
  headline: string;
  description: string;
  placement: GtexAdPlacement;
  destination_url: string;
  logo_url?: string | null;
  creative_url?: string | null;
  priority: number;
}

interface AdvertisingContextValue {
  campaigns: GtexAdCampaign[];
  loading: boolean;
  refresh: () => Promise<void>;
}

const AdvertisingContext = createContext<AdvertisingContextValue | null>(null);

function safeHttpUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function parseCampaigns(payload: any): GtexAdCampaign[] {
  const outer = payload?.data ?? payload;
  const rows = Array.isArray(outer?.campaigns) ? outer.campaigns : [];
  return rows
    .filter((row: any) =>
      row &&
      typeof row.id === "string" &&
      typeof row.brand_name === "string" &&
      typeof row.headline === "string" &&
      safeHttpUrl(row.destination_url) &&
      ["homepage_rail", "homepage_hero", "partner_showcase", "auth_canvas"].includes(row.placement)
    )
    .map((row: any) => ({
      id: row.id,
      brand_name: row.brand_name,
      headline: row.headline,
      description: typeof row.description === "string" ? row.description : "",
      placement: row.placement,
      destination_url: safeHttpUrl(row.destination_url) as string,
      logo_url: safeHttpUrl(row.logo_url),
      creative_url: safeHttpUrl(row.creative_url),
      priority: Number.isFinite(Number(row.priority)) ? Number(row.priority) : 100,
    }));
}

export function GtexAdvertisingProvider({ children }: { children: ReactNode }) {
  const [campaigns, setCampaigns] = useState<GtexAdCampaign[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const placements: GtexAdPlacement[] = [
        "homepage_rail",
        "homepage_hero",
        "partner_showcase",
        "auth_canvas",
      ];
      const responses = await Promise.all(
        placements.map((placement) =>
          axios.get(
            API + "/public/ads/campaigns?placement=" + placement + "&limit=100",
            { timeout: 4500, headers: { Accept: "application/json" } },
          ),
        ),
      );
      setCampaigns(responses.flatMap((response) => parseCampaigns(response.data)));
    } catch {
      // Advertising must never block sign-in or page rendering.
      // Keep previously loaded campaigns if a transient refresh fails.
      setCampaigns((current) => current);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!cancelled) await refresh();
    };
    void run();
    const interval = window.setInterval(() => void run(), 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [refresh]);

  const value = useMemo(() => ({ campaigns, loading, refresh }), [campaigns, loading, refresh]);
  return <AdvertisingContext.Provider value={value}>{children}</AdvertisingContext.Provider>;
}

export function useGtexAds(placement: GtexAdPlacement) {
  const context = useContext(AdvertisingContext);
  return {
    campaigns: (context?.campaigns ?? []).filter((campaign) => campaign.placement === placement),
    loading: context?.loading ?? true,
  };
}

interface CampaignCarouselProps {
  campaigns: GtexAdCampaign[];
  variant: "rail" | "hero" | "auth" | "auth-compact";
  placeholderTitle?: string;
}

function CampaignCarousel({
  campaigns,
  variant,
  placeholderTitle = "RUN YOUR AD HERE",
}: CampaignCarouselProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const touchStart = useRef<number | null>(null);
  const total = campaigns.length;
  const active = total > 0 ? campaigns[activeIndex % total] : null;
  const isRail = variant === "rail";
  const isCompact = variant === "auth-compact";

  const move = useCallback((direction: 1 | -1) => {
    setActiveIndex((current) => {
      if (total < 2) return 0;
      return (current + direction + total) % total;
    });
  }, [total]);

  useEffect(() => {
    setActiveIndex((current) => (total ? current % total : 0));
  }, [total]);

  useEffect(() => {
    if (total < 2) return;
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    if (reducedMotion) return;
    const interval = window.setInterval(() => move(1), isRail ? 8_500 : 9_000);
    return () => window.clearInterval(interval);
  }, [isRail, move, total]);

  const handleTouchStart = (event: React.TouchEvent<HTMLDivElement>) => {
    touchStart.current = event.changedTouches[0]?.clientX ?? null;
  };
  const handleTouchEnd = (event: React.TouchEvent<HTMLDivElement>) => {
    if (touchStart.current === null || total < 2) return;
    const delta = (event.changedTouches[0]?.clientX ?? touchStart.current) - touchStart.current;
    if (Math.abs(delta) > 45) move(delta < 0 ? 1 : -1);
    touchStart.current = null;
  };

  return (
    <section
      className={"gx-ad-unit gx-ad-unit-" + variant}
      aria-label={active ? "Sponsored advertisement from " + active.brand_name : "GTEX advertising opportunity"}
      data-testid={"gtex-ad-" + variant}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {active ? (
        <a
          key={active.id}
          href={active.destination_url}
          target="_blank"
          rel="noopener noreferrer sponsored"
          className="gx-ad-active-card gx-ad-slide-enter group"
          aria-label={active.brand_name + ": " + active.headline + ". Opens advertiser website in a new tab."}
        >
          {active.creative_url && (
            <img src={active.creative_url} alt="" aria-hidden="true" className="gx-ad-creative-image" loading="lazy"/>
          )}
          <div className="gx-ad-active-content">
            <span className="gx-ad-kicker"><RadioTower size={13}/>{isRail ? "GTEX LIVE ADVERTISING" : "SPONSORED PARTNER"}</span>
            <div className="gx-ad-brand-lockup">
              {active.logo_url && <img src={active.logo_url} alt={active.brand_name + " logo"} className="gx-ad-brand-logo" loading="lazy"/>}
              <span className="gx-ad-brand-name">{active.brand_name}</span>
            </div>
            <strong className="gx-ad-headline">{active.headline}</strong>
            {active.description && <span className="gx-ad-description">{active.description}</span>}
            <span className="gx-ad-visit">Visit website <ExternalLink size={13}/></span>
          </div>
        </a>
      ) : (
        <div className="gx-ad-placeholder">
          <div className="gx-ad-placeholder-icon"><Megaphone size={isRail ? 25 : 36}/></div>
          <div className="gx-ad-placeholder-copy">
            <span className="gx-ad-kicker"><RadioTower size={13}/>{isRail ? "GTEX LIVE ADVERTISING" : "GTEX ADVERTISING OPPORTUNITY"}</span>
            <strong>{placeholderTitle}</strong>
            <span>
              {isRail
                ? "Weekly placements • High visibility • Global football audience"
                : "Reach football fans, club owners, players, creators and investors on GTEX."}
            </span>
          </div>
          {!isRail && !isCompact && <span className="gx-ad-placeholder-aside">WEEKLY<br/>CAMPAIGNS</span>}
        </div>
      )}

      {total > 1 && (
        <>
          <div className="gx-ad-controls">
            <button type="button" aria-label="Previous advertisement" onClick={() => move(-1)}><ArrowLeft size={16}/></button>
            <button type="button" aria-label="Next advertisement" onClick={() => move(1)}><ArrowRight size={16}/></button>
          </div>
          <div className="gx-ad-indicators" aria-label={"Advertisement " + (activeIndex + 1) + " of " + total}>
            {campaigns.map((campaign, index) => (
              <button
                key={campaign.id}
                type="button"
                aria-label={"Show advertisement " + (index + 1)}
                aria-current={index === activeIndex ? "true" : undefined}
                onClick={() => setActiveIndex(index)}
                className={index === activeIndex ? "is-active" : ""}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export function GtexTopAdvertisingRail() {
  const { campaigns } = useGtexAds("homepage_rail");
  return <div className="gx-ad-top-rail"><CampaignCarousel campaigns={campaigns} variant="rail"/></div>;
}

function PartnerShowcase({ campaigns }: { campaigns: GtexAdCampaign[] }) {
  if (campaigns.length === 0) return null;
  return (
    <section className="gx-ad-partner-showcase" aria-label="GTEX advertising partners">
      <div className="gx-ad-partner-label"><Megaphone size={19}/><span>SPONSORED<br/>PARTNERS</span></div>
      <div className="gx-ad-partner-track">
        {campaigns.map((campaign) => (
          <a
            key={campaign.id}
            href={campaign.destination_url}
            target="_blank"
            rel="noopener noreferrer sponsored"
            aria-label={campaign.brand_name + ": " + campaign.headline}
            className="gx-ad-partner-card"
          >
            {campaign.logo_url && <img src={campaign.logo_url} alt="" loading="lazy"/>}
            <span>{campaign.brand_name}</span>
            <ExternalLink size={12}/>
          </a>
        ))}
      </div>
    </section>
  );
}

export function GtexHomepageAdvertising() {
  const { campaigns: heroCampaigns } = useGtexAds("homepage_hero");
  const { campaigns: partnerCampaigns } = useGtexAds("partner_showcase");
  return (
    <section className="gx-ad-homepage-wrap" aria-label="GTEX commercial partners">
      <div className="gx-ad-homepage-inner">
        <CampaignCarousel campaigns={heroCampaigns} variant="hero"/>
        <PartnerShowcase campaigns={partnerCampaigns}/>
      </div>
    </section>
  );
}

export function GtexAuthAdvertisingPanel({ compact = false }: { compact?: boolean }) {
  const { campaigns } = useGtexAds("auth_canvas");
  return <CampaignCarousel campaigns={campaigns} variant={compact ? "auth-compact" : "auth"}/>;
}
