import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useGlobalTicker, fmt } from "@/lib/owner";
import { Plane, Building, Gift, CheckCircle, ExternalLink } from "lucide-react";

export function GlobalLiveTicker() {
  const { data, isLoading } = useGlobalTicker(undefined, 15);
  const events: any[] = data?.events || [];
  const [isPaused, setIsPaused] = useState(false);

  if (isLoading && events.length === 0) {
    return (
      <div className="bg-slate-950/80 border-b border-white/5 py-1.5 px-4 text-xs text-slate-400 flex items-center space-x-2">
        <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px]">GTEX Live Wire:</span>
        <span className="italic">Connecting to global verified broadcasts...</span>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="bg-slate-950/80 border-b border-white/5 py-1.5 px-4 text-xs text-slate-400 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
          <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px]">GTEX Live Wire</span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400">Verified private jet purchases, facility upgrades, and player awards broadcast globally.</span>
        </div>
        <Link to="/app/newsroom" className="text-[11px] text-amber-400 hover:text-amber-300 flex items-center space-x-1">
          <span>Newsroom</span>
          <ExternalLink className="w-3 h-3" />
        </Link>
      </div>
    );
  }

  return (
    <div
      className="bg-slate-950/90 border-b border-amber-500/20 py-2 px-3 text-xs overflow-hidden relative shadow-inner"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="max-w-7xl mx-auto flex items-center space-x-3">
        {/* Ticker Badge */}
        <div className="flex items-center space-x-1.5 shrink-0 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded text-[10px] font-bold text-amber-400 uppercase tracking-wider">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
          <span>Global Wire</span>
        </div>

        {/* Scrolling or Flex items */}
        <div className="flex-1 overflow-x-auto no-scrollbar py-0.5">
          <div className={`flex items-center space-x-4 min-w-max ${isPaused ? "" : "animate-ticker"}`}>
            {events.map((evt) => {
              const isJet = evt.event_type === "private_jet_purchase";
              const isFacility = evt.event_type === "facility_upgrade";
              const isGift = evt.event_type === "player_gift";

              return (
                <div
                  key={evt.id}
                  className="flex items-center space-x-2.5 bg-slate-900/90 border border-slate-800 hover:border-amber-500/50 rounded-full pl-1.5 pr-3 py-1 transition-colors group"
                >
                  {/* Thumbnail / Icon */}
                  {evt.item_image_url || evt.player_portrait_url ? (
                    <img
                      src={evt.item_image_url || evt.player_portrait_url}
                      alt={evt.item_name || "Broadcast"}
                      className="w-6 h-6 rounded-full object-cover border border-white/10 shrink-0 bg-slate-800"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center shrink-0">
                      {isJet && <Plane className="w-3 h-3 text-amber-400" />}
                      {isFacility && <Building className="w-3 h-3 text-emerald-400" />}
                      {isGift && <Gift className="w-3 h-3 text-purple-400" />}
                    </div>
                  )}

                  {/* Headline & Details */}
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-slate-200 group-hover:text-amber-300 transition-colors">
                      {evt.headline || `${evt.owner_name} · ${evt.club_name}`}
                    </span>

                    {/* Price Tag if applicable */}
                    {Number(evt.verified_price_gtex) > 0 && (
                      <span className="inline-flex items-center space-x-1 px-1.5 py-0.2 bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded text-[10px] font-mono font-medium">
                        <CheckCircle className="w-2.5 h-2.5 text-amber-400" />
                        <span>{fmt(evt.verified_price_gtex)} GTX</span>
                      </span>
                    )}

                    {/* Club Story Link */}
                    {evt.club_id && (
                      <Link
                        to={`/app/clubs/${evt.club_id}/story`}
                        className="text-[10px] text-slate-500 hover:text-slate-300 underline underline-offset-2 ml-1"
                        title="View Club Story"
                      >
                        Story
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right CTA */}
        <div className="shrink-0 pl-2 border-l border-slate-800">
          <Link
            to="/app/newsroom"
            className="text-[11px] font-medium text-amber-400 hover:text-amber-300 flex items-center space-x-1"
          >
            <span>Newsroom</span>
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  );
}
