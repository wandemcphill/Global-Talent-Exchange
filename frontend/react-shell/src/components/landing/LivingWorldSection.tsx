import React, { useState } from "react";
import {
  Newspaper,
  Plane,
  Building2,
  Sparkles,
  ArrowRight,
  X,
  Radio,
  FileText,
} from "lucide-react";
import { publicUrl } from "@/lib/publicPath";
import { NewsroomArticleItem, kEditorialExamples } from "./landingModels";

export const LivingWorldSection: React.FC = () => {
  const [inspectedArticle, setInspectedArticle] = useState<NewsroomArticleItem | null>(null);

  return (
    <section id="world" className="border-b border-[#22385A] bg-[#081120] py-20 sm:py-28">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-12">
        {/* Section Header */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-[#38BDF8] shadow-[0_0_8px_#38BDF8]"></span>
            <p className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-[0.2em] text-[#38BDF8]">
              A Living Football World
            </p>
          </div>
          <h2 className="mt-3 font-['Barlow_Condensed'] text-4xl font-black uppercase tracking-tight text-[#F2F4F8] sm:text-5xl">
            Event-Driven Football & Global Broadcasts
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
            Club milestones, broadcast revenue and breakthrough talent can all become football
            stories. These cards preview the editorial format; live headlines and transaction
            details must come from confirmed GTEX data.
          </p>
        </div>

        {/* Global Broadcast Ticker Bar */}
        <div className="mt-10 rounded-xl border border-[#2F4C75] bg-[#13233A] p-5 shadow-lg">
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-1.5 rounded bg-[#D4AF37]/15 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-black uppercase tracking-wider text-[#D4AF37] border border-[#D4AF37]/30">
              <Radio size={12} className="animate-pulse" />
              EXAMPLE ANNOUNCEMENTS
            </span>
            <span className="text-xs italic text-[#6B7A93]">
              Story format previews — not live GTEX transactions
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            {[
              {
                icon: Plane,
                headline: "Club owner acquires a flagship private jet",
                status: "STORY CONCEPT",
                owner: "Illustrative",
                time: "Preview only",
              },
              {
                icon: Building2,
                headline: "A stadium upgrade changes a club’s ambitions",
                status: "STORY CONCEPT",
                owner: "Illustrative",
                time: "Preview only",
              },
              {
                icon: Sparkles,
                headline: "Academy regen signs first professional contract",
                status: "STORY CONCEPT",
                owner: "Illustrative",
                time: "Preview only",
              },
            ].map((item, idx) => {
              const Icon = item.icon;
              return (
                <div
                  key={idx}
                  className="flex items-start gap-3 rounded-lg border border-[#22385A] bg-[#0B1626]/60 p-3"
                >
                  <div className="rounded p-2 bg-[#22385A]/50 text-[#D4AF37]">
                    <Icon size={16} />
                  </div>
                  <div>
                    <span className="rounded bg-[#6B7A93]/20 px-1.5 py-0.5 text-[9px] font-bold text-[#9AA7BD]">
                      {item.status}
                    </span>
                    <p className="mt-1 text-xs font-semibold text-[#F2F4F8] leading-snug">
                      {item.headline}
                    </p>
                    <p className="mt-1 text-[10px] text-[#6B7A93]">
                      {item.owner} • {item.time}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Newsroom Header */}
        <div className="mt-14 flex flex-wrap items-center justify-between gap-4 border-b border-[#22385A] pb-4">
          <div className="flex items-center gap-2">
            <Newspaper size={20} className="text-[#D4AF37]" />
            <h3 className="font-['Barlow_Condensed'] text-base font-extrabold uppercase tracking-widest text-[#D4AF37]">
              GTEX NEWSROOM PREVIEW
            </h3>
          </div>
          <span className="font-['Barlow_Condensed'] text-xs font-bold uppercase tracking-wider text-[#6B7A93]">
            ILLUSTRATIVE STORIES • NOT A LIVE FEED
          </span>
        </div>

        {/* 3 Editorial Newsroom Cards */}
        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {kEditorialExamples.map((article, idx) => (
            <div
              key={idx}
              className="flex flex-col justify-between overflow-hidden rounded-xl border border-[#22385A] bg-[#13233A] transition-all hover:border-[#D4AF37]/50"
            >
              <div>
                <div className="relative h-48 w-full overflow-hidden bg-[#081120]">
                  <img
                    src={publicUrl(article.imageFile)}
                    alt={article.headline}
                    className="h-full w-full object-cover transition-transform duration-500 hover:scale-105"
                  />
                  <div className="absolute top-3 left-3 flex gap-2">
                    <span className="rounded bg-[#0B1626]/80 px-2 py-0.5 text-[10px] font-bold uppercase text-[#D4AF37] backdrop-blur-sm">
                      {article.category}
                    </span>
                    <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-300 backdrop-blur-sm border border-amber-500/30">
                      {article.statusLabel}
                    </span>
                  </div>
                </div>

                <div className="p-5">
                  <h4 className="font-['Barlow_Condensed'] text-xl font-bold uppercase text-[#F2F4F8] leading-tight">
                    {article.headline}
                  </h4>
                  <p className="mt-2 text-xs leading-relaxed text-[#9AA7BD]">
                    {article.subheadline}
                  </p>
                  <p className="mt-3 text-[11px] italic text-[#6B7A93]">
                    Illustrative story concept â€” not a live platform event.
                  </p>
                </div>
              </div>

              <div className="p-5 pt-0">
                <button
                  onClick={() => setInspectedArticle(article)}
                  className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-[#22385A] bg-[#0B1626] py-2.5 text-xs font-bold uppercase tracking-wider text-[#F2F4F8] transition-colors hover:border-[#D4AF37] hover:text-[#D4AF37]"
                >
                  <FileText size={14} />
                  <span>Read story concept</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modal Dialog for Article Inspection */}
      {inspectedArticle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
          <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-[#2F4C75] bg-[#0B1626] p-6 shadow-2xl sm:p-8">
            <button
              onClick={() => setInspectedArticle(null)}
              className="absolute top-4 right-4 rounded-lg p-2 text-[#9AA7BD] transition-colors hover:bg-[#13233A] hover:text-white"
              aria-label="Close dialog"
            >
              <X size={20} />
            </button>

            <div className="flex items-center gap-2">
              <span className="rounded bg-[#D4AF37]/20 px-2.5 py-1 font-['Barlow_Condensed'] text-xs font-bold uppercase text-[#D4AF37]">
                {inspectedArticle.category}
              </span>
              <span className="rounded bg-amber-500/20 px-2.5 py-1 text-xs font-bold text-amber-300 border border-amber-500/40">
                {inspectedArticle.statusLabel}
              </span>
            </div>

            <h3 className="mt-4 font-['Barlow_Condensed'] text-2xl sm:text-3xl font-black uppercase text-[#F2F4F8] leading-tight">
              {inspectedArticle.headline}
            </h3>
            <p className="mt-1 text-sm text-[#9AA7BD]">{inspectedArticle.subheadline}</p>

            <div className="mt-5 overflow-hidden rounded-xl border border-[#22385A] bg-[#081120]">
              <img
                src={publicUrl(inspectedArticle.imageFile)}
                alt={inspectedArticle.headline}
                className="max-h-60 w-full object-cover"
              />
            </div>

            {/* Illustrative Story Premise */}
            <div className="mt-6 rounded-xl border border-[#22385A] bg-[#13233A] p-4">
              <p className="font-['Barlow_Condensed'] text-xs font-black uppercase tracking-wider text-[#38BDF8]">
                ILLUSTRATIVE STORY PREMISE
              </p>
              <ul className="mt-2.5 space-y-1.5 text-xs text-[#9AA7BD]">
                {inspectedArticle.editorialNotes.map((note, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-[#38BDF8]">•</span>
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Editorial Narration */}
            <div className="mt-4 rounded-xl border border-[#22385A] bg-[#13233A] p-4">
              <p className="font-['Barlow_Condensed'] text-xs font-black uppercase tracking-wider text-[#D4AF37]">
                EDITORIAL NARRATION
              </p>
              <p className="mt-2 text-xs leading-relaxed text-[#F2F4F8]">
                {inspectedArticle.editorialNarration}
              </p>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setInspectedArticle(null)}
                className="rounded-lg bg-[#22385A] px-5 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-[#2F4C75]"
              >
                Close story preview
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
