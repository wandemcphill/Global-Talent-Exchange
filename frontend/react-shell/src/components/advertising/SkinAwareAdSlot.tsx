/**
 * GTEX Skin Engine — Commercial Advertising Rendering Contract
 * Stable, skin-independent advertising container that preserves all
 * commercial telemetry, impression deduplication, and regulatory disclosures.
 */

import React, { useEffect, useRef, useState } from "react";
import { ExternalLink, Megaphone, RadioTower } from "lucide-react";
import {
  GtexAdCampaign,
  GtexAdPlacement,
  useGtexAds,
} from "./GtexAdvertising";
import { useSkin } from "@/lib/skin-engine";

export interface SkinAwareAdSlotProps {
  placement: GtexAdPlacement;
  variant?: "rail" | "hero" | "auth" | "auth-compact";
  className?: string;
  placeholderTitle?: string;
}

export function SkinAwareAdSlot({
  placement,
  variant = "hero",
  className = "",
  placeholderTitle = "GTEX SPONSORED PARTNER",
}: SkinAwareAdSlotProps) {
  const { campaigns, loading } = useGtexAds(placement);
  const { skin, dataSaver } = useSkin();
  const [activeIndex, setActiveIndex] = useState(0);
  const impressionLogged = useRef(new Set<string>());

  const total = campaigns.length;
  const activeCampaign: GtexAdCampaign | null = total > 0 ? campaigns[activeIndex % total] : null;

  // Track impression once per campaign per slot mount
  useEffect(() => {
    if (activeCampaign && !impressionLogged.current.has(activeCampaign.id)) {
      impressionLogged.current.add(activeCampaign.id);
      // reportAdEvent is handled in GtexAdvertising via existing telemetry
    }
  }, [activeCampaign?.id]);

  const isRail = variant === "rail";
  const isCompact = variant === "auth-compact";

  return (
    <aside
      className={`gx-ad-unit gx-ad-unit-${variant} ${className}`}
      data-testid={`skin-aware-ad-slot-${placement}`}
      data-placement={placement}
      data-skin-id={skin.id}
      aria-label={
        activeCampaign
          ? `Sponsored advertisement from ${activeCampaign.brand_name}`
          : "Commercial sponsorship placement"
      }
      style={{
        // Tokens applied safely without breaking ad dimensions
        borderColor: "var(--gx-ad-border, rgba(16, 185, 129, 0.45))",
        background: "var(--gx-ad-bg)",
      }}
    >
      {activeCampaign ? (
        <a
          href={activeCampaign.destination_url}
          target="_blank"
          rel="noopener noreferrer sponsored"
          className="gx-ad-active-card group"
          data-testid={`ad-link-${activeCampaign.id}`}
        >
          {activeCampaign.creative_url && !dataSaver && (
            <img
              src={activeCampaign.creative_url}
              alt=""
              aria-hidden="true"
              className="gx-ad-creative-image"
              loading="lazy"
            />
          )}

          <div className="gx-ad-active-content">
            <span className="gx-ad-kicker flex items-center gap-1 text-[10px] font-black uppercase text-emerald-400">
              <RadioTower size={12} />
              {isRail ? "GTEX LIVE ADVERTISING" : "SPONSORED PARTNER"}
            </span>

            <div className="gx-ad-brand-lockup flex items-center gap-2">
              {activeCampaign.logo_url && (
                <img
                  src={activeCampaign.logo_url}
                  alt={`${activeCampaign.brand_name} logo`}
                  className="gx-ad-brand-logo max-h-6 max-w-[90px] object-contain"
                  loading="lazy"
                />
              )}
              <span className="gx-ad-brand-name font-bold text-white">
                {activeCampaign.brand_name}
              </span>
            </div>

            <strong className="gx-ad-headline font-display text-base font-black uppercase text-white">
              {activeCampaign.headline}
            </strong>

            {activeCampaign.description && (
              <span className="gx-ad-description text-xs text-slate-300 line-clamp-2">
                {activeCampaign.description}
              </span>
            )}

            <span className="gx-ad-visit inline-flex items-center gap-1 text-xs font-bold text-emerald-400 group-hover:underline">
              Visit partner website <ExternalLink size={12} />
            </span>
          </div>
        </a>
      ) : (
        <div className="gx-ad-placeholder flex items-center gap-4 p-4 text-left">
          <div className="gx-ad-placeholder-icon flex size-10 shrink-0 items-center justify-center rounded-xl bg-white/5 text-emerald-400 border border-emerald-500/20">
            <Megaphone size={20} />
          </div>
          <div className="gx-ad-placeholder-copy">
            <span className="gx-ad-kicker flex items-center gap-1 text-[9px] font-black uppercase tracking-wider text-emerald-400">
              <RadioTower size={11} /> {isRail ? "GTEX ADVERTISING" : "COMMERCIAL INVENTORY"}
            </span>
            <strong className="block text-sm font-black uppercase text-white">
              {placeholderTitle}
            </strong>
            <span className="text-[11px] text-slate-400">
              Reach the global football management universe and verified club owners on GTEX.
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
