import React from "react";
import { Link } from "react-router-dom";
import { DocumentHead } from "@/components/seo/DocumentHead";
import { NigeriaPlaySection } from "@/components/landing/NigeriaPlaySection";

const questions = [
  {
    q: "Can I buy and sell GTEX coins in Nigeria?",
    a: "Yes. Approved coin traders publish naira buy and sell adverts. A buy order escrows the trader's coins. A sell order escrows yours. Release happens after the naira payment is confirmed inside the order room.",
  },
  {
    q: "Does a new club pay to enter a league?",
    a: "No. Every GTEX competition is free to enter. A new club starts in foundation and moves only by promotion and relegation.",
  },
  {
    q: "What does a national team cost?",
    a: "Entering the competition is free. Renting the squad is the only cost. Prize coin is funded by GTEX.",
  },
  {
    q: "What is Build a Son?",
    a: "It is a paid academy order at the club you have open. The son inherits the parent's bloodline and joins that club's reserve squad. Slots are capped for the life of the owner.",
  },
];

export default function NigeriaPlay() {
  return (
    <div className="min-h-screen bg-[#0B1626] text-[#F2F4F8]" data-testid="nigeria-play-page">
      <DocumentHead
        title="Play GTEX in Nigeria | Clubs, naira coin desks, national teams"
        description="Create a GTEX football club in Nigeria, buy and sell coins in naira, run the 3D club operations centre, develop academy regens, and enter national team competitions for free."
        path="/nigeria"
      />
      <header className="border-b border-[#22385A] px-6 py-5 sm:px-12">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4">
          <Link to="/" className="font-['Barlow_Condensed'] text-2xl font-black tracking-widest">
            GTEX
          </Link>
          <div className="flex items-center gap-3 text-xs font-bold uppercase tracking-wider">
            <Link to="/login" className="text-[#9AA7BD] hover:text-white">
              Sign in
            </Link>
            <Link to="/signup" className="rounded-md bg-[#D4AF37] px-3 py-2 text-[#0B1626]">
              Create account
            </Link>
          </div>
        </div>
      </header>
      <NigeriaPlaySection id="play" />
      <section className="px-6 pb-20 sm:px-12">
        <div className="mx-auto max-w-[1440px]">
          <h2 className="font-['Barlow_Condensed'] text-3xl font-black uppercase text-[#F2F4F8]">
            Questions from Nigerian clubs
          </h2>
          <dl className="mt-6 grid gap-4 md:grid-cols-2">
            {questions.map((item) => (
              <div key={item.q} className="rounded-2xl border border-[#22385A] bg-[#13233A]/70 p-5">
                <dt className="font-semibold text-white">{item.q}</dt>
                <dd className="mt-2 text-sm leading-relaxed text-[#9AA7BD]">{item.a}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-8 text-xs leading-relaxed text-[#6B7A93]">
            GTEX is a simulated football universe operated from Lagos, Nigeria. In-game coins, player shares,
            and club values are game mechanics. They are not securities. Contact omotundeoni@playgtex.app or
            +234 806 993 8718.
          </p>
        </div>
      </section>
    </div>
  );
}
