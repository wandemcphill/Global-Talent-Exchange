import React, { useState } from "react";
import { Sparkles, UserCheck, Dumbbell, Trophy, TrendingUp, Activity, Award } from "lucide-react";
import { kFeaturedRegens, RegenTalentProfile } from "./landingModels";

interface RegenJourneyStep {
  stepNumber: string;
  title: string;
  subtitle: string;
  detail: string;
  metricLabel: string;
  metricValue: string;
  icon: any;
  accentColor: string;
}

const JOURNEY_STEPS: RegenJourneyStep[] = [
  {
    stepNumber: "01",
    title: "Academy Intake & Scout Identification",
    subtitle: "Scouts identify a young prospect with room to grow.",
    detail:
      "The live GTEX regen engine should supply a prospect’s identity, attributes, personality and potential. This step illustrates how an academy-intake story could be presented.",
    metricLabel: "EXAMPLE INTAKE",
    metricValue: "Youth prospect",
    icon: UserCheck,
    accentColor: "#38BDF8",
  },
  {
    stepNumber: "02",
    title: "Apex Campus & Training Multipliers",
    subtitle: "Sports science, youth facilities, and mentor coaching accelerate development.",
    detail:
      "Facility and training effects should follow the current simulation rules. Display specific multipliers only when they are confirmed by the game engine.",
    metricLabel: "DEVELOPMENT",
    metricValue: "Training + mentoring",
    icon: Dumbbell,
    accentColor: "#36E38A",
  },
  {
    stepNumber: "03",
    title: "Competitive Squad Progression",
    subtitle: "From U19 tournaments to first-team matchday bench and continental debuts.",
    detail:
      "Use the actual player’s appearances, progression history and attributes to tell this story. Do not invent match statistics, awards or progression guarantees.",
    metricLabel: "PATHWAY",
    metricValue: "Academy → First XI",
    icon: Trophy,
    accentColor: "#D4AF37",
  },
  {
    stepNumber: "04",
    title: "Valuation & Transfer Marketplace",
    subtitle: "A developing player may attract interest from other clubs.",
    detail:
      "Transfer values depend on the player record, contracts and actual marketplace activity. Rentals, purchases and sales should be described only where supported by the current game systems.",
    metricLabel: "TRANSFER MARKET",
    metricValue: "Value can change",
    icon: TrendingUp,
    accentColor: "#A855F7",
  },
];

