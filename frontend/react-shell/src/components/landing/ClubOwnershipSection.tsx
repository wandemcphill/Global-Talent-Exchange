import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Shield,
  Building2,
  Tv,
  Plane,
  Diamond,
  Gift,
  Radio,
  ArrowRight,
} from "lucide-react";
import { publicUrl } from "@/lib/publicPath";
import {
  kClubStages,
  kShowroomAssets,
  ClubStageData,
  ShowroomAssetItem,
} from "./landingModels";

export const ClubOwnershipSection: React.FC = () => {
  // Start on Legacy stage (index 4) as in canonical Flutter design
  const [selectedStageIndex, setSelectedStageIndex] = useState<number>(4);
  const [selectedAssetIndex, setSelectedAssetIndex] = useState<number>(0);

  const currentStage: ClubStageData = kClubStages[selectedStageIndex];
  const currentAsset: ShowroomAssetItem = kShowroomAssets[selectedAssetIndex];

  return (
    <section id="ownership" className="border-b border-[#22385A] bg-[#0B1626] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Masthead */}
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-8">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2.5">
              <span className="h-2 w-2 rounded-full bg-[#D4AF37] shadow-[0_0_8px_#D4AF37]"></span>
              <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#D4AF37]">
                Club Ownership & Simulation Life
              </p>
            </div>
            <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
              From Grassroots Founder to Global Football Institution
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
              Every owner can found or acquire up to three clubs. Define club identity, construct world-class facilities, appoint tacticians, and unlock luxury aviation as your institutional prestige rises.
            </p>
          </div>

          {/* Portfolio Limit Badge */}
          <div className="flex flex-col rounded-xl border border-[#D4AF37]/40 bg-[#13233A] p-4 lg:min-w-[240px]">
            <span className="font-['Barlow_Condensed'] text-[11px] font-extrabold uppercase tracking-wider text-[#D4AF37]">
              PORTFOLIO LIMIT
            </span>
            <span className="mt-1 font-['Barlow_Condensed'] text-xl font-black uppercase text-[#F2F4F8]">
              Up to 3 Active Clubs
            </span>
            <span className="text-xs text-[#6B7A93]">
              Independent sporting ledgers
            </span>
          </div>
        </div>

        {/* Stage Selector Tabs */}
        <div className="mt-10 overflow-x-auto pb-2 gx-scroll">
          <div className="flex gap-3 min-w-max">
            {kClubStages.map((stage, idx) => {
              const isSelected = idx === selectedStageIndex;
              return (
                <button
                  key={stage.stage}
                  onClick={() => setSelectedStageIndex(idx)}
                  className={`flex flex-col items-start rounded-xl border p-4 text-left transition-all duration-200 ${
                    isSelected
                      ? "bg-[#1A2E4A] shadow-[0_4px_20px_rgba(0,0,0,0.4)]"
                      : "border-[#22385A] bg-[#13233A] hover:border-[#2F4C75]"
                  }`}
                  style={{
                    borderColor: isSelected ? stage.badgeColor : undefined,
                    boxShadow: isSelected ? `0 0 16px ${stage.badgeColor}33` : undefined,
                  }}
                >
                  <span
                    className="font-['Barlow_Condensed'] text-[10px] font-extrabold uppercase tracking-widest"
                    style={{ color: isSelected ? stage.badgeColor : "#6B7A93" }}
                  >
                    STAGE {idx + 1}
                  </span>
                  <span
                    className={`mt-1 font-['Barlow_Condensed'] text-base font-bold uppercase ${
                      isSelected ? "text-[#F2F4F8]" : "text-[#9AA7BD]"
                    }`}
                  >
                    {stage.name}
                  </span>
                  <span className="mt-1 font-['JetBrains_Mono'] text-xs font-bold text-[#36E38A]">
                    TV Share: {stage.tvSharePercentage}%
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Active Stage Detail Card */}
        <div
          className="mt-6 rounded-2xl border bg-[#13233A] p-6 sm:p-8"
          style={{ borderColor: `${currentStage.badgeColor}80` }}
        >
          <div className="flex flex-wrap items-center gap-3">
            <span
              className="rounded-md px-3 py-1 font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-wider"
              style={{
                color: currentStage.badgeColor,
                backgroundColor: `${currentStage.badgeColor}20`,
                border: `1px solid ${currentStage.badgeColor}`,
              }}
            >
              {currentStage.scoreRange.toUpperCase()}
            </span>
            <h3 className="font-['Barlow_Condensed'] text-2xl font-black uppercase text-[#F2F4F8]">
              {currentStage.name}
            </h3>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-3">
            {/* Facilities */}
            <div className="rounded-xl border border-[#22385A] bg-[#0B1626]/60 p-4">
              <div className="flex items-center gap-2 text-[#9AA7BD]">
                <Building2 size={16} />
                <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider">
                  FACILITIES & STADIUM
                </span>
              </div>
              <p className="mt-2 font-['Barlow_Condensed'] text-lg font-bold text-[#F2F4F8]">
                {currentStage.facilitiesTitle}
              </p>
              <p className="mt-1 text-xs text-[#9AA7BD] leading-relaxed">
                {currentStage.facilitiesDescription}
              </p>
            </div>

            {/* Television Distribution */}
            <div className="rounded-xl border border-[#22385A] bg-[#0B1626]/60 p-4">
              <div className="flex items-center gap-2 text-[#36E38A]">
                <Tv size={16} />
                <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider">
                  TELEVISION DISTRIBUTION
                </span>
              </div>
              <p className="mt-2 font-['Barlow_Condensed'] text-lg font-bold text-[#36E38A]">
                {currentStage.tvSharePercentage}% Club TV Share
              </p>
              <p className="mt-1 text-xs text-[#9AA7BD] leading-relaxed">
                Host club retains 40% of club tournament pool; remainder split among participants.
              </p>
            </div>

            {/* Fleet & Luxury */}
            <div className="rounded-xl border border-[#22385A] bg-[#0B1626]/60 p-4">
              <div className="flex items-center gap-2 text-[#D4AF37]">
                <Plane size={16} />
                <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider">
                  FLEET & LUXURY UNLOCK
                </span>
              </div>
              <p className="mt-2 font-['Barlow_Condensed'] text-lg font-bold text-[#D4AF37]">
                {currentStage.luxuryAssetAvailable}
              </p>
              <p className="mt-1 text-xs text-[#9AA7BD] leading-relaxed">
                Institutional assets boost owner prestige and accelerate matchday travel.
              </p>
            </div>
          </div>
        </div>

        {/* Luxury Showroom Showcase */}
        <div className="mt-14">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#22385A] pb-4">
            <div className="flex items-center gap-2">
              <Diamond size={20} className="text-[#D4AF37]" />
              <h3 className="font-['Barlow_Condensed'] text-base font-extrabold uppercase tracking-widest text-[#D4AF37]">
                THE OWNER LUXURY SHOWROOM
              </h3>
            </div>
            <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#6B7A93]">
              LUXURY FLEET • STADIUMS • FACILITIES
            </span>
          </div>

          {/* Showroom Container */}
          <div className="mt-6 rounded-2xl border border-[#2F4C75] bg-[#081120] p-6 sm:p-8">
            {/* Asset Selector Tabs */}
            <div className="flex flex-wrap gap-2">
              {kShowroomAssets.map((asset, idx) => {
                const isSelected = idx === selectedAssetIndex;
                return (
                  <button
                    key={asset.catalogKey}
                    onClick={() => setSelectedAssetIndex(idx)}
                    className={`rounded-lg border px-3.5 py-2 font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider transition-colors ${
                      isSelected
                        ? "border-[#D4AF37] bg-[#D4AF37]/20 text-[#E8C766]"
                        : "border-[#22385A] bg-[#13233A] text-[#9AA7BD] hover:border-[#2F4C75]"
                    }`}
                  >
                    {asset.name}
                  </button>
                );
              })}
            </div>

            {/* Featured Asset Showcase */}
            <div className="mt-8 grid grid-cols-1 items-center gap-8 lg:grid-cols-12">
              <div className="overflow-hidden rounded-xl border border-[#22385A] bg-[#0B1626] lg:col-span-6">
                <img
                  src={publicUrl(currentAsset.imageFile)}
                  alt={currentAsset.name}
                  className="h-72 w-full object-cover transition-transform duration-500 hover:scale-105"
                />
              </div>

              <div className="lg:col-span-6">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-[#D4AF37]/15 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#D4AF37] border border-[#D4AF37]/30">
                    {currentAsset.tag}
                  </span>
                  <span className="rounded bg-[#13233A] px-2.5 py-1 text-xs text-[#9AA7BD]">
                    {currentAsset.category}
                  </span>
                </div>

                <h4 className="mt-3 font-['Barlow_Condensed'] text-3xl font-black uppercase text-[#F2F4F8]">
                  {currentAsset.name}
                </h4>
                <p className="mt-1 font-['JetBrains_Mono'] text-xs text-[#6B7A93]">
                  Model: {currentAsset.model}
                </p>

                <p className="mt-4 text-sm leading-relaxed text-[#9AA7BD]">
                  {currentAsset.description}
                </p>

                <div className="mt-6 grid grid-cols-2 gap-4 rounded-xl border border-[#22385A] bg-[#13233A] p-4">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-[#6B7A93]">
                      ASSET ACQUISITION
                    </span>
                    <p className="font-['JetBrains_Mono'] text-lg font-bold text-[#E8C766]">
                      {currentAsset.priceGtex.toLocaleString()} GTX
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-[#6B7A93]">
                      PRESTIGE BONUS
                    </span>
                    <p className="font-['JetBrains_Mono'] text-lg font-bold text-[#36E38A]">
                      +{currentAsset.prestigeBonus} Prestige
                    </p>
                  </div>
                </div>

                <div className="mt-6 flex flex-wrap gap-4 text-xs text-[#9AA7BD]">
                  {currentAsset.broadcastOnPurchase && (
                    <div className="flex items-center gap-1.5 text-[#38BDF8]">
                      <Radio size={14} />
                      <span>Triggers verified platform broadcast</span>
                    </div>
                  )}
                  {currentAsset.canGiftToPlayer && (
                    <div className="flex items-center gap-1.5 text-[#36E38A]">
                      <Gift size={14} />
                      <span>Eligible gift for squad stars</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
