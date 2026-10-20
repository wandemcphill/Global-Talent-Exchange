import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useNewsroom, fmt } from "@/lib/owner";
import { Newspaper, ShieldCheck, CheckCircle2, Filter, Calendar, ExternalLink, Plane, Building, Gift, Trophy } from "lucide-react";

export function Newsroom() {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const { data, isLoading } = useNewsroom(undefined, selectedCategory, 30);
  const articles: any[] = data?.articles || [];

  const categories = [
    { key: "all", label: "All Wire" },
    { key: "private_jet_purchase", label: "Jet Deliveries", icon: Plane },
    { key: "facility_upgrade", label: "Infrastructure", icon: Building },
    { key: "player_gift", label: "Player Gifts", icon: Gift },
    { key: "match_result", label: "Match Reports", icon: Trophy },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center space-x-2 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <Newspaper className="w-4 h-4" />
            <span>GTEX Press & Global Editorial</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">The Boardroom Chronicle</h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Real-time, verified football reporting and club-owner developments. All reporting is grounded in authoritative
            ledger and pitch events—distinguishing established facts from editorial narrative.
          </p>
        </div>

        {/* Verification Legend */}
        <div className="flex items-center space-x-2 bg-slate-900/90 border border-emerald-500/30 px-3 py-2 rounded-lg text-xs">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <div className="text-[11px] text-slate-300">
            <span className="font-semibold text-emerald-300">GTEX Grounding Guarantee:</span> AI narration cannot invent
            prices, modify state, or fabricate match scorelines.
          </div>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2 no-scrollbar">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const active = selectedCategory === cat.key;
          return (
            <button
              key={cat.key}
              onClick={() => setSelectedCategory(cat.key)}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors ${
                active
                  ? "bg-amber-500 text-slate-950 font-semibold shadow-sm"
                  : "bg-slate-900 text-slate-300 hover:bg-slate-800 border border-slate-800"
              }`}
            >
              {Icon && <Icon className="w-3.5 h-3.5" />}
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      {/* Articles Feed */}
      {isLoading ? (
        <div className="py-20 text-center text-slate-500">
          <div className="inline-block w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mb-3"></div>
          <p className="text-sm">Fetching verified dispatches from the newsroom...</p>
        </div>
      ) : articles.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-400">
          <Newspaper className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No Dispatches in this Wire</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Stories are generated immediately upon completed boardroom purchases, facility expansions, or final match whistles.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {articles.map((art) => {
            const facts = art.established_facts || {};
            const isVerified = art.is_grounded !== false;

            return (
              <article
                key={art.id}
                className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl overflow-hidden flex flex-col transition-shadow hover:shadow-lg"
              >
                {/* Visual Header */}
                {art.hero_image_url && (
                  <div className="relative h-44 w-full bg-slate-950 overflow-hidden">
                    <img
                      src={art.hero_image_url}
                      alt={art.headline}
                      className="w-full h-full object-cover object-center"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent"></div>
                    <div className="absolute top-3 left-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-900/90 text-amber-400 border border-amber-500/30">
                        {art.category.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
                )}

                <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{new Date(art.created_at).toLocaleDateString()}</span>
                      {art.world_day && <span>World Day {art.world_day}</span>}
                    </div>

                    <h2 className="text-lg font-bold text-white group-hover:text-amber-400 leading-snug">
                      {art.headline}
                    </h2>

                    {art.subhead && (
                      <p className="text-xs font-medium text-slate-300 italic">{art.subhead}</p>
                    )}

                    {/* Editorial Narration */}
                    <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-line pt-1">
                      {art.editorial_narration || art.body}
                    </div>
                  </div>

                  {/* Established Facts Box */}
                  <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      <span className="flex items-center space-x-1 text-emerald-400">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Verified Facts</span>
                      </span>
                      {isVerified && (
                        <span className="text-[9px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">
                          Grounded
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px]">
                      {facts.club_name && (
                        <div>
                          <span className="text-slate-500">Club: </span>
                          <span className="text-slate-200 font-medium">{facts.club_name}</span>
                        </div>
                      )}
                      {facts.owner && (
                        <div>
                          <span className="text-slate-500">Owner: </span>
                          <span className="text-slate-200 font-medium">{facts.owner}</span>
                        </div>
                      )}
                      {facts.item_name && (
                        <div className="col-span-2">
                          <span className="text-slate-500">Item: </span>
                          <span className="text-amber-300 font-medium">{facts.item_name}</span>
                        </div>
                      )}
                      {facts.verified_price_gtex && Number(facts.verified_price_gtex) > 0 && (
                        <div>
                          <span className="text-slate-500">Verified Cost: </span>
                          <span className="text-emerald-400 font-mono font-medium">
                            {fmt(facts.verified_price_gtex)} GTX
                          </span>
                        </div>
                      )}
                      {facts.player_name && (
                        <div>
                          <span className="text-slate-500">Player: </span>
                          <span className="text-slate-200 font-medium">{facts.player_name}</span>
                        </div>
                      )}
                      {facts.home_club && (
                        <div className="col-span-2">
                          <span className="text-slate-500">Fixture: </span>
                          <span className="text-slate-200 font-medium">
                            {facts.home_club} {facts.scoreline} {facts.away_club}
                          </span>
                        </div>
                      )}
                    </div>

                    {art.club_id && (
                      <div className="pt-2 border-t border-slate-900 flex justify-end">
                        <Link
                          to={`/app/clubs/${art.club_id}/story`}
                          className="text-[11px] text-amber-400 hover:text-amber-300 flex items-center space-x-1"
                        >
                          <span>View Club Story</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </div>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