export const RegenEconomySection: React.FC = () => {
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
  const [selectedRegenIndex, setSelectedRegenIndex] = useState<number>(0);

  const activeStep = JOURNEY_STEPS[activeStepIndex];
  const activeRegen: RegenTalentProfile = kFeaturedRegens[selectedRegenIndex];

  return (
    <section id="regens" className="border-b border-[#22385A] bg-[#0B1626] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Masthead */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-[#D4AF37] shadow-[0_0_8px_#D4AF37]"></span>
            <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#D4AF37]">
              Player Development & The Regen Economy
            </p>
          </div>
          <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
            Discover the Next Superstar. Build Living Football Value.
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            Explore an illustrative journey from academy intake to first-team football. In live
            GTEX, player identity, ratings, development history and valuation should come from the
            existing regen engine and player records.
          </p>
        </div>

        {/* 4-Step Pathway Stepper */}
        <div className="mt-10 overflow-x-auto pb-2 gx-scroll">
          <div className="flex gap-3 min-w-max">
            {JOURNEY_STEPS.map((step, idx) => {
              const isSelected = idx === activeStepIndex;
              return (
                <button
                  key={step.stepNumber}
                  onClick={() => setActiveStepIndex(idx)}
                  className={`flex items-center gap-3 rounded-xl border p-3.5 text-left transition-all ${
                    isSelected
                      ? "border-white/30 bg-[#1A2E4A]"
                      : "border-[#22385A] bg-[#13233A] hover:border-[#2F4C75]"
                  }`}
                  style={{
                    borderColor: isSelected ? step.accentColor : undefined,
                  }}
                >
                  <span
                    className="font-['JetBrains_Mono'] text-lg font-black"
                    style={{ color: isSelected ? step.accentColor : "#6B7A93" }}
                  >
                    {step.stepNumber}
                  </span>
                  <div>
                    <p
                      className={`font-['Barlow_Condensed'] text-sm font-bold uppercase ${
                        isSelected ? "text-[#F2F4F8]" : "text-[#9AA7BD]"
                      }`}
                    >
                      {step.title}
                    </p>
                    <p
                      className="font-['JetBrains_Mono'] text-[10px]"
                      style={{ color: isSelected ? step.accentColor : "#6B7A93" }}
                    >
                      {step.metricValue}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Active Step Detail Banner */}
        <div
          className="mt-4 rounded-xl border bg-[#13233A] p-5"
          style={{ borderColor: `${activeStep.accentColor}50` }}
        >
          <div className="flex items-start gap-4">
            <div
              className="rounded-lg p-2.5"
              style={{ backgroundColor: `${activeStep.accentColor}15` }}
            >
              <activeStep.icon size={22} style={{ color: activeStep.accentColor }} />
            </div>
            <div>
              <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#9AA7BD]">
                STEP {activeStep.stepNumber} • {activeStep.metricLabel}
              </span>
              <h3 className="mt-0.5 font-['Barlow_Condensed'] text-xl font-bold uppercase text-[#F2F4F8]">
                {activeStep.subtitle}
              </h3>
              <p className="mt-1 text-xs text-[#9AA7BD] leading-relaxed max-w-3xl">
                {activeStep.detail}
              </p>
            </div>
          </div>
        </div>

        {/* Featured Regen Talent Dossiers */}
        <div className="mt-14">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#22385A] pb-4">
            <div className="flex items-center gap-2">
              <Sparkles size={20} className="text-[#D4AF37]" />
              <h3 className="font-['Barlow_Condensed'] text-base font-extrabold uppercase tracking-widest text-[#D4AF37]">
                FEATURED REGEN TALENT DOSSIERS
              </h3>
            </div>
            <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#6B7A93]">
              SAMPLE PROFILES â€¢ ILLUSTRATIVE VALUES
            </span>
          </div>

          {/* Regen Selector Chips */}
          <div className="mt-6 flex flex-wrap gap-2">
            {kFeaturedRegens.map((regen, idx) => {
              const isSelected = idx === selectedRegenIndex;
              return (
                <button
                  key={regen.name}
                  onClick={() => setSelectedRegenIndex(idx)}
                  className={`rounded-xl border px-4 py-2 font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider transition-all ${
                    isSelected
                      ? "border-[#D4AF37] bg-[#D4AF37]/20 text-[#E8C766] shadow-[0_0_16px_rgba(212,175,55,0.2)]"
                      : "border-[#22385A] bg-[#13233A] text-[#9AA7BD] hover:border-[#2F4C75]"
                  }`}
                >
                  {regen.name} ({regen.position} • {regen.age})
                </button>
              );
            })}
          </div>

          {/* Dossier Card */}
          <div className="mt-6 rounded-2xl border border-[#2F4C75] bg-[#081120] p-6 sm:p-8">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
              {/* Profile Overview */}
              <div className="lg:col-span-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-[#D4AF37]/20 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#D4AF37] border border-[#D4AF37]/30">
                    {activeRegen.gsiTierLabel}
                  </span>
                  <span className="rounded bg-[#13233A] px-2.5 py-1 text-xs text-[#9AA7BD]">
                    {activeRegen.nationality} ({activeRegen.countryCode})
                  </span>
                  <span className="rounded bg-[#13233A] px-2.5 py-1 text-xs font-bold text-[#F2F4F8]">
                    {activeRegen.position} • Age {activeRegen.age}
                  </span>
                </div>

                <h4 className="mt-3 font-['Barlow_Condensed'] text-3xl font-black uppercase text-[#F2F4F8]">
                  {activeRegen.name}
                </h4>
                <p className="mt-0.5 font-['JetBrains_Mono'] text-xs text-[#38BDF8]">
                  {activeRegen.archetype}
                </p>

                <div className="mt-5 rounded-xl border border-[#22385A] bg-[#13233A] p-4">
                  <span className="text-[10px] uppercase tracking-wider text-[#6B7A93]">
                    ESTIMATED MARKET VALUE
                  </span>
                  <p className="font-['JetBrains_Mono'] text-xl font-bold text-[#E8C766]">
                    {activeRegen.estimatedValueCredits}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="rounded bg-emerald-500/20 px-2 py-0.5 font-['JetBrains_Mono'] text-xs font-bold text-[#36E38A]">
                      Current: {activeRegen.currentRating}
                    </span>
                    <span className="rounded bg-amber-500/20 px-2 py-0.5 font-['JetBrains_Mono'] text-xs font-bold text-[#E8C766]">
                      {activeRegen.potentialLabel}
                    </span>
                  </div>
                </div>

                <p className="mt-4 text-xs leading-relaxed text-[#9AA7BD]">{activeRegen.story}</p>

                {/* Traits */}
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {activeRegen.traits.map((trait) => (
                    <span
                      key={trait}
                      className="rounded border border-[#22385A] bg-[#0B1626] px-2 py-0.5 text-[10px] text-[#F2F4F8]"
                    >
                      {trait}
                    </span>
                  ))}
                </div>
              </div>

              {/* Attributes Radar & Ratings */}
              <div className="lg:col-span-7">
                <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#6B7A93]">
                  TACTICAL ATTRIBUTES & RATINGS
                </span>

                <div className="mt-4 space-y-3.5">
                  {[
                    { label: "Pace & Acceleration", val: activeRegen.pace, color: "#38BDF8" },
                    { label: "Vision & Playmaking", val: activeRegen.vision, color: "#36E38A" },
                    {
                      label: "Technique & Dribbling",
                      val: activeRegen.technique,
                      color: "#D4AF37",
                    },
                    { label: "Stamina & Physicality", val: activeRegen.stamina, color: "#F59E0B" },
                    {
                      label: "Mentality & Composure",
                      val: activeRegen.mentality,
                      color: "#A855F7",
                    },
                  ].map((attr) => (
                    <div key={attr.label}>
                      <div className="flex justify-between text-xs">
                        <span className="text-[#9AA7BD]">{attr.label}</span>
                        <span className="font-['JetBrains_Mono'] font-bold text-[#F2F4F8]">
                          {attr.val}
                        </span>
                      </div>
                      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[#13233A]">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${attr.val}%`,
                            backgroundColor: attr.color,
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Potential Ceiling Highlight */}
                <div className="mt-8 flex items-center justify-between rounded-xl border border-[#D4AF37]/40 bg-[#13233A] p-4">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-[#6B7A93]">
                      PEAK POTENTIAL CEILING
                    </span>
                    <p className="font-['Barlow_Condensed'] text-lg font-bold text-[#E8C766]">
                      {activeRegen.potentialLabel}
                    </p>
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#D4AF37] font-['Barlow_Condensed'] text-2xl font-black text-[#0B1626]">
                    {activeRegen.potentialRating}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
